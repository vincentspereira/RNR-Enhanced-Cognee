"""Offline-only CPU embedding for the approved pinned BGE-small-en-v1.5 export.

No model discovery, downloads, transformers, remote providers or fallback.
Pooling follows the pinned model card: first token (CLS), then L2 normalize.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading


class LocalOnnxEmbedder:
    QUERY_PREFIX = 'Represent this sentence for searching relevant passages: '
    MODEL_REPO = 'BAAI/bge-small-en-v1.5'
    MODEL_REVISION = '5c38ec7c405ec4b44b94cc5a9bb96e735b38267a'

    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir).resolve(strict=True)
        manifest_bytes = (self.model_dir / 'manifest.json').read_bytes()
        manifest = json.loads(manifest_bytes)
        if manifest.get('repo') != self.MODEL_REPO or manifest.get('revision') != self.MODEL_REVISION:
            raise ValueError('Only the approved pinned BGE-small-en-v1.5 model is supported')
        required = {'onnx/model.onnx', 'tokenizer.json', 'tokenizer_config.json',
                    'special_tokens_map.json', 'config.json'}
        entries = {entry['path']: entry for entry in manifest['files']}
        if not required <= entries.keys():
            raise ValueError('Incomplete local model manifest')
        for name, entry in entries.items():
            path = (self.model_dir / name).resolve(strict=True)
            if not path.is_relative_to(self.model_dir):
                raise ValueError('Model asset path escapes model directory')
            digest = hashlib.sha256()
            with path.open('rb') as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != entry['sha256'] or path.stat().st_size != entry['size']:
                raise ValueError(f'Local model asset integrity mismatch: {name}')
        config = json.loads((self.model_dir / 'config.json').read_text())
        token_config = json.loads((self.model_dir / 'tokenizer_config.json').read_text())
        self._dimension = int(config['hidden_size'])
        if self._dimension != 384 or config['model_type'] != 'bert':
            raise ValueError('Unexpected pinned model configuration')
        self.manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        self.fingerprint = self.manifest_sha256 + ':cls-l2:query-instruction-v1'
        # Optional native dependencies are imported only on explicit construction.
        import onnxruntime as ort
        from tokenizers import Tokenizer
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self._session = ort.InferenceSession(str(self.model_dir / 'onnx/model.onnx'),
                                            sess_options=options, providers=['CPUExecutionProvider'])
        self._input_names = {item.name for item in self._session.get_inputs()}
        if self._input_names != {'input_ids', 'attention_mask', 'token_type_ids'}:
            raise ValueError('Unexpected ONNX input contract')
        if any(item.type != 'tensor(int64)' for item in self._session.get_inputs()):
            raise ValueError('ONNX inputs must be int64')
        outputs = self._session.get_outputs()
        if len(outputs) != 1 or outputs[0].name != 'last_hidden_state' or outputs[0].shape[-1] != 384:
            raise ValueError('Unexpected ONNX output contract')
        self._tokenizer = Tokenizer.from_file(str(self.model_dir / 'tokenizer.json'))
        self._tokenizer.enable_truncation(max_length=min(int(token_config['model_max_length']),
                                                       int(config['max_position_embeddings'])))
        pad_token = token_config['pad_token']
        self._tokenizer.enable_padding(pad_id=self._tokenizer.token_to_id(pad_token), pad_token=pad_token)
        self._lock = threading.Lock()

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not isinstance(texts, list) or any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError('Embedding input must be a list of nonempty strings')
        if not texts:
            return []
        import numpy as np
        result = []
        with self._lock:
            for start in range(0, len(texts), 16):
                encoded = self._tokenizer.encode_batch(texts[start:start + 16])
                feeds = {'input_ids': np.asarray([e.ids for e in encoded], dtype=np.int64),
                         'attention_mask': np.asarray([e.attention_mask for e in encoded], dtype=np.int64),
                         'token_type_ids': np.asarray([e.type_ids for e in encoded], dtype=np.int64)}
                hidden = self._session.run(['last_hidden_state'], feeds)[0]
                pooled = hidden[:, 0, :]
                norms = np.linalg.norm(pooled, axis=1, keepdims=True)
                if not np.isfinite(pooled).all() or not (norms > 0).all():
                    raise RuntimeError('ONNX produced nonfinite or zero embeddings')
                result.extend((pooled / norms).tolist())
        return result

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError('Query must be a nonempty string')
        return self.embed([self.QUERY_PREFIX + text])[0]
