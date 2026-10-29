# Live Hermes qualification - 20 October 2026

The separate invented-data installation now works inside Ubuntu-Hermes. The
complete remediation plan and everyday/private-data activation are not complete.
The owner has authorized publication and eventual conflict resolution/merge;
merge remains conditional on completing the implementation and working checks.

## What was installed and exercised

Code arrived through GitHub into a separate Hermes-local checkout. The tested
source revision is recorded in the accompanying JSON evidence. No Workspace or
Windows project/model folders were connected to Hermes.

- A dedicated native PostgreSQL 16.15 test cluster, bound to loopback, obtained
  from signed Ubuntu package metadata and unpacked into the user's test runtime.
  No system-wide package installation, Docker startup, firewall or mount change.
- A dedicated Python 3.12.13 service environment installed from the hashed locks.
  Persistent encryption/signing material and a restricted database role were
  generated into owner-only files. Runtime startup validates schema version 2;
  a separate operator provisions it. The profile token expires after 24 hours.
- The free local BAAI/bge-small-en-v1.5 search model, prepared inside Hermes and
  loaded offline by the service. The ready/status responses identify semantic
  retrieval and explicitly identify graph reasoning as unavailable.
- The `enhanced_cognee` provider in a fresh `enhanced-cognee-test` Hermes profile,
  with no cloned notebook. The everyday provider was not switched.

Hermes' actual CLI launcher selects Python 3.14.7. An older Python 3.12.13 Hermes
environment also remains on the machine. Direct provider lifecycle checks passed
in both; the full chat checks used the actual CLI, not an interpreter substitute.
The service's separate Python version does not change Hermes' interpreter.

## Results

| Check | Result and limit |
| --- | --- |
| Full qualification lane inside Ubuntu-Hermes | 69 passed, including actual PostgreSQL, offline embeddings, service permissions, capture/library boundaries, migration, keys and age backups |
| Same lane in Workspace | 69 passed on the disposable PostgreSQL/container fixture; separate from the Hermes native-cluster result |
| Installed Hermes provider lifecycle | 11 live checks passed, including retry safety, paraphrase recall, secret rejection, clarification, version conflicts, retraction, bot denial and session switching |
| English retrieval set | All 12 intended facts ranked first; no private-project distractor was returned. Inside Hermes: median 39.51 ms, p95 50.34 ms. Small synthetic set, not general accuracy/load evidence |
| Actual selected automatic capture | The configured GLM-5.3-Flash chat searched first and saved the fictional Cedar decision without a remember request |
| Actual new-session recall | A different chat recalled the saved eleven-day decision and used the record; the built-in notebook did not contain the fixture |
| Actual clear correction | Hermes used the current version and changed the decision to nine days. Database inspection confirmed encrypted versions 1 and 2, with eleven retained only as the earlier decision/history |
| Actual uncertain change | Hermes called `enhanced_clarify`, asked the user, and made no remember/correct/retract call. Version 2 stayed current |
| Native default backup/restore command | Passed age encryption, wrong-key/changed-manifest denial, refusal to overwrite an existing database, decryption, retained history and project denial |

The four model-driven scenarios used the existing, owner-authorized cloud route
and invented information. The cloud credential was passed only to the child
process, never saved in the test profile or printed. Each run restored the test
profile's previous model settings. These results qualify those specific runs;
they do not guarantee that every model will always select or correct memory well.

The initial correction checker rejected a legitimate sentence that mentioned the
superseded eleven-day interval as history. Inspection showed a correct nine-day
current decision and a committed version change. The checker now checks the
current decision clause rather than banning the old word everywhere. The trace
and independent database history check are recorded, not disguised as an earlier
unmodified automated-check success.

A process snapshot measured roughly 314 MiB resident memory for the search/API
process and 24 MiB for the PostgreSQL parent. These exclude database backends,
the Unsloth/model server, filesystem cache and other applications. They are not
a full machine resource budget or a sustained-load result.

## Local chat-model prerequisite

The existing Unsloth endpoint is reachable from Ubuntu-Hermes and advertises the
owner's configured local models. The loaded Granite model reported an 8,192-token
serving window. This Hermes version requires at least 64,000 tokens.

The first chat reached the local endpoint and exceeded its 8,192-token window.
Once Hermes detected the window, subsequent startup correctly refused it. Moving
to an empty workspace did not remove that requirement. Hermes' `--ignore-rules`
also skips memory, so it is not a valid way to qualify this integration.

Recommendation: keep the lightweight local embedding model for search. Before
using a local chat model with this Hermes version, configure and verify an actual
serving window of at least 64,000 tokens and measure resource use. A larger model
is not inherently required. Its advertised native maximum is not proof that the
current serving process has that window. No Unsloth settings or Hermes safety
guards were changed. Local automatic capture remains unqualified. The existing
authorized cloud route is a tested alternative for the separate synthetic profile.

## Repairs found by testing published delivery

An inherited `*_backup.*` ignore rule excluded the new operator backup module and
its test. Explicit exceptions now include both in GitHub delivery. The native
restore path also needed an explicit fresh database name; the Docker fixture's
custom restore command had masked that omission. Both repairs were pushed and
pulled from GitHub before the native default-command and 69-check runs passed.
The incomplete synthetic restore and all prior fixtures were retained.

The CI image check now provisions and uses a generated restricted database role
instead of starting the application with the database operator credential. YAML
and embedded launcher syntax were checked locally. This is not a remote CI pass.

## Remaining release and private-use requirements

- Full legacy transport consolidation, graph/index workers, derived-store
  correction handling and default-stack failure/load qualification remain open.
- The image advisory gates remain open. The dated Debian image scans still have
  high OS findings, and the full image retains the version-matched Cognee advisory
  despite its tested backport. This native test does not clear container scans.
- Local chat use needs the serving-window adjustment described above. The test
  profile's restored local setting currently fails that Hermes prerequisite.
- Agent and test service share an OS user. File modes do not protect service
  administrator/encryption secrets from another process running as that user.
  Establish a separate operator/service boundary before admitting private data.
- Historical credential revocation, password-manager recovery custody, a chosen
  private backup destination/schedule and expiring-token renewal still need
  operational completion. Existing whole-WSL backups are not evidence of those
  individual steps. No real backup destination or upload was activated.
- Review the synthetic results before connecting the everyday profile or other
  projects. Retraction retains encrypted history; no permanent erasure was added.

No merge to main has been performed. The owner's conditional merge approval is
recorded; another publication/merge approval is not being requested.

## Evidence and reproduction

See `remediation-evidence/2026-10-20-hermes-live-summary.json`, the dated native
69-check XML/log and the separate native backup XML/log. Runtime source hashes
and exact tested revisions are in the summary. Raw cloud traces and generated
secrets stay in the private Hermes test runtime.

`tests/qualification/hermes_live_smoke.py` runs under an installed Hermes
interpreter with the dedicated profile active. It calls the actual provider and
service without a chat-model call. The normal pytest lane also runs on the native
cluster when an explicit disposable database and prepared model cache are supplied.

`tests/qualification/hermes_model_smoke.py` is an opt-in full-chat runner, excluded
from pytest/CI. Its `--use-configured-cloud` flag deliberately requires the
operator to select the existing cloud route. It never provisions a new provider
or transfers a cloud credential into a profile file. Its scenarios use the seeded
Cedar fixture in order: recall, correction, uncertain change. Start with an
eleven-day seed when repeating the correction scenario.
