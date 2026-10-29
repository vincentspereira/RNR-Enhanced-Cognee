# Enhanced Cognee native Hermes provider

This is a standalone **source-runtime adapter**, not a new Hermes core memory store.
It implements the public `agent.memory_provider.MemoryProvider` ABC and exports
`register(ctx)`. The provider identifier is `enhanced-cognee`. No profile is activated
by importing, testing or packaging it. The tested host checkout is
`97a9ae8ee55d31bebce49f1fb6b5ef775323976a`.

## What this adapter does

- Constructor/import/schemas/identity/backup probes do not create stores, initialize
  models, read dotenv, request credentials, ingest native memory or call services.
- Availability reads only `enhanced-cognee.json` in an explicitly supplied home,
  the host's context-local home override, or explicit `HERMES_HOME`. Without one,
  it fails closed instead of exploring a default profile. It checks module specs
  without importing runtime/ML packages and checks owned local model files,
  including the required `manifest.json`. Full manifest/asset integrity validation
  happens only when the actual embedder opens; the cheap probe does not hash assets.
  This is prerequisite readiness, not proof a model or store can open.
- Initialization requires the host's explicit `hermes_home`, pins the instance to
  that resolved profile, and lazily creates the local backend. Initialization
  failures remain not-ready; later recall/capture cannot claim success.
- All state belongs under `<hermes_home>/enhanced-cognee/`; setup settings are in
  `<hermes_home>/enhanced-cognee.json`. Obvious root/model symlink escapes are
  rejected. This is not a sandbox against hostile concurrent filesystem changes.
- `get_tool_schemas()` returns `[]`. There is no model-callable namespace argument,
  arbitrary path, destructive tool, or memory mirror.
- Recall sends at most 2,000 query characters, requests five results with a 0.25
  minimum score, discards invalid/low scores and bounds output to 6,000 characters
  of escaped, valid JSON. Quotes are labelled **UNTRUSTED reference evidence**,
  never system instructions or verified personal facts. Escaping is not a claim
  that adversarial text cannot influence an LLM. Last recall status resets on each
  invocation, errors/no answer return `""`, and session-switch late results are
  discarded. System-prompt text stays empty/static; built-in memory stays intact.
- Conversation scope is an opaque SHA-256. Unkeyed `platform=cli` uses a stable,
  domain-separated **profile-private local owner scope**, so a fresh provider and
  physical CLI session can recall that same home's previously captured evidence.
  This assumes a single local owner per CLI home; it does not infer a speaker ID
  or verify statements as owner facts. Do not share that home between local users.
  Explicitly keyed chats retain resolved-home/platform/`gateway_session_key` scope;
  they cannot collide with the CLI owner scope, even on `platform=cli`. Other
  unkeyed platforms retain physical-session isolation. No cross-profile/all-bot
  sharing or Brain ingestion is enabled. Titles/cwd/session-opener identity are
  not scope. Old physical-session CLI records are not automatically migrated into
  the new scope; this change does not widen or rewrite historical data.
- Old session mappings are immutable and retained for delayed host callbacks.
  Reusing a physical session with a conflicting platform, gateway key or agent
  context raises `ValueError` **before** changing the current session, recall status
  or generation. Switch metadata inherits from the current session; an omitted key
  cannot silently select an old mapping belonging to another chat. Supply the old
  mapping's correct platform/key/context explicitly when switching back. Ready
  `initialize` remains idempotent (it is not a session-switch API), but explicitly
  contradictory metadata for an already bound physical session is rejected.
  Explicit `turn_author` identifies **this turn**, not the initialization user.
  Without it, attribution is `unknown`; the adapter never guesses the session
  opener or mutable latest-turn identity. Each recalled entry includes quoted
  `metadata.author_id`, `author_name`, **source** `session_id` (not the retrieving
  session), and `platform`, bounded to 128/128/128/64 characters respectively.
  Missing or empty provenance is `unknown`; source metadata is not authenticated.
  Evidence type remains bounded to 64 characters and `verified_owner_fact=false`
  is explicit. The UNTRUSTED label says that "I" refers to the quoted speaker, not
  necessarily the owner or assistant. Metadata receives the same JSON/HTML-character
  escaping as text; whole entries may be omitted to keep valid JSON within 6,000
  characters. This supports inspectable keyed-chat quotes, not speaker ACLs, fact
  resolution or a guarantee that an LLM will attribute every statement correctly.

## Optional capture, disabled by default

`get_config_schema()`/`save_config(values, hermes_home)` implement native setup's
non-secret sidecar path. Only `auto_capture` is accepted, as a real boolean;
its default is **false**. Setup saves do not change `memory.provider` or activate
anything. Change settings while quiescent and restart the provider instance.
`diagnostics()` returns safe state/status codes, not exception text, source
content, credentials, or receipt payloads.

