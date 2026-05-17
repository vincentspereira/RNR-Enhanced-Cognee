"""
Unit tests for src/security/data_protection.py
Covers: EncryptionManager (encrypt, decrypt, encrypt_dict, decrypt_dict),
        PIIDetector (detect_pii, mask_pii, sanitize_for_log),
        GDPRCompliance (stubbed DB, export_user_data, delete_user_data).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.security.data_protection import (
    EncryptionManager,
    PIIDetector,
    GDPRCompliance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(conn):
    class _Ctx:
        async def __aenter__(self): return conn
        async def __aexit__(self, *a): pass

    class _Pool:
        def acquire(self): return _Ctx()

    return _Pool()


# ---------------------------------------------------------------------------
# EncryptionManager
# ---------------------------------------------------------------------------

class TestEncryptionManager:
    @pytest.fixture
    def enc(self):
        return EncryptionManager()

    @pytest.mark.unit
    def test_encrypt_returns_string(self, enc):
        result = enc.encrypt("hello world")
        assert isinstance(result, str)
        assert result != "hello world"

    @pytest.mark.unit
    def test_decrypt_roundtrip(self, enc):
        plaintext = "sensitive data"
        ciphertext = enc.encrypt(plaintext)
        result = enc.decrypt(ciphertext)
        assert result == plaintext

    @pytest.mark.unit
    def test_encrypt_different_values_each_time(self, enc):
        ct1 = enc.encrypt("same text")
        ct2 = enc.encrypt("same text")
        # Fernet uses random IV so each call produces different ciphertext
        assert ct1 != ct2

    @pytest.mark.unit
    def test_decrypt_wrong_key_raises(self):
        enc1 = EncryptionManager()
        enc2 = EncryptionManager()
        ct = enc1.encrypt("secret")
        with pytest.raises(Exception):
            enc2.decrypt(ct)

    @pytest.mark.unit
    def test_encrypt_empty_string(self, enc):
        ct = enc.encrypt("")
        result = enc.decrypt(ct)
        assert result == ""

    @pytest.mark.unit
    def test_encrypt_unicode(self, enc):
        text = "Unicode: 中文, emoji: 🎉"
        ct = enc.encrypt(text)
        result = enc.decrypt(ct)
        assert result == text

    @pytest.mark.unit
    def test_encrypt_dict_returns_string(self, enc):
        data = {"key": "value", "num": 42}
        ct = enc.encrypt_dict(data)
        assert isinstance(ct, str)

    @pytest.mark.unit
    def test_decrypt_dict_roundtrip(self, enc):
        data = {"key": "value", "nested": {"a": 1}}
        ct = enc.encrypt_dict(data)
        result = enc.decrypt_dict(ct)
        assert result == data

    @pytest.mark.unit
    def test_custom_master_key_produces_deterministic_cipher(self):
        key = b"x" * 32
        enc1 = EncryptionManager(master_key=key)
        enc2 = EncryptionManager(master_key=key)
        ct = enc1.encrypt("data")
        # Both use same key, so dec2 can decrypt what enc1 produced
        result = enc2.decrypt(ct)
        assert result == "data"


# ---------------------------------------------------------------------------
# PIIDetector
# ---------------------------------------------------------------------------

class TestPIIDetector:
    @pytest.fixture
    def detector(self):
        return PIIDetector()

    @pytest.mark.unit
    def test_detect_email(self, detector):
        text = "Contact me at alice@example.com for info."
        detected = detector.detect_pii(text)
        assert "email" in detected
        assert len(detected["email"]) == 1

    @pytest.mark.unit
    def test_detect_phone(self, detector):
        text = "Call us at 555-867-5309 anytime."
        detected = detector.detect_pii(text)
        assert "phone" in detected

    @pytest.mark.unit
    def test_detect_no_pii_returns_empty_dict(self, detector):
        text = "This is a regular sentence with no PII."
        detected = detector.detect_pii(text)
        assert detected == {}

    @pytest.mark.unit
    def test_detect_multiple_emails(self, detector):
        text = "alice@example.com and bob@test.org are colleagues."
        detected = detector.detect_pii(text)
        assert "email" in detected
        assert len(detected["email"]) == 2

    @pytest.mark.unit
    def test_detect_ip_address(self, detector):
        text = "Server at 192.168.1.100 is down."
        detected = detector.detect_pii(text)
        assert "ip_address" in detected

    @pytest.mark.unit
    def test_detect_password_pattern(self, detector):
        text = "password: mysecretpass123"
        detected = detector.detect_pii(text)
        assert "password" in detected

    @pytest.mark.unit
    def test_detect_secret_pattern(self, detector):
        text = "secret=abc123 token=xyz789"
        detected = detector.detect_pii(text)
        assert "secret" in detected

    @pytest.mark.unit
    def test_mask_pii_email(self, detector):
        text = "Email: alice@example.com here."
        masked = detector.mask_pii(text)
        assert "alice@example.com" not in masked
        assert "***@***.***" in masked

    @pytest.mark.unit
    def test_mask_pii_phone(self, detector):
        text = "Phone: 555-867-5309 please call."
        masked = detector.mask_pii(text)
        assert "555-867-5309" not in masked
        assert "***-***-****" in masked

    @pytest.mark.unit
    def test_mask_pii_generic_mask(self, detector):
        text = "API key: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        masked = detector.mask_pii(text)
        assert "a1b2c3d4e5f6" not in masked

    @pytest.mark.unit
    def test_mask_pii_with_pii_info_provided(self, detector):
        text = "Email: alice@example.com"
        pii_info = detector.detect_pii(text)
        masked = detector.mask_pii(text, pii_info=pii_info)
        assert "alice@example.com" not in masked

    @pytest.mark.unit
    def test_mask_pii_no_pii_unchanged(self, detector):
        text = "No PII here at all."
        masked = detector.mask_pii(text)
        assert masked == text

    @pytest.mark.unit
    def test_mask_ssn(self, detector):
        text = "SSN: 123-45-6789 on record."
        masked = detector.mask_pii(text)
        assert "123-45-6789" not in masked
        assert "***-**-****" in masked

    @pytest.mark.unit
    def test_sanitize_for_log_string(self, detector):
        text = "User email is alice@example.com"
        result = detector.sanitize_for_log(text)
        assert isinstance(result, str)
        assert "alice@example.com" not in result

    @pytest.mark.unit
    def test_sanitize_for_log_dict_masks_sensitive_keys(self, detector):
        data = {"username": "alice", "password": "secret123"}
        result = detector.sanitize_for_log(data)
        parsed = json.loads(result)
        assert parsed["password"] == "***MASKED***"
        assert parsed["username"] == "alice"

    @pytest.mark.unit
    def test_sanitize_for_log_dict_masks_token(self, detector):
        data = {"token": "abc123", "name": "alice"}
        result = detector.sanitize_for_log(data)
        parsed = json.loads(result)
        assert parsed["token"] == "***MASKED***"

    @pytest.mark.unit
    def test_sanitize_for_log_non_string_non_dict(self, detector):
        result = detector.sanitize_for_log(42)
        assert result == "42"

    @pytest.mark.unit
    def test_sanitize_for_log_no_mask_pii(self, detector):
        text = "alice@example.com"
        result = detector.sanitize_for_log(text, mask_pii=False)
        assert result == text

    @pytest.mark.unit
    def test_detect_credit_card(self, detector):
        text = "Card: 4111 1111 1111 1111 is on file."
        detected = detector.detect_pii(text)
        assert "credit_card" in detected

    @pytest.mark.unit
    def test_mask_credit_card(self, detector):
        text = "Card: 4111-1111-1111-1111"
        masked = detector.mask_pii(text)
        assert "4111" not in masked
        assert "****-****-****-****" in masked


# ---------------------------------------------------------------------------
# GDPRCompliance (DB stubbed)
# ---------------------------------------------------------------------------

class TestGDPRCompliance:
    @pytest.fixture
    def conn(self):
        return AsyncMock()

    @pytest.fixture
    def gdpr(self, conn):
        pool = _make_pool(conn)
        pii = PIIDetector()
        return GDPRCompliance(db_pool=pool, pii_detector=pii), conn

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_user_data_returns_dict(self, gdpr):
        mgr, conn = gdpr
        conn.fetchrow = AsyncMock(return_value={"user_id": "u1", "email": "u@x.com", "created_at": "2026"})
        conn.fetch = AsyncMock(return_value=[])
        result = await mgr.export_user_data("u1")
        assert isinstance(result, dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_user_not_found_returns_error(self, gdpr):
        mgr, conn = gdpr
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(return_value=[])
        result = await mgr.export_user_data("ghost")
        # Should return some kind of result (error or empty)
        assert result is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_user_data_full(self, gdpr):
        mgr, conn = gdpr
        conn.fetchrow = AsyncMock(return_value={"user_id": "u1", "email": "u@x.com", "created_at": "2026"})
        conn.fetch = AsyncMock(return_value=[])
        result = await mgr.export_user_data("u1")
        assert "user" in result
        assert "memories" in result
        assert "sessions" in result
        assert "api_keys" in result
        assert "export_timestamp" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_user_data_returns_counts(self, gdpr):
        mgr, conn = gdpr
        # Mock transaction context manager
        class _TxCtx:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        conn.transaction = MagicMock(return_value=_TxCtx())
        conn.execute = AsyncMock(side_effect=[
            "DELETE 5",   # memories
            "DELETE 2",   # sessions
            "DELETE 1",   # api_keys
            "DELETE 3",   # permissions
            "DELETE 1",   # user
        ])

        result = await mgr.delete_user_data("u1", reason="GDPR request")
        assert result["user_id"] == "u1"
        assert result["memories_deleted"] == 5
        assert result["sessions_deleted"] == 2
        assert result["api_keys_deleted"] == 1
        assert result["permissions_deleted"] == 3
        assert result["user_deleted"] == 1
        assert result["reason"] == "GDPR request"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_data_summary(self, gdpr):
        mgr, conn = gdpr
        conn.fetchval = AsyncMock(side_effect=[10, 3, 2])  # memories, sessions, keys
        conn.fetchrow = AsyncMock(return_value={
            "username": "alice",
            "email": "alice@example.com",
            "role": "user",
            "created_at": MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00")),
        })
        result = await mgr.get_user_data_summary("u1")
        assert result["user_id"] == "u1"
        assert result["memories_count"] == 10
        assert result["sessions_count"] == 3
        assert result["active_api_keys"] == 2
        assert "data_summary" in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_data_summary_user_not_found(self, gdpr):
        mgr, conn = gdpr
        conn.fetchval = AsyncMock(side_effect=[0, 0, 0])
        conn.fetchrow = AsyncMock(return_value=None)
        result = await mgr.get_user_data_summary("ghost")
        assert result["username"] is None
        assert result["email"] is None


# ---------------------------------------------------------------------------
# EncryptionManager exception paths
# ---------------------------------------------------------------------------

class TestEncryptionManagerErrors:
    @pytest.mark.unit
    def test_decrypt_invalid_ciphertext_raises(self):
        enc = EncryptionManager()
        with pytest.raises(Exception):
            enc.decrypt("not-valid-base64-ciphertext-garbage!!!")

    @pytest.mark.unit
    def test_sanitize_for_log_dict_non_string_value_preserved(self):
        detector = PIIDetector()
        data = {"count": 42, "active": True}
        result = detector.sanitize_for_log(data)
        parsed = json.loads(result)
        assert parsed["count"] == 42
