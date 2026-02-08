"""
Enhanced Cognee - Encryption & Data Protection

Implements encryption at rest, PII detection, and GDPR compliance tools.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import json
import logging
import re
import secrets
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Encryption manager for sensitive data.

    Provides encryption at rest for passwords, API keys, and sensitive memories.
    """

    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize encryption manager.

        Args:
            master_key: Master encryption key (auto-generated if None)
        """
        if master_key is None:
            master_key = secrets.token_bytes(32)

        # Derive encryption key from master key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'enhanced-cognee-salt',
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))

        self.cipher = Fernet(key)
        self.master_key = master_key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext.

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted data (base64 encoded)
        """
        try:
            encrypted = self.cipher.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext.

        Args:
            ciphertext: Encrypted data (base64 encoded)

        Returns:
            Decrypted plaintext
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary.

        Args:
            data: Dictionary to encrypt

        Returns:
            Encrypted data
        """
        json_str = json.dumps(data)
        return self.encrypt(json_str)

    def decrypt_dict(self, ciphertext: str) -> Dict[str, Any]:
        """
        Decrypt a dictionary.

        Args:
            ciphertext: Encrypted dictionary

        Returns:
            Decrypted dictionary
        """
        json_str = self.decrypt(ciphertext)
        return json.loads(json_str)


class PIIDetector:
    """
    Personally Identifiable Information (PII) detector.

    Detects and masks PII in text for GDPR compliance.
    """

    def __init__(self):
        """Initialize PII detector."""
        # PII patterns (simplified - production would use more sophisticated NLP)
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'api_key': r'\b[A-Za-z0-9]{32,}\b',
            'password': r'\b(password|passwd|pwd)[:=]\s*\S+',
            'secret': r'\b(secret|token|key)[:=]\s*\S+',
        }

    def detect_pii(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect PII in text.

        Args:
            text: Text to analyze

        Returns:
            Dict of PII types with matches
        """
        detected = {}

        for pii_type, pattern in self.patterns.items():
            matches = []
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append({
                    "start": match.start(),
                    "end": match.end(),
                    "value": match.group(),
                    "length": match.end() - match.start()
                })

            if matches:
                detected[pii_type] = matches

        return detected

    def mask_pii(
        self,
        text: str,
        pii_info: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> str:
        """
        Mask PII in text.

        Args:
            text: Text to mask
            pii_info: Pre-detected PII (optional, will detect if None)

        Returns:
            Text with PII masked
        """
        if pii_info is None:
            pii_info = self.detect_pii(text)

        # Sort matches by position (reverse to avoid index shifting)
        all_matches = []
        for pii_type, matches in pii_info.items():
            for match in matches:
                all_matches.append({
                    "type": pii_type,
                    "start": match["start"],
                    "end": match["end"],
                    "value": match["value"]
                })

        # Sort by start position (descending)
        all_matches.sort(key=lambda x: x["start"], reverse=True)

        # Mask each match
        masked_text = text
        for match in all_matches:
            start = match["start"]
            end = match["end"]
            pii_type = match["type"]
            length = end - start

            # Create mask
            if pii_type == "email":
                mask = "***@***.***"
            elif pii_type == "phone":
                mask = "***-***-****"
            elif pii_type == "ssn":
                mask = "***-**-****"
            elif pii_type == "credit_card":
                mask = "****-****-****-****"
            else:
                mask = "*" * min(length, 8)

            # Replace in text
            masked_text = masked_text[:start] + mask + masked_text[end:]

        return masked_text

    def sanitize_for_log(
        self,
        data: Any,
        mask_pii: bool = True
    ) -> str:
        """
        Sanitize data for logging (mask PII).

        Args:
            data: Data to sanitize
            mask_pii: Whether to mask PII

        Returns:
            Sanitized string representation
        """
        # Convert to string
        if isinstance(data, dict):
            # Mask sensitive fields
            sanitized = {}
            for key, value in data.items():
                if key.lower() in ['password', 'token', 'secret', 'api_key']:
                    sanitized[key] = "***MASKED***"
                elif isinstance(value, str) and mask_pii:
                    sanitized[key] = self.mask_pii(value)
                else:
                    sanitized[key] = value
            return json.dumps(sanitized, default=str)
        elif isinstance(data, str) and mask_pii:
            return self.mask_pii(data)
        else:
            return str(data)


class GDPRCompliance:
    """
    GDPR compliance tools.

    Provides data export, access, and deletion (right to be forgotten).
    """

    def __init__(self, db_pool, pii_detector: PIIDetector):
        """
        Initialize GDPR compliance tools.

        Args:
            db_pool: Database connection pool
            pii_detector: PII detector instance
        """
        self.db_pool = db_pool
        self.pii_detector = pii_detector

    async def export_user_data(
        self,
        user_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Export all user data (GDPR right to data portability).

        Args:
            user_id: User identifier
            format: Export format ('json' or 'csv')

        Returns:
            User data dict
        """
        async with self.db_pool.acquire() as conn:
            # Get user info
            user = await conn.fetchrow(
                "SELECT * FROM shared_memory.users WHERE user_id = $1",
                user_id
            )

            # Get user's memories
            memories = await conn.fetch("""
                SELECT * FROM shared_memory.documents
                WHERE agent_id = $1
                ORDER BY created_at DESC
            """, user_id)

            # Get user's sessions
            sessions = await conn.fetch("""
                SELECT * FROM shared_memory.sessions
                WHERE user_id = $1
                ORDER BY start_time DESC
            """, user_id)

            # Get API keys (without hashes)
            api_keys = await conn.fetch("""
                SELECT key_id, name, role, scopes, created_at, last_used, is_active
                FROM shared_memory.api_keys
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)

        # Build export data
        export_data = {
            "user": dict(user) if user else None,
            "memories": [dict(m) for m in memories],
            "sessions": [dict(s) for s in sessions],
            "api_keys": [dict(k) for k in api_keys],
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "format": format
        }

        logger.info(f"Exported data for user={user_id} ({len(export_data['memories'])} memories)")

        return export_data

    async def delete_user_data(
        self,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Delete all user data (GDPR right to be forgotten).

        Args:
            user_id: User identifier
            reason: Reason for deletion

        Returns:
            Counts of deleted items
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Delete memories
                memories_result = await conn.execute("""
                    DELETE FROM shared_memory.documents
                    WHERE agent_id = $1
                """, user_id)

                memories_deleted = int(memories_result.split()[-1])

                # Delete sessions
                sessions_result = await conn.execute("""
                    DELETE FROM shared_memory.sessions
                    WHERE user_id = $1
                """, user_id)

                sessions_deleted = int(sessions_result.split()[-1])

                # Delete API keys
                keys_result = await conn.execute("""
                    DELETE FROM shared_memory.api_keys
                    WHERE user_id = $1
                """, user_id)

                keys_deleted = int(keys_result.split()[-1])

                # Delete permissions
                permissions_result = await conn.execute("""
                    DELETE FROM shared_memory.user_permissions
                    WHERE user_id = $1
                """, user_id)

                permissions_deleted = int(permissions_result.split()[-1])

                # Delete user
                user_result = await conn.execute("""
                    DELETE FROM shared_memory.users
                    WHERE user_id = $1
                """, user_id)

                user_deleted = int(user_result.split()[-1])

        logger.info(f"Deleted data for user={user_id}: {memories_deleted} memories, {sessions_deleted} sessions, {keys_deleted} keys")

        return {
            "user_id": user_id,
            "memories_deleted": memories_deleted,
            "sessions_deleted": sessions_deleted,
            "api_keys_deleted": keys_deleted,
            "permissions_deleted": permissions_deleted,
            "user_deleted": user_deleted,
            "reason": reason
        }

    async def get_user_data_summary(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get summary of user data (for GDPR access requests).

        Args:
            user_id: User identifier

        Returns:
            Summary of user's stored data
        """
        async with self.db_pool.acquire() as conn:
            # Count memories
            memories_count = await conn.fetchval("""
                SELECT COUNT(*) FROM shared_memory.documents
                WHERE agent_id = $1
            """, user_id)

            # Count sessions
            sessions_count = await conn.fetchval("""
                SELECT COUNT(*) FROM shared_memory.sessions
                WHERE user_id = $1
            """, user_id)

            # Count active API keys
            api_keys_count = await conn.fetchval("""
                SELECT COUNT(*) FROM shared_memory.api_keys
                WHERE user_id = $1 AND is_active = true
            """, user_id)

            # Get user info
            user = await conn.fetchrow(
                "SELECT username, email, role, created_at FROM shared_memory.users WHERE user_id = $1",
                user_id
            )

        return {
            "user_id": user_id,
            "username": user["username"] if user else None,
            "email": user["email"] if user else None,
            "role": user["role"] if user else None,
            "member_since": user["created_at"].isoformat() if user else None,
            "memories_count": memories_count,
            "sessions_count": sessions_count,
            "active_api_keys": api_keys_count,
            "data_summary": f"{memories_count} memories, {sessions_count} sessions, {api_keys_count} active API keys"
        }


async def main():
    """Test security features."""
    print("Security features require database connection")
    print("Use with PostgreSQL connection pool")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