When separately authorized with `auto_capture=true`, `sync_turn` performs one
upsert of the **direct user text**, with `evidence_type=direct_user_statement`,
`verified_owner_fact=false`, author/session/platform provenance and a truncation
flag. Assistant statements, raw tool output, full transcript text, delegation,
compression archives and MEMORY.md/USER.md writes are not copied. Cron,
subagent, flush and bot-authored capture is suppressed. Corrections become new
quoted evidence; no inferred fact extraction or speculative deletion happens.

Capture admits at most 16,000 input characters, stores at most 4,000, and scans
only role labels when a transcript has at most 2,048 rows. Evidence IDs depend on
scope, physical session, author ID and original user text—not retry timing,
assistant output or transcript growth. **Identical text from the same author in
the same session collapses into one evidence record**, even if intentionally
repeated; Hermes supplies no stable event ID to this callback. Distinct correction
text gets a distinct ID. Restart/replay with unchanged inputs uses the same ID.

## Worker, deadline and durability limits

There is **no independent adapter thread/queue**. The real Hermes manager dispatches
`sync_turn` on its context-bound serialized worker. Direct callers of `sync_turn`
execute inline and should dispatch it themselves. One non-blocking admission lock
prevents concurrent calls against a single backend; busy recall/writes are rejected
with `busy` status, not silently queued or acknowledged. A busy write can be lost;
the host does not automatically retry it. No durable outbox is advertised.

Recall has a **soft 2-second elapsed-result budget**; an over-budget return is
not injected. The agreed synchronous runtime API has no cancellation/deadline
parameter. **This adapter cannot hard-cancel a wedged backend call.** Hermes's
own recall timeout prevents the chat waiting indefinitely but is not cancellation.
There are no unlimited adapter threads. Actual runtime operation/lock/model
latency bounds must be verified before a pilot; this remains an integration gate.

`last_write=backend_returned` means a dictionary receipt returned, not that evidence
is crash-safe. Error/invalid/busy/oversized states are explicit. This provider keeps
checkpoint API **v1**; it makes no v2 pre-compression checkpoint promise. The host's
callback completion and bounded shutdown do not guarantee durable delivery or
recovery of turns lost before their callback ran.

Shutdown rejects new work, resets recall and closes the backend once. If a backend
call is active, shutdown returns with `close_pending=true`; that call closes it when
it finally exits. A permanently wedged call remains pending. Close itself is a local
runtime call and is not hard-cancellable. Shutdown/disable never deletes data,
Brain files, native memory, transcripts, model assets, services or sibling profiles.
Quiesce/close the runtime before backup; raw concurrent file copies are not a
transaction-consistent export claim. Removal/export/purge requires separate approval.

## Narrow quiescent restore contract

Scope hashes include the **resolved absolute Hermes home**. Supported restoration
in this source-level test is limited to a complete quiescent copy returned to the
**same resolved absolute home**, with unchanged platform/key and embedding identity.
Copying the same bytes to a different home intentionally does **not** grant recall
of the original scope. No portable migration, rekey, import, hot backup, generic
backup integration or host-crash recovery is implemented. `backup_paths()` remains
empty; do not infer native backup support or retry an owner-blocked backup command.

For a separately approved restore, all writers/readers and host callback workers
must first be stopped/drained and the backend closed (`close_pending=false` is
necessary, not a substitute for quiescing every process). Preserve the entire owned
`enhanced-cognee/` tree together, including the SQLite revision/control ledger,
LanceDB vectors/manifests, lock file and pinned model assets, plus
`enhanced-cognee.json`. Do not select only the SQLite file or live-copy open stores.
Set capture off in the quiescent configuration before the copy and keep it off on
initial restored startup. Record a complete relative-path inventory and every
file's size/SHA-256, including model manifest/assets; verify the whole restored
inventory before reopening. Move the original aside instead of deleting or
replacing it. Restore to the original resolved path; verify actual quoted recall
from a fresh provider/session with the original source provenance. Enabling capture
again, removal, relocation or rekey requires separate owner approval.

`test_bridge_rebind_provenance.py` exercises precisely this sequence using **only
its newly created synthetic fixture**. It closes the real engine, turns capture
off, checks every file/directory, size, mode and hash in the quiescent copy, moves
the original aside, copies back to the same path, and verifies real CPU ONNX/LanceDB
recall. The moved original and copy remain unchanged. A byte-identical different-home
copy retains original ledger rows but returns no recall in the new home's scope.
This is a positive same-home restore control plus an isolation control, not general
backup acceptance; no real profile/private files are copied.

## Source and dependency layout (not activated by these instructions)

The root Enhanced Cognee wheel **does not include `src/` or `bin/`**. Installing it
alone is NOT a usable adapter-runtime installation. This adapter's wheel contains
only `enhanced_cognee_hermes/`, its README/manifest and the memory-provider entry point;
it does not pretend to package the runtime. No adapter wheel build/install was run
in the acceptance suite. The isolated test environment lacked a build backend.

