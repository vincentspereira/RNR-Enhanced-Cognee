# Owner recovery custody and credential-review checkpoint

Date: 22 October 2026. Current protected configuration custody has been checked
through the owner's guided terminal, password-manager and OneDrive workflow.
This supersedes earlier pending-custody statements for these selected current
files only. Credential ownership/revocation and everyday activation remain open.
No private key, password, encrypted attachment or private global instructions
are included in this report.

## Recovery evidence

- The owner inventoried 12 protected files in /etc/enhanced-cognee. These include
  the operator/API/worker/backup configurations, database credentials, store
  configuration/ACLs and the private age recovery identity. JSON setting-name
  inspection identified the memory master key, persistent index key, JWT secret,
  backup recipient, manifest signing key/ID and role-specific credentials.
- The owner created a fresh passphrase-encrypted age package of that directory
  using a tar-to-age pipe, with no plaintext archive file written. Existing keys,
  credentials and service configuration were retained unchanged.
- Owner-run decryption and streaming tar comparison reported all 12 protected
  file contents matched their current originals. The comparison did not extract
  keys or display their values. It is a byte-content check, not a separate test
  of restoration permissions/ACLs on a new host.
- The encrypted package was transferred by the Windows operator to Windows
  staging without adding a mount/share or granting Hermes Windows access. The
  owner-run transfer verified source/copy SHA256 before attachment.
- The owner attached the package to a dedicated entry in the original KeePassXC
  vault, saved it, and copied that updated encrypted vault to a new dated OneDrive
  recovery folder while retaining the earlier version. Upload completion was
  owner-reported.
- The owner explicitly reported downloading the updated vault through the
  OneDrive website, unlocking that downloaded copy with the written vault master
  passphrase, and finding the Cognee entry and attachment. This remote-download
  provenance is owner-reported; the implementation session did not observe the
  browser. The recovered attachment was exported to a separate Windows folder.
- The implementation session independently compared the exported attachment
  against the verified Windows staging package using SHA256: PASS. A temporary
  filename discrepancy was resolved; no package content was changed by this
  session. Other unrelated files in the verification directory were not used.
- The owner then used the package password from the downloaded vault to decrypt
  the byte-identical Hermes package to /dev/null. The supplied terminal result
  was `Recovered-vault package password: PASS`. No secret values were supplied.

This establishes checked owner custody for the selected current recovery files,
including an independently downloaded vault/attachment and a working recovered
package password. It does not establish custody of unknown legacy keyrings,
restore a complete machine, prove current service health, or replace the earlier
20 October disposable canonical-data/history/index restore evidence. The written
vault master passphrase must remain independently available. No temporary files
or older vault/backup generations were deleted.

## Historical credential provenance

Read-only local Git inspection confirms the eight non-placeholder candidates
selected in evidence/historical-secret-triage.json are in commits already present
in the recorded upstream/main history:

| Source commit | Date | Selected candidate labels |
|---|---|---|
| 81b6cc192041b71b7c4b0a14121831d52cc3ce83 | 17 August 2023 | OPENAI_API_KEY, PINECONE_API_KEY, GPLACES_API_KEY, REPLICATE_API_TOKEN, SERPAPI_API_KEY, ZAPIER_NLA_API_KEY, WEAVIATE_API_KEY |
| 8cbf488e59ad1f814a71c96413ec40d87f918e67 | 12 March 2024 | destination.qdrant.credentials.api_key |

These inherited-history facts do not prove current key validity, account
ownership, revocation or absence of reuse. No candidate was sent to a provider
or tested for validity. Values/prefixes were not displayed. The eight candidates
are a selected subset of the historical scanner findings, not a claim that all
61 matches are real credentials or that the entire review is closed.

## Guided owner review: current checkpoint

| Provider | Owner report | Disposition so far |
|---|---|---|
| OpenAI | Has not personally created an OpenAI API key | No owner-created key reported; inherited candidate is not marked revoked; current reuse remains to be checked |
| Google Maps/Places | No key created or received | No owned key reported; not marked revoked |
| Pinecone | No key created or received | No owned key reported; not marked revoked |
| Replicate | Created a key for RNR Spatial Engine, not Enhanced Cognee | Local configured-token comparison differs from the inherited Cognee candidate; no revocation justified by this match check |
| SerpAPI | No key created or received | No owned key reported; not marked revoked |
| Zapier NLA | No key created or received | No owned key reported; not marked revoked |
| Weaviate | No key created or received | No owned key reported; not marked revoked |
| Qdrant credential in historical DLT settings | Both prior services were local: Enhanced Cognee at localhost:26333, another project at localhost:6333 | Workspace Cognee QDRANT_API_KEY differs from the upstream candidate; second project/key not identified or compared; no Qdrant Cloud revocation step identified; protected Hermes keys are separate |

