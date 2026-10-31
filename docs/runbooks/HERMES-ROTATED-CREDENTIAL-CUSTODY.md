# Owner custody of the new rotated logins

Prepared 25 October 2026. This covers NEW authentication material. Reuse the
previously verified custody of unchanged encryption/recovery keys.

The protected encrypted package is `current-logins.json.age` under
`/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc/credential-custody-export`.
Its authenticated in-memory decryption already passed. Expected ciphertext SHA256:

```text
6951fd09ed6edcce2a3fc53f1d8f90861e8776c4a3663397091ff3e7327d4322
```

1. Run `release_launch_encrypted_custody_copy.py` through the prepared local
   sudo command. It reads only the verified ciphertext and places a separate
   owner-readable copy in a NEW private `/tmp/ec-owner-custody-*` folder. Use
   the returned `owner_file`. No decryption, key read, plaintext export, vault
   modification or credential change occurs. Original ciphertext is retained.
2. In your own KeePassXC application, unlock the existing local vault and create
   an entry named `Enhanced Cognee - rotated logins - 2026-10-25`.
3. Edit the entry, open Advanced / Attachments, and Add the returned `.age` file.
   Save the entry and local vault. KeePassXC stores attachments inside its
   encrypted database; see the [official attachment guide](https://keepassxc.org/docs/KeePassXC_UserGuide#_attachments).
4. In the entry notes, record the ciphertext SHA256 above and a reference to
   your existing Cognee AGE recovery-identity entry. Keep secret values out of
   notes/reports/chat. The attachment plus the previously stored matching AGE
   identity provides the recoverable credential package. This operation stores
   the package; individual service login fields are not populated automatically.
5. Save the attachment back out through KeePassXC to a separate owner-selected
   location, then verify that its SHA256 matches the value above with your local
   file-hash tool. Inside Ubuntu-Hermes, `sha256sum 'SAVED-ATTACHMENT-PATH'` prints
   only the ciphertext hash/path. Retain original packages and pickup copies.
6. Reply only `attached and verified` after saving and checking the new package.
   Never paste decrypted JSON, passwords, keys, vault passwords or screenshots
   containing them. Owner confirmation is separate from host encryption proof.

If a temporary pickup has disappeared, run the updated release helper again.
It releases the same hash-verified ciphertext into a new private pickup folder
and writes a uniquely named receipt, retaining earlier receipts. Use the NEW
`owner_file` returned by that execution; no credentials are rotated or decrypted.

The file picker must reach the owner copy from the machine where KeePassXC runs.
Hermes does not open another device's vault or add mounts/shares to reach it.
Use the existing approved owner file-pickup method if the GUI is on another
device. The vault's location/password are not required by the release helper.

The package contains current authentication fields for six protected config
groups. Encryption/index/backup-signing/AGE private keys were excluded from this
new export; existing key-custody and restore passes remain retained. No cloud
upload or re-enrollment is part of this procedure.
