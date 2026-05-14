"""
Encryption Manager - Phase 14.3
=================================
Provides transparent Fernet encryption/decryption for memory content stored
in PostgreSQL.  Each memory can be independently encrypted with a per-tenant
or global key.  Key rotation is supported by re-encrypting all rows.

Dependencies: cryptography (pip install cryptography)
Falls back gracefully if cryptography is not installed (plain-text mode).

ASCII-only output. No Unicode symbols.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional cryptography import
# ---------------------------------------------------------------------------

try:
    from cryptography.fernet import Fernet

    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    logger.warning(
        "WARN cryptography package not installed. "
        "EncryptionManager running in plain-text mode. "
        "Install with: pip install cryptography"
    )

# Prefix used to mark ciphertext so we can detect encrypted vs plain-text rows.
_ENC_PREFIX = "enc:"


class EncryptionManager:
    """
    Transparent Fernet encryption/decryption for shared_memory.documents.

    When cryptography is not installed the class operates in pass-through
    mode: encrypt() returns the plaintext unchanged and decrypt() returns
    the ciphertext unchanged.  All async methods degrade gracefully when
    the database pool is unavailable.

    Usage::

        mgr = EncryptionManager(postgres_pool=pool)
        ciphertext = mgr.encrypt("secret data")
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
            master_key:    Base64-urlsafe 32-byte Fernet key (as a str).
                           When omitted a fresh key is generated automatically
                           (if cryptography is installed).
        """
        self.pool = postgres_pool
        self._enabled: bool = _CRYPTO_AVAILABLE

        if not self._enabled:
            self._fernet: Any = None
            self._raw_key: Optional[bytes] = None
            return

        if master_key:
            key_bytes = master_key.encode() if isinstance(master_key, str) else master_key
        else:
            key_bytes = Fernet.generate_key()
            logger.info(
                "INFO EncryptionManager: no master_key provided - generated a new Fernet key"
            )

        self._raw_key: Optional[bytes] = key_bytes
        self._fernet = Fernet(key_bytes)
        logger.debug("EncryptionManager initialized with Fernet/AES-128-CBC")

    # ------------------------------------------------------------------
    # Synchronous encrypt / decrypt
    # ------------------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Returns the original string unchanged when encryption is disabled.
        Encrypted output is prefixed with "enc:" so it can be detected later.
        """
        if not self._enabled or not plaintext:
            return plaintext

        try:
            token: bytes = self._fernet.encrypt(plaintext.encode("utf-8"))
            return _ENC_PREFIX + token.decode("ascii")
        except Exception as exc:
            logger.error("encrypt failed: %s", exc)
            return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a Fernet-encrypted string.

        Returns the original value unchanged when:
        - encryption is disabled, or
        - the value does not start with the "enc:" prefix (already plaintext).
        """
        if not self._enabled or not ciphertext:
            return ciphertext

        if not ciphertext.startswith(_ENC_PREFIX):
            return ciphertext

        try:
            token_str = ciphertext[len(_ENC_PREFIX):]
            plaintext: bytes = self._fernet.decrypt(token_str.encode("ascii"))
            return plaintext.decode("utf-8")
        except Exception as exc:
            logger.error("decrypt failed: %s", exc)
            return ciphertext

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    async def _ensure_column(self, conn: Any) -> None:
        """Add is_encrypted column to documents if it does not exist."""
        await conn.execute(
            """
            ALTER TABLE shared_memory.documents
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
                    "SELECT content, is_encrypted FROM shared_memory.documents WHERE id = $1",
                    memory_id,
                )
                if row is None:
                    return {"memory_id": memory_id, "error": "memory not found"}

                if row["is_encrypted"]:
                    return {"memory_id": memory_id, "ok": True, "note": "already encrypted"}

                encrypted = self.encrypt(row["content"])
                await conn.execute(
                    """
                    UPDATE shared_memory.documents
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
        """
        Return aggregate encryption statistics for shared_memory.documents.

        Returns:
            Dict with total_memories, encrypted_memories, encryption_enabled,
            and algorithm keys.
        """
        if not self.pool:
            return {
                "total_memories": 0,
                "encrypted_memories": 0,
                "encryption_enabled": self._enabled,
                "algorithm": "Fernet/AES-128-CBC",
                "error": "No database pool",
            }

        try:
            async with self.pool.acquire() as conn:
                await self._ensure_column(conn)
                row = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*)                                            AS total,
                        COUNT(*) FILTER (WHERE is_encrypted = TRUE)        AS encrypted
                    FROM shared_memory.documents
                    """
                )

            return {
                "total_memories": int(row["total"]) if row else 0,
                "encrypted_memories": int(row["encrypted"]) if row else 0,
                "encryption_enabled": self._enabled,
                "algorithm": "Fernet/AES-128-CBC",
            }
        except Exception as exc:
            logger.error("get_encryption_stats failed: %s", exc)
            return {
                "total_memories": 0,
                "encrypted_memories": 0,
                "encryption_enabled": self._enabled,
                "algorithm": "Fernet/AES-128-CBC",
                "error": str(exc),
            }

    async def rotate_encryption_key(
        self, new_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rotate the master encryption key.

        Fetches all encrypted rows, decrypts them with the current key,
        re-encrypts with the new key, and persists.  Atomicity is row-level
        (not a single transaction) to avoid long locks on large tables.

        Args:
            new_key: Base64-urlsafe 32-byte Fernet key string.  When omitted
                     a fresh key is generated automatically.

        Returns:
            Dict with "rotated" count and "new_key_preview" (first 8 chars
            of the raw key + "..."), or "error" key on failure.
        """
        if not self._enabled:
            return {"error": "encryption not enabled (cryptography not installed)"}

        if not self.pool:
            return {"error": "No database pool"}

        # Prepare new Fernet instance
        if new_key:
            new_key_bytes = new_key.encode() if isinstance(new_key, str) else new_key
        else:
            new_key_bytes = Fernet.generate_key()

        new_fernet = Fernet(new_key_bytes)
        new_key_preview = new_key_bytes.decode("ascii")[:8] + "..."

        rotated = 0
        try:
            async with self.pool.acquire() as conn:
                await self._ensure_column(conn)

                rows = await conn.fetch(
                    """
                    SELECT id, content
                      FROM shared_memory.documents
                     WHERE is_encrypted = TRUE
                    """
                )

            for row in rows:
                try:
                    plaintext = self.decrypt(row["content"])
                    # Re-encrypt with the new key
                    new_token = new_fernet.encrypt(plaintext.encode("utf-8"))
                    new_ciphertext = _ENC_PREFIX + new_token.decode("ascii")

                    async with self.pool.acquire() as conn:
                        await conn.execute(
                            """
                            UPDATE shared_memory.documents
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

            # Switch to the new key after all rows are updated
            self._raw_key = new_key_bytes
            self._fernet = new_fernet
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
        master_key:    Optional base64-urlsafe 32-byte Fernet key string.

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
