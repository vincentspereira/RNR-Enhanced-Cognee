# Credential review and owner recovery custody

Prepared 20 October 2026. This procedure supports phase 0 and private-activation
acceptance. It does not record a completed revocation, owner transfer or restore.
Keep account-specific inventories, values and raw evidence private, outside Git.

## Two different operations

Exposed provider credentials should be revoked by the account owner. Create a
replacement only if a current application still needs that provider. Historical
scanner findings are candidates, not proof of ownership or active credentials.
An inherited key that is not owned must never be tested or labelled revoked by
this operator. Record uncertain ownership/status honestly.

Encryption and backup recovery material must remain available to recover old
records. Generating a fresh memory key does not decrypt earlier ciphertext.
Preserve retained keys/IDs and follow the tested rotation runbook for a migration.
Do not rerun create-config over an existing deployment as a custody shortcut.

## Credential review

1. Use the existing sanitized audit metadata to identify provider, historical
   location and key label. Do not reproduce historical values in chat/logs.
2. Review only accounts the owner controls, using the provider's authenticated
   key dashboard/account inventory. Never send a candidate to a provider to test
   validity. A private owner inspection can resolve metadata if necessary.
3. Classify each candidate as owned/current, owned/unused, already revoked or
   expired, not-owned/inherited, or unresolved. Not remembering an account is
   not evidence of revocation. Do not create accounts for inherited findings.
4. Revoke exposed owned credentials promptly. If still required, issue a scoped
   replacement, update the actual consumer and review the account's usage.
   Coordinate cutovers with the host session operating that consumer; do not
   interrupt an active model/deployment test with an unannounced config change.
5. Update the real ignored local configuration, profile secret mechanism,
   deployment secret store or Actions secret, as applicable. Editing historical
   Git files, instructions or a vault entry does not revoke a provider key.
6. Record provider/key label, disposition, date and evidence reference without
   values. Unresolved and inherited outcomes must not be counted as revocation.
   History rewriting is separate and has not been authorized as a substitute.

## New service configuration versus owner recovery

The supplied service templates use /etc/enhanced-cognee/api.json, worker.json and
backup.json as protected role-specific credential sources. The installed host
must report its actual paths. Do not treat template paths as a live inventory.
Hermes receives only its scoped ENHANCED_COGNEE_ACCESS_TOKEN through its profile's
supported secret store, never the operator, signing or decryption configuration.

Keep a recoverable private record of:

- Memory master key or complete named keyring, including keys needed by retained
  history/backups and their identifiers.
- Persistent index key and pipeline/model configuration references.
- Backup manifest signing keys/IDs needed by each retained backup generation.
- Private age identity and corresponding public recipient reference; the public
  recipient alone cannot decrypt the backup.
- JWT signing arrangement when used, operator/database/store recovery entries
  and the role/namespace/configuration map needed for a deliberate restore.
- The separate Windows archive password if cloud archive generations use it.

Recommended: use the owner's existing trusted password manager; free KeePassXC
is an option if none is already in use. Store actual keys in protected entries
or attachments, not this runbook. Preserve an independently accessible encrypted
vault/bundle copy and separate unlock material. Do not keep the sole recovery
copy inside an archive whose only unlock secret is inside that same archive.

The operator must arrange an approved private owner transfer, using a supervised
non-recorded operator workflow or encrypted recovery export. Do not print keys
to an agent transcript, grant ordinary agents file access, relax service ACLs,
add mounts or move raw root keys into a bot's home for convenience. An export
file being generated does not establish that the owner independently holds it.
Record the transfer route/path privately and its completion as a sanitized fact.

Before private activation, the owner should open the independent recovery copy,
confirm the required entries/attachments exist and can be unlocked, and have a
disposable restore prove current records, retained history, index rebuild and
scope restrictions. Never restore over the live service for this drill.

## Completion evidence

Track credential review, account revocation, consumer update, private recovery
transfer, independent vault opening, service restore and Windows archive restore
separately. A credential audit has no authority to delete history/backup files.
No actual secret value, prefix or private recovery attachment belongs in a public
completion report. Provider labels, outcome dates and pass/fail/pending suffice.

## Supporting sources

- [OpenAI key safety](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)
- [Google Maps key restrictions and rotation](https://developers.google.com/maps/api-security-best-practices)
- [KeePassXC getting started](https://keepassxc.org/docs/KeePassXC_GettingStarted)
- [Canonical key rotation](../reports/audits/2026-10-19-hermes-security/KEY-ROTATION.md)
- [Canonical memory/index operations](CANONICAL-MEMORY-AND-INDEXES.md)
