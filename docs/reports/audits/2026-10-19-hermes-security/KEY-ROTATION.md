# Canonical memory key rotation

Status: implemented and tested with invented keys and disposable PostgreSQL.
Existing private data, service settings and recovery keys have not been changed.
This applies to the restricted canonical memory service, not every legacy store.

## What this means for Vincent

Each encryption key can now have a short name. The service can keep older keys
available to read existing memories while using a new key for new memories. A
separate operator command can then protect the current records and their retained
history with the new key. A failed batch rolls back together, preserving the
previous readable state.

Recommended: retain old keys in protected recovery storage until all projects,
retained history and backup copies have been checked. Removing a key too early
can make an older backup unreadable. Rotation does not remove old keys, change
backups, erase history, or decide who holds the recovery copy.

Hermes must receive only its scoped service token. It must not receive encryption
keys, the keyring configuration, database credentials, or the rotation command.
An agent with access to the service's operating-system account or administrator
powers could bypass that separation; service placement must account for this.

## Operator configuration and sequence

The service accepts `ENHANCED_MEMORY_KEYRING_JSON`, containing exactly `active`
and `keys`. `active` names one key in the `keys` object. Each value is a separately
generated valid Fernet-format master key, as accepted by the existing encryption
manager. Use short lowercase identifiers such as `key_october`. Key material
belongs in the service's protected secret configuration, never Git, notebooks,
commands saved in chat, or the non-secret Hermes profile file.

Existing deployments can continue using `ENCRYPTION_MASTER_KEY`. During a staged
move to named keys, retain that setting for previously unnamed `enc2:`/`enc:` data.
Named records use `enc2:kid:<key-name>:<authenticated-ciphertext>`. An unknown key
name, invalid ring, missing legacy key or failed decryption causes failure; there
is no plaintext fallback or guessing between unrelated keys.

1. Check an owner-managed recovery copy and restore a disposable backup with its
   retained key before changing a real deployment.
2. Supply the new keyring to the service operator. Keep existing keys available
   and select the new key for new writes. Confirm the authenticated status reports
   the intended `encryption_key_id`.
3. Use the operator environment to preview one named project's batch:

   ```bash
   python -m src.memory_key_rotation --tenant <tenant_id> --project <project_id> --actor <operator_id>
   ```

4. Review the counts, then rerun with `--apply` to commit that batch. Follow
   `next_after_id` using `--after-id` for later batches. Do this for every approved
   project; the command deliberately does not guess all project ownership.
5. Repeat the complete project scan from the beginning after a deployment-wide
   writer switch. Confirm no payloads need rewrapping. Otherwise an old service
   process could still create old-key records behind the pagination cursor.
6. Recheck current reads, retained history, project denial and a separately
   restored backup. Keep old keys until the recovery/retention decision allows
   retirement. No key-retirement or deletion command is implemented.

The operator must ensure all service writers use the intended active key before
retiring a key. Mixed-key reads permit a staged rollout but do not replace this
coordination. Key changes require service restart/configuration reload through
the normal deployment procedure; keys are not changed through an agent API.

## Limits and evidence

The command locks selected canonical rows in the same order as mutations,
including retracted records. It validates at most 500 current records and 5,000
historical versions per batch, with a 16 MiB encrypted-payload budget checked
before fetching payloads. Reduce the batch if it exceeds a limit. An individual
record with an unusually large history needs separate reviewed handling.

All selected ciphertexts must decrypt before writes begin. Updates and the audit
event commit in one transaction. IDs, versions, content, source declarations,
sharing grants and change-feed events are preserved. Rotation is retriable;
already current-key payloads are checked but not rewritten. Dry-run takes short
database locks to obtain a consistent selection, so use a suitable operator
window and bounded batches.

Qualification covers old-key reads, named-key writes, missing-key denial, invalid
configuration, dry-run preservation, a failure after the first attempted update,
full batch rollback, current/history readability with the new key, unchanged
other-project ciphertext, stable versions and repeat-run idempotence. This is not
evidence that Vincent's private recovery arrangement is already operational.
