# Enhanced Cognee native directory provider — deployment preparation v1

This preserved candidate packages the accepted request-validation provider with
only its selected local runtime: CPU ONNX embeddings, LanceDB vector adapter and
SQLite revision ledger. No full Enhanced Cognee service stack, library service,
remote extraction model, database credentials or generic `src` import path is required.

## Prepared, not activated

The native plugin root is this candidate directory: `__init__.py`, `plugin.yaml`,
`pyproject.toml`, and `enhanced_cognee_hermes/`. The root wrapper delegates registration
to the packaged provider. Hermes loads it under a home/source-specific synthetic
module namespace; all bundled runtime imports are relative to that namespace.
The wheel includes the selected runtime, but is a build artifact, **not permission
to pip-install into Hermes's managed environment**.

Direct dependencies are pinned to the real isolated test versions:
`numpy==2.5.4`, `onnxruntime==1.31.0`, `tokenizers==0.23.3`,
`lancedb==0.40.0`, `pyarrow==26.0.0`. Python >=3.12 is required by this NumPy pin.
Actual tested interpreter: CPython 3.12.13 on Ubuntu/WSL. Other interpreters and
platforms are not accepted by these tests. Transitive versions are recorded in evidence.

No startup model download is performed. Copy the already verified model tree
into `<explicit-home>/enhanced-cognee/models/bge-small-en-v1.5/`; symlinks escaping
the owned home are rejected. The model is BAAI/bge-small-en-v1.5 revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` and its model card declares MIT.
The selected source is covered by the repository Apache-2.0 license, retained as
`LICENSE-Enhanced-Cognee`. Copied runtime/adapter provenance and exact import-only
diffs are in the packaging evidence. Dependencies retain their own wheel licenses.

## Installation/preparation boundary

The installed host CLI accepts catalog names and Git URLs, including `file://` Git
URLs, **not a local uncommitted directory**. No commit or publication is authorized
in this phase. Therefore no `plugins install` transaction or managed-runtime union
sync is claimed. Actual native loading was exercised by placing this exact directory
in disposable homes, through genuine `plugins.memory` discovery/registration and
`MemoryManager`, with the real host configuration loader (no loader stub).

After independent review, the parent may place the verified directory at
`<approved-home>/plugins/enhanced-cognee/`, or publish an approved exact Git revision
and use the supported CLI flow. Validate with `hermes plugins validate <directory>
--json`. For a Git installation use `hermes plugins install <Git-URL> --ref
<40-character-reviewed-commit> --yes-deps --no-enable`. This invokes PM before
publication. Those transaction commands remain unexecuted here; their flags are
verified against the real CLI help/source. Do not install the built wheel using pip
in Hermes's selected runtime. Do not use `--install-deps` on the live checkout before
parent review: changing HERMES_HOME alone does not isolate its checkout-owned state.

`hermes memory setup enhanced-cognee` is the native dependency/setup path, but it
also offers provider selection/configuration; reserve it for separately approved
activation. Keep capture false and choose an approved audience/data scope first.
The provider's sidecar is `<home>/enhanced-cognee.json` with `{"auto_capture": false}`.
Creating that file alone neither selects a provider nor ingests any data.

## Scope and tests

New deployment tests prove directory discovery, native registration with empty tool
schemas before initialization, default-factory startup with actual 384-dimensional
CPU ONNX and LanceDB, manually seeded synthetic turn-source recall after reopening,
source provenance, default capture suppression, same-home fresh CLI-session recall,
other keyed-chat/other-home negative controls, and independence from a hostile
ambient `src` package. Model/storage execution uses an isolated network namespace
and disposable homes outside both source checkouts. Host source/config is genuine;
no fake model/backend/config loader is used in these new tests.

The historical tests are preserved unchanged, including their explicit stubs and
old import-boundary expectations. Their prior accepted verdict does NOT accept
this packaging delta. A fresh bound rebind/replay and independent review remain
required before promotion. Never execute historical `tests/run_evidence.py` here:
it targets the old candidate and old evidence folder.

Provider behavior remains unchanged apart from packaged dependency lookup/imports:
UNTRUSTED escaped source quotations; stable profile-private unkeyed CLI scope;
keyed conversations stay isolated; empty tool schemas; no built-in memory mirror;
no inferred owner facts; capture off; best-effort callbacks; soft two-second recall
budget, not hard cancellation; no crash-safe outbox; no portable rekey/migration.
No live LLM prompt-dispatch or private-ingestion acceptance is asserted.

## Maintenance and rollback

Keep one immutable provider artifact, its manifest, model manifest and license
records. Rebuild/review/replay before changing dependency/model pins. No service
supervisor or additional updater is needed for this in-process selection. Quiesce
all writers before copying the complete `enhanced-cognee/` tree plus sidecar for
backup. Restore only to the same resolved home with the same embedding identity;
profile scope hashes intentionally prevent cross-home recall. Disabling/removing
the provider must not delete its data or Hermes built-in memory/session stores.
Parent approval remains required for native backup/restore commands or live setup.
