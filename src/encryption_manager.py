"""
Encryption Manager - Phase 14.3
=================================
Provides transparent at-rest encryption/decryption for memory content stored
in PostgreSQL.  Each memory can be independently encrypted with a per-tenant
or global key.  Key rotation is supported by re-encrypting all rows.

CRYPTOGRAPHY (RNR Enhanced Cognee):
  - New data is encrypted with **AES-256-GCM** (authenticated encryption,
    256-bit key, fresh 96-bit nonce per message).  Ciphertext is stored with
    the "enc2:" prefix.
  - Legacy data encrypted with Fernet (AES-128-CBC + HMAC-SHA256, "enc:"
    prefix) is still DECRYPTED transparently for backward compatibility, so
    existing rows remain readable after the upgrade with no migration step.
  - Key rotation re-encrypts every row to AES-256-GCM under the new key.
  - The AES-256 key is derived from the supplied master key via HKDF-SHA256,
    so the existing master-key configuration is reused unchanged.

Dependencies: cryptography (pip install cryptography)
Falls back gracefully if cryptography is not installed (plain-text mode).

ASCII-only output. No Unicode symbols.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, Optional


# Multi-tenant helper -- routes Postgres reads/writes to the per-tenant
# table when a TenantContext is active. See src/multi_tenant.py.
def _t_docs() -> str:
    from src.multi_tenant import tenant_scoped_table
    return tenant_scoped_table("shared_memory.documents")


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional cryptography import
# ---------------------------------------------------------------------------

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    logger.warning(
        "WARN cryptography package not installed. "
        "EncryptionManager running in plain-text mode. "
        "Install with: pip install cryptography"
    )

# Prefixes used to mark ciphertext so we can detect encrypted vs plain-text
# rows AND route decryption to the correct algorithm.
_ENC_PREFIX = "enc:"   # legacy Fernet (AES-128-CBC + HMAC-SHA256)
_GCM_PREFIX = "enc2:"  # AES-256-GCM (current default)

_GCM_NONCE_LEN = 12  # 96-bit nonce, the AEAD standard for GCM
_HKDF_INFO = b"enhanced-cognee.encryption.v2.aes-256-gcm"

# Algorithm label reported by get_encryption_stats() and tooling.
_ALGORITHM = "AES-256-GCM"


def _derive_aes_key(master_key_bytes: bytes) -> bytes:
    """Derive a 32-byte AES-256 key from the master key via HKDF-SHA256.

    The master key (e.g. a 32-byte Fernet-format key) is used as input keying
    material.  HKDF yields a dedicated, independent 256-bit AES key so the same
    master key can also continue to drive legacy Fernet decryption without key
    reuse across algorithms.
    """
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_HKDF_INFO,
    ).derive(master_key_bytes)


class EncryptionManager:
    """
    Transparent at-rest encryption/decryption for shared_memory.documents.

    New content is encrypted with AES-256-GCM ("enc2:" prefix). Legacy Fernet
    content ("enc:" prefix) is decrypted transparently for backward
    compatibility, so no data migration is required to read existing rows.

    When cryptography is not installed the class operates in pass-through
    mode: encrypt() returns the plaintext unchanged and decrypt() returns
    the ciphertext unchanged.  All async methods degrade gracefully when
    the database pool is unavailable.

    Usage::

        mgr = EncryptionManager(postgres_pool=pool)
        ciphertext = mgr.encrypt("secret data")     # -> "enc2:..."
        plaintext  = mgr.decrypt(ciphertext)
        await mgr.encrypt_memory("some-uuid")
        stats = await mgr.get_encryption_stats()
        result = await mgr.rotate_encryption_key()
    """

    def __init__(
        self,
        postgres_pool: Any = None,
        master_key: Optional[str] = None,
    ) -> None:
        """
        Initialize EncryptionManager.

        Args:
            postgres_pool: An asyncpg connection pool.  May be None; async
                           methods will return error dicts in that case.
            master_key:    Base64-urlsafe 32-byte key (as a str). Reused as
                           HKDF input keying material for AES-256-GCM and as
                           the Fernet key for legacy decryption.  When omitted
                           a fresh key is generated automatically (if
                           cryptography is installed).
        """
        self.pool = postgres_pool
        self._enabled: bool = _CRYPTO_AVAILABLE

        if not self._enabled:
            self._fernet: Any = None
            self._aesgcm: Any = None
            self._raw_key: Optional[bytes] = None
            return

        if master_key:
            key_bytes = master_key.encode() if isinstance(master_key, str) else master_key
        else:
            key_bytes = Fernet.generate_key()
            logger.info(
                "INFO EncryptionManager: no master_key provided - generated a new key"
            )

        self._raw_key = key_bytes
        # Fernet is retained solely to DECRYPT legacy "enc:" rows.
        self._fernet = Fernet(key_bytes)
        # AES-256-GCM is the default for all NEW encryption.
        self._aesgcm = AESGCM(_derive_aes_key(key_bytes))
        logger.debug("EncryptionManager initialized with AES-256-GCM")

    # ------------------------------------------------------------------
    # Synchronous encrypt / decrypt
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string with AES-256-GCM.

        Returns the original string unchanged when encryption is disabled.
        Encrypted output is prefixed with "enc2:" so it can be detected and
        routed later.  A fresh 96-bit nonce is generated for every call, so
        encrypting the same value twice yields different ciphertext.
        """
        if not self._enabled or not plaintext:
            return plaintext

        try:
            nonce = os.urandom(_GCM_NONCE_LEN)
            ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
            token = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
            return _GCM_PREFIX + token
        except Exception as exc:
            logger.error("encrypt failed: %s", exc)
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string, auto-routing by prefix.

        - "enc2:" -> AES-256-GCM (current default).
        - "enc:"  -> legacy Fernet (backward compatibility).
        - anything else -> returned unchanged (already plaintext).

        Returns the original value unchanged when encryption is disabled.
        """
        if not self._enabled or not ciphertext:
            return ciphertext

        if ciphertext.startswith(_GCM_PREFIX):
            try:
                raw = base64.urlsafe_b64decode(
                    ciphertext[len(_GCM_PREFIX):].encode("ascii")
                )
                nonce, body = raw[:_GCM_NONCE_LEN], raw[_GCM_NONCE_LEN:]
                plaintext = self._aesgcm.decrypt(nonce, body, None)
                return plaintext.decode("utf-8")
            except Exception as exc:
                logger.error("decrypt failed: %s", exc)
                return ciphertext

        if ciphertext.startswith(_ENC_PREFIX):
            try:
                token_str = ciphertext[len(_ENC_PREFIX):]
                plaintext = self._fernet.decrypt(token_str.encode("ascii"))
                return plaintext.decode("utf-8")
            except Exception as exc:
                logger.error("decrypt failed: %s", exc)
                return ciphertext

        return ciphertext

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    async def _ensure_column(self, conn: Any) -> None:
        """Add is_encrypted column to documents if it does not exist."""
        await conn.execute(
            f"""
            ALTER TABLE {_t_docs()}
                ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT FALSE
            """
        )

    # ------------------------------------------------------------------
    # Async DB operations
    # ------------------------------------------------------------------

    async def encrypt_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Fetch, encrypt, and persist the content of a single memory row.

        Args:
            memory_id: The UUID string of the memory to encrypt.

        Returns:
            Dict with "memory_id" and "ok" True on success, or "error" key
            on failure.
        """
        if not self._enabled:
            return {"memory_id": memory_id, "error": "encryption not enabled (cryptography not installed)"}

        if not self.pool:
            return {"memory_id": memory_id, "error": "No database pool"}

        try:
            async with self.pool.acquire() as conn:
                await self._ensure_column(conn)

                row = await conn.fetchrow(
                    f"SELECT content, is_encrypted FROM {_t_docs()} WHERE id = $1",
                    memory_id,
                )
                if row is None:
                    return {"memory_id": memory_id, "error": "memory not found"}

                if row["is_encrypted"]:
                    return {"memory_id": memory_id, "ok": True, "note": "already encrypted"}

                encrypted = self.encrypt(row["content"])
                await conn.execute(
                    f"""
                    UPDATE {_t_docs()}
                       SET content = $1, is_encrypted = TRUE, updated_at = NOW()
                     WHERE id = $2
                    """,
                    encrypted,
                    memory_id,
                )

            logger.debug("encrypt_memory OK for %s", memory_id)
            return {"memory_id": memory_id, "ok": True}
        except Exception as exc:
            logger.error("encrypt_memory failed for %s: %s", memory_id, exc)
            return {"memory_id": memory_id, "error": str(exc)}

    async def get_encryption_stats(self) -> Dict[str, Any]:
        f"""
        Return aggregate encryption statistics for {_t_docs()}.

        Returns:
            Dict with total_memories, encrypted_memories, encryption_enabled,
            and algorithm keys.
        """
        if not self.pool:
            return {
                "total_memories": 0,
                "encrypted_memories": 0,
                "encryption_enabled": self._enabled,
                "algorithm": _ALGORITHM,
                "error": "No database pool",
            }

        try:
            async with self.pool.acquire() as conn:
                await self._ensure_column(conn)
                row = await conn.fetchrow(
                    f"""
                    SELECT
                        COUNT(*)                                            AS total,
                        COUNT(*) FILTER (WHERE is_encrypted = TRUE)        AS encrypted
                    FROM {_t_docs()}
                    """
                )

            return {
                "total_memories": int(row["total"]) if row else 0,
                "encrypted_memories": int(row["encrypted"]) if row else 0,
                "encryption_enabled": self._enabled,
                "algorithm": _ALGORITHM,
            }
        except Exception as exc:
            logger.error("get_encryption_stats failed: %s", exc)
            return {
                "total_memories": 0,
                "encrypted_memories": 0,
                "encryption_enabled": self._enabled,
                "algorithm": _ALGORITHM,
                "error": str(exc),
            }

    async def rotate_encryption_key(
        self, new_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rotate the master encryption key.

        Fetches all encrypted rows, decrypts them with the current key
        (auto-routing enc:/enc2:), re-encrypts with the new key as
        AES-256-GCM (enc2:), and persists.  Atomicity is row-level (not a
        single transaction) to avoid long locks on large tables.  After a
        successful rotation every row is AES-256-GCM.

        Args:
            new_key: Base64-urlsafe 32-byte key string (reused as HKDF input
                     for AES-256-GCM and as the Fernet key for any legacy
                     rows).  When omitted a fresh key is generated.

        Returns:
            Dict with "rotated" count and "new_key_preview" (first 8 chars
            of the raw key + "..."), or "error" key on failure.
        """
        if not self._enabled:
            return {"error": "encryption not enabled (cryptography not installed)"}

        if not self.pool:
            return {"error": "No database pool"}

        # Prepare the new key material + derived AES-256-GCM cipher.
        if new_key:
            new_key_bytes = new_key.encode() if isinstance(new_key, str) else new_key
        else:
            new_key_bytes = Fernet.generate_key()

        new_fernet = Fernet(new_key_bytes)                    # for legacy decrypt
        new_aesgcm = AESGCM(_derive_aes_key(new_key_bytes))   # new default
        new_key_preview = new_key_bytes.decode("ascii")[:8] + "..."

        rotated = 0
        try:
            async with self.pool.acquire() as conn:
                await self._ensure_column(conn)

                rows = await conn.fetch(
                    f"""
                    SELECT id, content
                      FROM {_t_docs()}
                     WHERE is_encrypted = TRUE
                    """
                )

            for row in rows:
                try:
                    # Decrypt with the CURRENT key (auto-routes enc:/enc2:).
                    plaintext = self.decrypt(row["content"])
                    # Re-encrypt with the NEW key as AES-256-GCM (enc2:).
                    nonce = os.urandom(_GCM_NONCE_LEN)
                    ciphertext = new_aesgcm.encrypt(
                        nonce, plaintext.encode("utf-8"), None
                    )
                    new_ciphertext = (
                        _GCM_PREFIX
                        + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")
                    )

                    async with self.pool.acquire() as conn:
                        await conn.execute(
                            f"""
                            UPDATE {_t_docs()}
                               SET content = $1, updated_at = NOW()
                             WHERE id = $2
                            """,
                            new_ciphertext,
                            row["id"],
                        )
                    rotated += 1
                except Exception as row_exc:
                    logger.error(
                        "rotate_encryption_key: failed to rotate memory %s: %s",
                        row["id"],
                        row_exc,
                    )

            # Switch to the new key after all rows are updated.
            self._raw_key = new_key_bytes
            self._fernet = new_fernet
            self._aesgcm = new_aesgcm
            logger.info(
                "INFO rotate_encryption_key: rotated %d memories to new key (%s)",
                rotated,
                new_key_preview,
            )
            return {"rotated": rotated, "new_key_preview": new_key_preview}
        except Exception as exc:
            logger.error("rotate_encryption_key failed: %s", exc)
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_instance: Optional[EncryptionManager] = None


def init_encryption_manager(
    postgres_pool: Any = None,
    master_key: Optional[str] = None,
) -> EncryptionManager:
    """
    Create and register the global EncryptionManager singleton.

    Args:
        postgres_pool: asyncpg connection pool.
        master_key:    Optional base64-urlsafe 32-byte key string (reused as
                       HKDF input for AES-256-GCM and as the legacy Fernet key).

    Returns:
        The newly created EncryptionManager instance.
    """
    global _instance
    _instance = EncryptionManager(postgres_pool=postgres_pool, master_key=master_key)
    logger.info(
        "OK EncryptionManager initialized (enabled=%s)",
        _instance._enabled,
    )
    return _instance


def get_encryption_manager() -> Optional[EncryptionManager]:
    """
    Return the global EncryptionManager singleton.

    Returns:
        The EncryptionManager instance, or None if init_encryption_manager
        has not been called yet.
    """
    return _instance
