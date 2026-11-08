# Enhanced Cognee: narrow local memory runtime

This opt-in **source-checkout feature**, not a production-readiness claim, adds
local source revision control and semantic vector recall. It reuses Enhanced
Cognee's `src.db_adapters.vector_lancedb.create_client` directly. It does not
import upstream Cognee pipelines, generate graphs, call an LLM, read `.env`,
select global providers, or start a service.

## Minimal use

Run from this checkout with its root and `src` on `PYTHONPATH`. The existing
wheel configuration does not yet package this new runtime or the `src` adapters.
Native adapter/library integration is separate work.

```python
from pathlib import Path
from hermes_memory import EnhancedMemoryEngine, LocalOnnxEmbedder

embedder = LocalOnnxEmbedder(Path('.data/hermes-models/bge-small-en-v1.5'))
engine = EnhancedMemoryEngine(Path('.data/my-dedicated-memory-root'), embedder)
try:
    engine.upsert('synthetic:note', 'A young feline drinks milk.',
                  scope='trusted-profile-and-user-scope',
                  metadata={'owner': 'synthetic-user', 'synthetic': True})
    hits = engine.search('What does the kitten drink?',
                         scope='trusted-profile-and-user-scope', limit=5)
    engine.withdraw('synthetic:note', scope='trusted-profile-and-user-scope')
    counts = engine.stats(scope='trusted-profile-and-user-scope')
finally:
    engine.close()
```

Scopes must be nonempty strings supplied by a trusted caller. The engine does
not authenticate users or accept a model-selected scope as trustworthy. Every
scope maps to its own SHA-256-named LanceDB collection; isolation does not depend
on optional payload filters. Different scopes may use identical source IDs.
The root must be a dedicated caller-owned local directory. New root directories
are mode 0700; owned control/lock files and generated vector files are tightened
to 0600, and vector directories to 0700. Reserved storage symlinks are rejected.
Existing caller root permissions are not silently changed. This is not encryption
or a defense against a malicious same-user filesystem actor.

## Embeddings and offline contract

`LocalOnnxEmbedder(model_dir)` requires all assets already present plus a local
manifest containing sizes and SHA-256 digests. It supports only
`BAAI/bge-small-en-v1.5` at revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`. It checks manifest-listed files,
loads ONNX explicitly with `CPUExecutionProvider`, and uses local `tokenizers`.
Missing or mismatched assets fail; there is no implicit download or remote
fallback. Optional dependencies are imported only during explicit construction.

The pinned model card specifies **CLS pooling plus L2 normalization**, not mean
pooling. Its int64 inputs are `input_ids`, `attention_mask`, `token_type_ids`;
`last_hidden_state` has shape `[batch, sequence, 384]`. Documents are embedded
unchanged. `embed_query` adds the model card's retrieval instruction:
`Represent this sentence for searching relevant passages: `.
The engine uses that hook when available; injected test embedders need only
`dimension` and `embed(list[str])`. Inputs are truncated to the model/tokenizer
maximum of 512 tokens; there is no automatic chunking. A root records embedding
identity and dimension to reject incompatible reopening. Custom embedders
should expose a stable `fingerprint`; otherwise identity falls back to class
name plus dimension, which cannot detect changed weights inside that class.

Reference: the locally verified pinned `README.md`, especially its English
retrieval-instruction table and Transformers CLS-pooling example; upstream URL:
https://huggingface.co/BAAI/bge-small-en-v1.5/blob/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/README.md

## Revision control and failures

SQLite is a local revision/control ledger, not a second search backend. It
retains original text, metadata/provenance, content hashes, source revision
history and authoritative head/tombstone state. LanceDB stores vectors plus
revision/hash references. All semantic ranking comes from the existing vector
adapter's cosine search. `stats.active` counts ledger heads, not independently
verified healthy vector rows.

Upserts stage a fresh UUID vector, then verify self-search readback (ID,
revision, hash and cosine score) **before** atomically advancing the source
head. Unchanged text and metadata are idempotent and still verify the existing
vector before returning `indexed: true`. Exceptions propagate; failed staging
leaves the prior revision active. Crashes between vector staging and ledger
commit can leave orphan vectors, but recall accepts only current, active,
ledger-matched revisions. Withdrawal only sets a tombstone: no source history
or vector data is physically deleted. An explicit later upsert reactivates the
source as a new revision.

Thread locks and Linux `flock` serialize all operations sharing the root,
including initialization and recall. Each process must construct its own
engine; inherited engine objects after `fork` are rejected. Local cooperating
writers were tested, not NFS/distributed writers. SQLite uses synchronous FULL;
process interruption was exercised, not hardware power-loss durability.

For correctness in this minimal implementation, vector search retrieves all
rows in the selected scope before rejecting stale/orphan/tombstoned references
and applying the requested limit. This prevents obsolete rows crowding out
active results, but is O(scope history) and unsuitable for large-scale use.
There is no compaction, source restoration API, remote synchronization, graph
pipeline, ACL service, encryption or full feature-parity promise.

## Reproducible checks

```sh
# No native dependencies needed: fake embedding/vector unit tests only.
python -m unittest discover -s tests/hermes_runtime -p test_runtime.py -v

# Actual CPU ONNX + actual existing LanceDB adapter; namespace blocks egress.
unshare --user --map-root-user --net .venv/bin/python -m unittest discover \
  -s tests/hermes_runtime -v
```

Actual-model tests explicitly skip if assets/dependencies are unavailable;
they never install or download. The real semantic fixture uses only synthetic
sources. Durability/process tests use real LanceDB with **fake embeddings** and
are labeled accordingly; they do not measure semantic quality. RED/GREEN logs
and source/model hashes are stored under the separately approved verification
`runtime/` directory. The observed model-manifest SHA-256 is
`a8cc5d0e4ca40a702dfb5b0b01144d474c026d3ad2b2909ae79c6fcd8983d9b2`.
Held-out comparative benchmarking is independent work; this smoke test does
not establish a benchmark winner.