The Replicate comparison read only the REPLICATE_API_TOKEN assignment from
Spatial's documented local secret source, ~/.config/rnr/env.sh. The literal
value was compared locally against the REPLICATE_API_TOKEN assignment at
81b6cc192041b71b7c4b0a14121831d52cc3ce83:level_2/.env. Result: DIFFERENT.
No values/prefixes/digests were displayed or added here, no configuration was
changed, and no provider request was made. This comparison does not inspect all
Spatial deployments, old tokens or every other possible exposure. It does not
prove a currently running process uses that file's present value.

A subsequent value-free local check compared the historical Qdrant candidate
against the QDRANT_API_KEY literal in the Workspace Cognee .env: DIFFERENT.
None of the eight selected historical candidate strings appeared in that .env
or the documented shared Spatial provider file. Other enumerated root-local
.env variants and .dlt/secrets.toml were absent. These checks read files only;
there were no provider requests, credential changes or value disclosures. They
do not inspect the protected Hermes configuration, every deployed process,
unknown second Qdrant consumer, or all other configurations/history findings.

The owner clarified that both older Qdrant services were local: Cognee used
localhost:26333 and the other project localhost:6333. A read-only Workspace
configuration check confirms the Cognee .env selects a loopback host and port
26333. Neither port was visible as listening in this implementation session,
and Docker metadata was unavailable. That observation is not proof that a host
service is stopped, nor permission to start/stop/reconfigure it. No service,
key, mount or network setting was changed.

No owner-key exposure has been confirmed from the selected candidates and
comparisons so far; the known owned configured Replicate and Workspace Cognee
Qdrant credentials differ from their respective inherited candidates. This does
not clear all credentials, the unidentified second local Qdrant key, or every
historical scanner match. Do not revoke unrelated working keys to satisfy an
inherited-history finding or claim a Qdrant Cloud revocation was performed.
Local rotation, if evidence warrants it later, needs a coordinated server/client
cutover rather than an unrelated provider dashboard.

Next, continue read-only readiness checks for the already installed protected
Hermes service while keeping remaining credential/configuration coverage
explicit. Compare any owned/current credentials through an approved local
process without exposing values. Revoke exposed owned credentials;
replace only those needed by current consumers. An inherited/not-owned finding
must not be marked revoked or tested. Unknown ownership remains unresolved. If
an inherited key was copied into a current config, remove that dependency through
a coordinated replacement using an owned credential or approved local route;
do not revoke another owner's key. The selected review remains incomplete.

## Work still separate

- Credential classification, any owned-key revocation and consumer cutover.
- Current Hermes service/profile privilege/renewal admission, remaining frontend
  dependency and exact-candidate release checks, and everyday/bot rollout.
- V12 corrected-runtime native rerun, first complete normal backup, provider
  recovery review and actual scheduled execution. V12 remains paused and v11
  remains scheduled; this checkpoint starts no backup or profile activation.

## Current host/profile readiness checkpoint

Latest owner update: the owner explicitly approved the restricted account and
initial profile and required eventual coverage of all 40-plus bots and every
other Hermes profile after testing. This supersedes the earlier deferral quoted
below for account/profile preparation. The updated live-profile account plan
records the received approval and staged fleet objective. This Workspace update
did not create an Ubuntu-Hermes account, change a running profile or prove
private readiness. Initial qualification still uses invented data; existing
profiles, service/recovery keys and backup generations remain preserved.

The owner-run systemctl query reports the API, indexing worker and backup timer
active. Main-profile path checks report ~/.hermes exists and its Cognee plugin
and settings file are absent. The current account includes sudo and docker;
the filtered ordinary/hermes-named account inventory returned only
vincentspereira. These checks do not establish a restricted everyday runtime,
authenticated recall or a new provider/model qualification. No profile/account
was changed. A concrete restricted-runtime account proposal is available in
[the live-profile account plan](../../../runbooks/HERMES-LIVE-PROFILE-ACCOUNT-PLAN.md).
The proposed persistent identity is separate from the already removed temporary
test account. At the earlier checkpoint the owner chose "Keep the current setup
for invented-data testing only". That earlier choice deferred account creation
and private/everyday activation. It has now been superseded for account/profile
preparation as stated above; it never established private-use qualification.
Preserve the administrator account, existing bots, protected services and backups
while preparing the newly approved account and initial invented-data profile.
With the new account approval, explicit new-home backup coverage is required
before private use. Current-profile privilege limitations and other private-use
prerequisites remain recorded rather than bypassed.
