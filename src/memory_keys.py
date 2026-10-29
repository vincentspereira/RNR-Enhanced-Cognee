"""Named canonical-memory keys support staged rotation without plaintext fallback.

The keyring is service/operator configuration, never an agent-visible setting.
Keep retired keys until retained history and separately stored backups have been
reviewed. This module does not delete keys or rewrite any stored record.
"""
from __future__ import annotations

import json
import os
import re

from src.encryption_manager import EncryptionManager

PREFIX = "enc2:kid:"


class MemoryKeyring:
    def __init__(self, keys: dict[str, str], active: str, *, legacy_key: str | None = None):
        if (not isinstance(keys, dict) or not 1 <= len(keys) <= 16
                or any(not isinstance(k, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", k)
                       or not isinstance(v, str) for k, v in keys.items())
                or active not in keys or len(set(keys.values())) != len(keys)):
            raise ValueError("Invalid named memory-key configuration")
        self.active = active
        self._keys = {name: EncryptionManager(master_key=key) for name, key in keys.items()}
        self._legacy = EncryptionManager(master_key=legacy_key) if legacy_key else None
        if not all(cipher._enabled for cipher in self._keys.values()) or (self._legacy and not self._legacy._enabled):
            raise RuntimeError("Required memory-key encryption is unavailable")
        self._enabled = True

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            raise ValueError("Canonical encryption requires nonempty content")
        encoded = self._keys[self.active].encrypt(plaintext)
        if not encoded.startswith("enc2:"):
            raise RuntimeError("Protected memory encryption did not produce an authenticated envelope")
        return PREFIX + self.active + ":" + encoded.removeprefix("enc2:")

    @staticmethod
    def key_id(ciphertext: str) -> str | None:
        if ciphertext.startswith(PREFIX):
            parts = ciphertext.split(":", 3)
            if len(parts) != 4 or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", parts[2]) or not parts[3]:
                raise ValueError("Invalid named-key memory envelope")
            return parts[2]
        if ciphertext.startswith(("enc2:", "enc:")):
            return None
        raise ValueError("Protected memory requires an encrypted envelope")

    def decrypt(self, ciphertext: str) -> str:
        ident = self.key_id(ciphertext)
        if ident is None:
            if self._legacy is None:
                raise RuntimeError("The retained legacy memory key is required")
            return self._legacy.decrypt(ciphertext)
        cipher = self._keys.get(ident)
        if cipher is None:
            raise RuntimeError("A retained memory key is unavailable")
        return cipher.decrypt("enc2:" + ciphertext.split(":", 3)[3])


def canonical_cipher_from_environment():
    """Select exactly the operator-configured cipher; invalid rings never fall back."""
    ring = os.getenv("ENHANCED_MEMORY_KEYRING_JSON")
    if ring is not None:
        try:
            settings = json.loads(ring)
            if not isinstance(settings, dict) or set(settings) != {"keys", "active"}:
                raise ValueError
            return MemoryKeyring(settings["keys"], settings["active"],
                                 legacy_key=os.getenv("ENCRYPTION_MASTER_KEY") or None)
        except Exception:
            raise ValueError("Invalid memory keyring configuration; startup refused") from None
    key = os.environ["ENCRYPTION_MASTER_KEY"]
    if not key:
        raise ValueError("A persistent encryption master key is required")
    return EncryptionManager(master_key=key)