Supported offline development layout:

```text
RNR-Enhanced-Cognee-Hermes/
  .venv/                           # owner-prepared isolated Python deps
  src/hermes_memory/runtime.py     # separately supplied local runtime
  src/hermes_memory/embeddings.py  # actual local ONNX embedder
  integrations/hermes/
    pyproject.toml
    enhanced_cognee_hermes/         # this adapter, source importable
Hermes checkout/
  agent/memory_provider.py         # actual host ABC (no copied fallback)
synthetic/profile-home/
  enhanced-cognee.json
  enhanced-cognee/
    models/bge-small-en-v1.5/
      manifest.json
      onnx/model.onnx
      tokenizer.json
      config.json
      tokenizer_config.json
      special_tokens_map.json
```

The lazy seam imports `src.hermes_memory.runtime` for `EnhancedMemoryEngine` and
`src.hermes_memory.embeddings` for `LocalOnnxEmbedder(model_dir)`, then creates
`EnhancedMemoryEngine(root, embedder)`.
The agreed engine API is `upsert(source_id,text,scope,metadata) -> dict`,
`search(query,scope,limit=5,min_score=None) -> list[dict]`, soft-only
`withdraw(source_id,scope) -> dict`, `stats(scope) -> dict`, and `close()`.
This adapter does not expose withdraw/stats to the LLM. `backend_factory(root,
model_dir)` allows isolated injected clients; fake clients prove the seam, not
actual ONNX/search/persistence benefit. The real bridge tests below exercise this
default factory, not an injected runtime or embedding replacement.

For an owner-managed source launch, make the full checkout, Hermes checkout and
`integrations/hermes` importable **in the interpreter that actually executes the
provider**, using an explicit launcher/PYTHONPATH. A side environment's installed
packages are not automatically visible to another Hermes interpreter/plugin host.
The manifest and adapter pyproject declare bounded numpy/onnxruntime/tokenizers
requirements; actual runtime-specific requirements must also be reconciled by the
owner. Never mutate Hermes's selected environment with ad-hoc pip injection.

For a future directory deployment, copy the *contents* of
`enhanced_cognee_hermes/` into `<approved_home>/plugins/enhanced-cognee/`, retain
`plugin.yaml`, let Hermes's plugin/PM admission prepare declared dependencies, and
provide the separate source-runtime import path to that plugin execution environment.
For an owner-managed packaged deployment, build/install `integrations/hermes` through
that owner's declarative packaging process. Neither route fixes the missing runtime
source by installing the root wheel. Plugin-host isolation/source-path propagation
and real backend startup still require integration acceptance. **No such deployment
or installation was performed here.**

Provision the verified ONNX assets by copying—not downloading on startup—into the
owned model directory of a synthetic home first. Do not borrow another profile's
stores/credentials or run the native and MCP writers on one data root.
Only after separate approval should native setup and `memory.provider` selection
be run for an approved home. Built-in selection remains unchanged in this delivery.

## Reproduce offline acceptance

Set `TMPDIR` to the approved scratch directory. From the checkout, use the already
prepared isolated environment; do not install or activate a provider for tests:

```sh
TMPDIR=/absolute/path/to/approved-scratch \
HERMES_SOURCE=/absolute/path/to/hermes-agent \
  unshare --user --map-root-user --net .venv/bin/python -B -m pytest \
  --noconftest -p no:cacheprovider -o addopts= integrations/hermes/tests -q
```

`test_provider.py` loads the real host ABC and exercises the real manager's registration,
context-bound writer, author forwarding, FIFO callback flush and shutdown with
fresh fixture homes and **fake in-memory backends**. Host config loading is explicitly
stubbed in manager fixtures to prevent managed-runtime re-exec/live config reads;
the manager and worker implementation are real.

`test_real_bridge.py` copies the owner's already verified assets from
`.data/hermes-models/bge-small-en-v1.5` into disposable synthetic homes. It uses
the real default factory, EnhancedMemoryEngine, LanceDB and pinned CPU ONNX model:
384-dimensional normalized embeddings, opt-in learned-evidence recall from a fresh
CLI provider/session, negative other-profile/keyed-chat cases, gateway continuation,
immutable delayed-job provenance, missing-manifest fail-closed readiness, invalid
manifest initialization failure, default capture suppression and native mirror no-op.
The manager config-loader stub is the only host dependency replacement on that path;
no fake model/engine is used. The command above denies networking at the namespace
level. No live profile discovery/config, bots or Brain/native store migration is tested.
This is bounded local integration acceptance, not deployed/installed fleet proof.

`tests/run_evidence.py <unique-label>` also
preserves each red/green log and source snapshot under the approved build evidence
folder; labels cannot overwrite existing logs.
