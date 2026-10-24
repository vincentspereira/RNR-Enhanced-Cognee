"""Offline text-only BGE inference from reviewed, hash-pinned model files.

The restricted service does not import an image/model-download framework. New
model families need explicit admission and vector/retrieval qualification.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import stat

MODEL = "BAAI/bge-small-en-v1.5"
MODEL_REPOSITORY = "Qdrant/bge-small-en-v1.5-onnx-Q"
MODEL_REVISION = "aa8f8b060edb00e03bfdd08813a2949946c8ba55"
# MIT-licensed public model; sizes bound reads before loading executable ONNX.
MODEL_FILES = {
    "model_optimized.onnx": (66465124, "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431"),
    "tokenizer.json": (711396, "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"),
    "tokenizer_config.json": (1242, "0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53"),
    "special_tokens_map.json": (695, "5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a"),
    "config.json": (706, "13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd"),
}


def model_file(cache: Path, name: str) -> bytes:
    """Read an exact regular file; never load unchecked or substituted bytes."""
    size, expected = MODEL_FILES[name]
    fd = os.open(cache / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != size:
            raise ValueError("Prepared text-model file size/type differs")
        raw = source.read(size + 1)
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Prepared text-model file hash differs")
    return raw


class LocalEmbeddings:
    def __init__(self, model: str, cache: str):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        if model != MODEL:
            raise ValueError("Text-only model is not admitted; retain the prior runtime for other models")
        if not Path(cache).is_dir():
            raise ValueError("Prepare the local embedding model cache before starting")
        self.model = model
        self._slots = asyncio.Semaphore(2)
        # All bytes are verified before parsing. No hub client, fallback model,
        # remote execution provider, image import or startup download is used.
        prepared = Path(cache)
        for name in ("config.json", "tokenizer_config.json", "special_tokens_map.json"):
            model_file(prepared, name)
        self.tokenizer = Tokenizer.from_str(model_file(prepared, "tokenizer.json").decode("utf-8"))
        self.tokenizer.enable_truncation(max_length=512, direction="right")
        self.tokenizer.enable_padding(direction="right", pad_id=0, pad_type_id=0, pad_token="[PAD]")
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.engine = ort.InferenceSession(model_file(prepared, "model_optimized.onnx"),
                                           sess_options=options, providers=["CPUExecutionProvider"])
        if ({item.name for item in self.engine.get_inputs()}
                != {"input_ids", "attention_mask", "token_type_ids"}):
            raise ValueError("Prepared text-model input contract differs")

    async def embed(self, content: str) -> list[float]:
        import numpy as np

        if not isinstance(content, str):
            raise ValueError("Embedding content must be text")

        def run():
            encoded = self.tokenizer.encode(content)
            inputs = {"input_ids": np.asarray([encoded.ids], dtype=np.int64),
                      "attention_mask": np.asarray([encoded.attention_mask], dtype=np.int64),
                      "token_type_ids": np.zeros((1, len(encoded.ids)), dtype=np.int64)}
            output = self.engine.run(None, inputs)[0]
            if output.ndim != 3 or output.shape != (1, len(encoded.ids), 384):
                raise ValueError("Prepared text-model output contract differs")
            vector = output[:, 0]
            vector = vector / np.maximum(np.linalg.norm(vector, axis=1, keepdims=True), 1e-12)
            if not np.isfinite(vector).all():
                raise ValueError("Text model returned nonfinite embeddings")
            return vector[0].tolist()
        async with self._slots:
            return await asyncio.to_thread(run)
