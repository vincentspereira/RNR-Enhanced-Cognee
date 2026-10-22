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
| SerpAPI | Not yet reviewed | Pending owner response |
| Zapier NLA | Not yet reviewed | Pending owner response |
| Weaviate | Not yet reviewed | Pending owner response |
| Qdrant credential in historical DLT settings | Not yet reviewed | Pending owner response; distinguish any hosted account from newly generated local service keys |

The Replicate comparison read only the REPLICATE_API_TOKEN assignment from
Spatial's documented local secret source, ~/.config/rnr/env.sh. The literal
value was compared locally against the REPLICATE_API_TOKEN assignment at
81b6cc192041b71b7c4b0a14121831d52cc3ce83:level_2/.env. Result: DIFFERENT.
No values/prefixes/digests were displayed or added here, no configuration was
changed, and no provider request was made. This comparison does not inspect all
Spatial deployments, old tokens or every other possible exposure. It does not
prove a currently running process uses that file's present value.

Next, review SerpAPI ownership. Continue classifying candidates and actual
consumers privately. Compare any owned/current credentials through an approved
local process without exposing values. Revoke exposed owned credentials;
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
