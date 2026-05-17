"""
Extended unit tests for src/encryption_manager.py

Adds coverage for the pool-backed async paths (encrypt_memory with real pool mock,
rotate_encryption_key with rows, get_encryption_stats with pool) that the Phase 14
test file does not cover.

Targets >= 85% combined with test_phase14_new_modules.py.
ASCII-only assertions.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def _make_pool(conn):
    """Build a minimal pool mock whose acquire() returns a proper async ctx."""
    class _Ctx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *args):
            pass

    class _Pool:
        def acquire(self):
            return _Ctx()

    return _Pool()


class TestEncryptionManagerWithPool:
    """Tests exercising the asyncpg pool code paths."""

    @pytest.mark.asyncio
    async def test_encrypt_memory_not_found(self):
        from src.encryption_manager import EncryptionManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(return_value=None)  # row not found

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool)
        if not em._enabled:
            pytest.skip("cryptography not installed")

        result = await em.encrypt_memory("unknown-uuid")
        assert result.get("error") == "memory not found"

    @pytest.mark.asyncio
    async def test_encrypt_memory_already_encrypted(self):
        from src.encryption_manager import EncryptionManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(return_value={
            "content": "enc:someciphertext",
            "is_encrypted": True,
        })

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool)
        if not em._enabled:
            pytest.skip("cryptography not installed")

        result = await em.encrypt_memory("already-enc-uuid")
        assert result.get("ok") is True
        assert result.get("note") == "already encrypted"

    @pytest.mark.asyncio
    async def test_encrypt_memory_plain_text_row(self):
        from src.encryption_manager import EncryptionManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(return_value={
            "content": "plaintext secret",
            "is_encrypted": False,
        })

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool)
        if not em._enabled:
            pytest.skip("cryptography not installed")

        result = await em.encrypt_memory("plain-uuid")
        assert result.get("ok") is True
        # execute should have been called for ensure_column + UPDATE
        assert conn.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_encrypt_memory_db_exception(self):
        from src.encryption_manager import EncryptionManager
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("DB error"))
        conn.fetchrow = AsyncMock(return_value={
            "content": "some text",
            "is_encrypted": False,
        })

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool)
        if not em._enabled:
            pytest.skip("cryptography not installed")

        result = await em.encrypt_memory("error-uuid")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_encryption_stats_with_pool(self):
        from src.encryption_manager import EncryptionManager
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.fetchrow = AsyncMock(return_value={"total": 50, "encrypted": 10})

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool)

        stats = await em.get_encryption_stats()
        assert isinstance(stats, dict)
        assert "total_memories" in stats
        assert "encrypted_memories" in stats
        assert "algorithm" in stats

    @pytest.mark.asyncio
    async def test_get_encryption_stats_db_exception(self):
        from src.encryption_manager import EncryptionManager
        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("DB down"))
        conn.fetchrow = AsyncMock(side_effect=RuntimeError("DB down"))

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool)

        stats = await em.get_encryption_stats()
        assert "error" in stats

    @pytest.mark.asyncio
    async def test_rotate_encryption_key_with_rows(self):
        from src.encryption_manager import EncryptionManager
        from cryptography.fernet import Fernet

        old_key = Fernet.generate_key()
        old_fernet = Fernet(old_key)
        plaintext = "rotate me"
        ciphertext = "enc:" + old_fernet.encrypt(plaintext.encode()).decode("ascii")

        # First conn.fetch returns one row; second acquire for UPDATE
        row = {"id": "row-1", "content": ciphertext}
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(return_value=[row])

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool, master_key=old_key.decode())
        if not em._enabled:
            pytest.skip("cryptography not installed")

        new_key = Fernet.generate_key().decode()
        result = await em.rotate_encryption_key(new_key=new_key)
        assert "rotated" in result
        assert result["rotated"] == 1

    @pytest.mark.asyncio
    async def test_rotate_encryption_key_db_exception(self):
        from src.encryption_manager import EncryptionManager

        conn = AsyncMock()
        conn.execute = AsyncMock(side_effect=RuntimeError("conn error"))
        conn.fetch = AsyncMock(side_effect=RuntimeError("conn error"))

        pool = _make_pool(conn)
        em = EncryptionManager(postgres_pool=pool)
        if not em._enabled:
            pytest.skip("cryptography not installed")

        result = await em.rotate_encryption_key()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_rotate_with_disabled_encryption(self):
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        em._enabled = False
        result = await em.rotate_encryption_key()
        assert "error" in result

    def test_encrypt_empty_string_passthrough(self):
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        result = em.encrypt("")
        assert result == ""

    def test_decrypt_empty_string_passthrough(self):
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        result = em.decrypt("")
        assert result == ""

    def test_encrypt_with_provided_master_key(self):
        from src.encryption_manager import EncryptionManager
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        em = EncryptionManager(master_key=key)
        if not em._enabled:
            pytest.skip("cryptography not installed")
        encrypted = em.encrypt("secret")
        assert encrypted.startswith("enc:")
        decrypted = em.decrypt(encrypted)
        assert decrypted == "secret"

    def test_encrypt_disabled_returns_plaintext(self):
        """Lines 79-81: _enabled=False path in __init__, encrypt passes through."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        em._enabled = False
        result = em.encrypt("plaintext value")
        assert result == "plaintext value"

    def test_decrypt_disabled_returns_ciphertext(self):
        """Decrypt when disabled returns input unchanged."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        em._enabled = False
        result = em.decrypt("enc:someciphertext")
        assert result == "enc:someciphertext"

    def test_decrypt_no_prefix_returns_plaintext(self):
        """Line 128: ciphertext without enc: prefix is returned unchanged."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        if not em._enabled:
            pytest.skip("cryptography not installed")
        result = em.decrypt("no prefix here")
        assert result == "no prefix here"

    def test_encrypt_exception_returns_plaintext(self):
        """Lines 112-114: encrypt() exception caught, returns plaintext."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        if not em._enabled:
            pytest.skip("cryptography not installed")
        # Force _fernet.encrypt to raise
        em._fernet = MagicMock()
        em._fernet.encrypt.side_effect = RuntimeError("fernet boom")
        result = em.encrypt("something")
        assert result == "something"

    def test_decrypt_exception_returns_ciphertext(self):
        """Lines 134-136: decrypt() exception caught, returns ciphertext."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager()
        if not em._enabled:
            pytest.skip("cryptography not installed")
        em._fernet = MagicMock()
        em._fernet.decrypt.side_effect = RuntimeError("decrypt boom")
        ciphertext = "enc:invaliddatahere"
        result = em.decrypt(ciphertext)
        assert result == ciphertext

    @pytest.mark.asyncio
    async def test_encrypt_memory_no_pool(self):
        """Line 170: encrypt_memory returns error when pool is None."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager(postgres_pool=None)
        if not em._enabled:
            pytest.skip("cryptography not installed")
        result = await em.encrypt_memory("some-uuid")
        assert "error" in result
        assert result["error"] == "No database pool"

    @pytest.mark.asyncio
    async def test_get_encryption_stats_no_pool(self):
        """Line 212: get_encryption_stats without pool returns error."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager(postgres_pool=None)
        result = await em.get_encryption_stats()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_rotate_encryption_key_no_pool(self):
        """Line 270: rotate_encryption_key without pool returns error."""
        from src.encryption_manager import EncryptionManager
        em = EncryptionManager(postgres_pool=None)
        if not em._enabled:
            pytest.skip("cryptography not installed")
        result = await em.rotate_encryption_key()
        assert "error" in result
        assert result["error"] == "No database pool"

    @pytest.mark.asyncio
    async def test_rotate_encryption_key_row_exception(self):
        """Lines 312-313: per-row exception during rotation is caught (UPDATE raises)."""
        from src.encryption_manager import EncryptionManager
        from cryptography.fernet import Fernet

        old_key = Fernet.generate_key()
        old_fernet = Fernet(old_key)
        plaintext = "content to rotate"
        ciphertext = "enc:" + old_fernet.encrypt(plaintext.encode()).decode("ascii")
        row = {"id": "row-1", "content": ciphertext}

        # Outer conn (for _ensure_column + conn.fetch) succeeds.
        # Inner conn (for UPDATE inside the loop) raises.
        # We use two separate conn mocks and a call counter on the pool.
        outer_conn = AsyncMock()
        outer_conn.execute = AsyncMock(return_value=None)   # _ensure_column OK
        outer_conn.fetch = AsyncMock(return_value=[row])

        inner_conn = AsyncMock()
        inner_conn.execute = AsyncMock(side_effect=RuntimeError("UPDATE failed"))

        call_count = [0]

        class _MultiCtx:
            def __init__(self, c):
                self._c = c
            async def __aenter__(self):
                return self._c
            async def __aexit__(self, *args):
                pass

        class _MultiPool:
            def acquire(self_):
                call_count[0] += 1
                if call_count[0] == 1:
                    return _MultiCtx(outer_conn)
                return _MultiCtx(inner_conn)

        em = EncryptionManager(postgres_pool=_MultiPool(), master_key=old_key.decode())
        if not em._enabled:
            pytest.skip("cryptography not installed")

        result = await em.rotate_encryption_key()
        assert "rotated" in result
        # Row exception was caught so nothing was rotated
        assert result["rotated"] == 0

    def test_singleton_init_and_get(self):
        """Lines 355-360, 371: init_encryption_manager and get_encryption_manager."""
        from src.encryption_manager import init_encryption_manager, get_encryption_manager
        mgr = init_encryption_manager(postgres_pool=None)
        assert mgr is not None
        retrieved = get_encryption_manager()
        assert retrieved is mgr

    def test_init_with_crypto_disabled_sets_none_fernet(self):
        """Lines 79-81: when _CRYPTO_AVAILABLE=False, fernet is None."""
        import src.encryption_manager as _em_mod
        from unittest.mock import patch
        with patch.object(_em_mod, "_CRYPTO_AVAILABLE", False):
            from src.encryption_manager import EncryptionManager
            em = EncryptionManager(master_key="doesnotmatter")
        assert em._fernet is None
        assert em._raw_key is None

    @pytest.mark.asyncio
    async def test_encrypt_memory_crypto_disabled(self):
        """Line 167: encrypt_memory when encryption not enabled."""
        import src.encryption_manager as _em_mod
        from unittest.mock import patch
        with patch.object(_em_mod, "_CRYPTO_AVAILABLE", False):
            from src.encryption_manager import EncryptionManager
            em = EncryptionManager()
        result = await em.encrypt_memory("some-uuid")
        assert "error" in result
        assert "not enabled" in result["error"]
