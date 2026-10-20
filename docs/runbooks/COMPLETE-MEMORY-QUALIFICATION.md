# Complete memory qualification

Use `tests/qualification/run_complete.py` for a complete synthetic qualification
run. It enables the real language clients and browser checks and fails if any
test fails, errors or skips. Optional CI lanes can still select smaller scopes;
their result must not be labelled a complete qualification.

## Prerequisites

Prepare these in a verified Linux checkout, preserving any existing builds:

- The Python 3.12 environment with hashed service/index/MCP dependencies and
  the repository's qualification test dependencies.
- Native Node/npm, Go, a C compiler for Go race checks, and Rust/Cargo. Keep
  downloaded toolchains and caches scoped to the project or operator runtime.
- `clients/node` installed from its lock and compiled with `npm run build`.
- `clients/rust` dependencies prepared with `cargo test --locked --test
  project_live --no-run`; `clients/go` prepared with `go test -race -run '^$'`.
- `dashboard/nextjs-dashboard` installed from its lock, built with
  `NEXT_PUBLIC_API_URL=http://localhost:8000`, and a real Playwright Chromium
  installation that launches successfully. Keep telemetry disabled.
- Explicit disposable PostgreSQL, Qdrant, ArcadeDB and Valkey services and a
  prepared offline BGE model cache. Do not point the suite at an installed
  canonical database: some fixtures use temporary encryption keys.
- Native compatible `pg_dump`, `pg_restore`, `age` and `age-keygen` on PATH.
- Unoccupied loopback ports 8000 and 9050 for the built-dashboard fixture.

The operator supplies these through the private process environment:

- `RNR_QUALIFICATION_DATABASE_URL`
- `RNR_QUALIFICATION_MODEL_CACHE`
- `RNR_QUALIFICATION_INDEX_SETTINGS`

The index settings name the intentionally selected synthetic stores. Optional
`qdrant_api_key` and `qdrant_read_api_key` let the suite retain Qdrant
authentication. Keep the settings and credentials outside published artifacts.
The full runner sets `RNR_QUALIFICATION_CROSS_LANGUAGE=1` and
`RNR_QUALIFICATION_BROWSER=1`; no skipped case is changed into a passing case.

For the scoped tool installation used in Ubuntu-Hermes, set the following in
the qualification process's shell (these do not edit shell configuration):

```bash
qualification_tools_dir="$PWD/.qualification-tools"
export PATH="$qualification_tools_dir/go/bin:$qualification_tools_dir/cargo/bin:$PATH"
export CARGO_HOME="$qualification_tools_dir/cargo"
export RUSTUP_HOME="$qualification_tools_dir/rustup"
export GOPATH="$qualification_tools_dir/gopath"
export GOCACHE="$qualification_tools_dir/gocache"
export PLAYWRIGHT_BROWSERS_PATH="$qualification_tools_dir/browsers"
```

Keep compatible PostgreSQL/age tools on PATH as well. Load the three private
qualification settings above through the operator's local mechanism; never paste
credential values into a command, report or conversation.

Run from the selected checkout using the prepared Python environment (in this
Hermes checkout, `.venv-deployment/bin/python`):

```bash
python tests/qualification/run_complete.py --artifacts /absolute/private/new-run
```

The artifact directory must not already exist and must be outside the source
checkout, including paths reached through symlinks. The runner creates it with
owner-only access, disables dotenv loading and telemetry in its child process,
and retains the log, JUnit XML, summary and fixtures. The exit status is nonzero
for any failure, error, skip, missing report or invalid report.
Only sanitized summaries should be published. Preserve failed runs as evidence.

## Model-driven capture is a separate check

Passing the suite does not prove that a chat model chooses memory tools. Use the
dedicated synthetic Hermes profile and invented, uniquely named project facts.
Keep cloud fallbacks disabled for a local qualification. Confirm the endpoint's
actual served context, not just the model's native maximum. Preserve settings
and existing data before a model or serving change; never falsify a context
window or disable Hermes guards.

Check automatic selected save without an explicit remember request, recall in a
new session, a clear versioned correction, ambiguous-change clarification with
no mutation, and credential refusal with no saved secret. Inspect tool traces
and independently inspect encrypted canonical versions. Keep raw traces private.
Do not accept a statement that the model remembered something as storage proof.

Use the actual Hermes-managed runtime and profile secret scope. A bare Python
interpreter may lack dependencies supplied by Hermes' bootstrap. Retain model
failures even when another configured local model passes. Model-driven results
qualify the tested model, prompt, serving configuration and scenarios; they do
not establish universal model compliance or private OS isolation.
