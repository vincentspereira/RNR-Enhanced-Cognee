"""
Enhanced Cognee - Authentication & Authorization System

Implements JWT authentication, API key management, and RBAC.
Enterprise-grade security for Enhanced Cognee.

Author: Enhanced Cognee Team
Version: 1.0.0
Date: 2026-02-06
"""

import asyncio
import secrets
import jwt
import hashlib
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"          # Full access
    USER = "user"            # Standard user access
    READONLY = "readonly"    # Read-only access
    API_CLIENT = "api_client" # API service account


class Permission(str, Enum):
    """Permissions for fine-grained access control."""
    # Memory permissions
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    MEMORY_ADMIN = "memory:admin"

    # Session permissions
    SESSION_READ = "session:read"
    SESSION_WRITE = "session:write"
    SESSION_DELETE = "session:delete"

    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_CONFIG = "system:config"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.MEMORY_READ, Permission.MEMORY_WRITE, Permission.MEMORY_DELETE, Permission.MEMORY_ADMIN,
        Permission.SESSION_READ, Permission.SESSION_WRITE, Permission.SESSION_DELETE,
        Permission.SYSTEM_ADMIN, Permission.SYSTEM_MONITOR, Permission.SYSTEM_CONFIG
    ],
    Role.USER: [
        Permission.MEMORY_READ, Permission.MEMORY_WRITE,
        Permission.SESSION_READ, Permission.SESSION_WRITE,
        Permission.SYSTEM_MONITOR
    ],
    Role.READONLY: [
        Permission.MEMORY_READ,
        Permission.SESSION_READ,
        Permission.SYSTEM_MONITOR
    ],
    Role.API_CLIENT: [
        Permission.MEMORY_READ, Permission.MEMORY_WRITE,
        Permission.SESSION_READ, Permission.SESSION_WRITE
    ]
}


class JWTAuthenticator:
    """
    JWT-based authentication system.

    Provides token generation, validation, and refresh.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        token_expiry_hours: int = 24
    ):
        """
        Initialize JWT authenticator.

        Args:
            secret_key: Secret key for signing (auto-generated if None)
            algorithm: JWT algorithm
            token_expiry_hours: Token expiration time
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.token_expiry = timedelta(hours=token_expiry_hours)

    def create_token(
        self,
        user_id: str,
        role: Role = Role.USER,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a JWT token.

        Args:
            user_id: User identifier
            role: User role
            additional_claims: Additional claims to include

        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "role": role,
            "iat": now,
            "exp": now + self.token_expiry,
            **(additional_claims or {})
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Created token for user={user_id}, role={role}")

        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            logger.debug(f"Verified token for user={payload.get('user_id')}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_token(self, token: str) -> Optional[str]:
        """
        Refresh an expired token.

        Args:
            token: Original token

        Returns:
            New token or None if refresh not possible
        """
        payload = self.verify_token(token)
        if not payload:
            # Try to decode without expiration check
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm],
                    options={"verify_exp": False}
                )

                # Create new token with same claims
                return self.create_token(
                    payload["user_id"],
                    Role(payload["role"])
                )

            except jwt.InvalidTokenError:
                return None

        # Token is still valid, no refresh needed
        return token


class APIKeyManager:
    """
    API key management system.

    Provides API key generation, validation, and rotation.
    """

    def __init__(self, db_pool):
        """
        Initialize API key manager.

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    async def create_api_key(
        self,
        user_id: str,
        name: str,
        role: Role = Role.API_CLIENT,
        scopes: Optional[List[str]] = None
    ) -> str:
        """
        Create a new API key.

        Args:
            user_id: User identifier
            name: Key name/description
            role: User role
            scopes: Permission scopes

        Returns:
            API key (format: cogne_xxxx...)
        """
        # Generate API key
        key_id = secrets.token_urlsafe(16)
        api_key = f"cogne_{key_id}"

        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO shared_memory.api_keys (
                    key_id,
                    key_hash,
                    user_id,
                    name,
                    role,
                    scopes,
                    created_at,
                    is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), true)
            """, key_id, key_hash, user_id, name, role,
                 json.dumps(scopes or []))

        logger.info(f"Created API key: {key_id} for user={user_id}")
        return api_key

    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Verify an API key.

        Args:
            api_key: API key string

        Returns:
            Key info or None if invalid
        """
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT key_id, user_id, name, role, scopes, last_used, is_active
                FROM shared_memory.api_keys
                WHERE key_hash = $1 AND is_active = true
            """, key_hash)

        if not row:
            return None

        # Update last used timestamp
        await conn.execute("""
            UPDATE shared_memory.api_keys
            SET last_used = NOW()
            WHERE key_id = $1
        """, row["key_id"])

        return dict(row)

    async def revoke_api_key(self, key_id: str, user_id: str) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: Key identifier
            user_id: User requesting revocation

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE shared_memory.api_keys
                SET is_active = false, revoked_at = NOW()
                WHERE key_id = $1 AND user_id = $2
            """, key_id, user_id)

        return result == "UPDATE 1"

    async def list_user_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all API keys for a user.

        Args:
            user_id: User identifier

        Returns:
            List of API keys
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT key_id, name, role, scopes, created_at, last_used, is_active
                FROM shared_memory.api_keys
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)

        return [dict(row) for row in rows]


class RBACManager:
    """
    Role-Based Access Control manager.

    Enforces permissions based on user roles.
    """

    def __init__(self, db_pool):
        """
        Initialize RBAC manager.

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    def has_permission(
        self,
        role: Role,
        permission: Permission
    ) -> bool:
        """
        Check if role has permission.

        Args:
            role: User role
            permission: Permission to check

        Returns:
            True if role has permission
        """
        role_permissions = ROLE_PERMISSIONS.get(role, [])
        return permission in role_permissions

    def has_any_permission(
        self,
        role: Role,
        permissions: List[Permission]
    ) -> bool:
        """
        Check if role has any of the specified permissions.

        Args:
            role: User role
            permissions: List of permissions

        Returns:
            True if role has at least one permission
        """
        return any(self.has_permission(role, perm) for perm in permissions)

    def has_all_permissions(
        self,
        role: Role,
        permissions: List[Permission]
    ) -> bool:
        """
        Check if role has all specified permissions.

        Args:
            role: User role
            permissions: List of permissions

        Returns:
            True if role has all permissions
        """
        return all(self.has_permission(role, perm) for perm in permissions)

    async def check_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """
        Check if user has permission (from database).

        Args:
            user_id: User identifier
            permission: Permission to check

        Returns:
            True if user has permission
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT role FROM shared_memory.users
                WHERE user_id = $1
            """, user_id)

        if not row:
            return False

        return self.has_permission(Role(row["role"]), permission)

    async def grant_permission(
        self,
        user_id: str,
        permission: Permission,
        granted_by: str
    ) -> bool:
        """
        Grant a permission to a user (beyond their role).

        Args:
            user_id: User to grant permission to
            permission: Permission to grant
            granted_by: User granting the permission

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            # Check if granter has admin permission
            granter_role = await conn.fetchval(
                "SELECT role FROM shared_memory.users WHERE user_id = $1",
                granted_by
            )

            if not self.has_permission(Role(granter_role), Permission.SYSTEM_ADMIN):
                logger.warning(f"User {granted_by} lacks permission to grant {permission}")
                return False

            # Grant permission
            await conn.execute("""
                INSERT INTO shared_memory.user_permissions (user_id, permission, granted_by, granted_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id, permission) DO NOTHING
            """, user_id, permission, granted_by)

        logger.info(f"Granted {permission} to {user_id} by {granted_by}")
        return True

    async def revoke_permission(
        self,
        user_id: str,
        permission: Permission,
        revoked_by: str
    ) -> bool:
        """
        Revoke a permission from a user.

        Args:
            user_id: User to revoke permission from
            permission: Permission to revoke
            revoked_by: User revoking the permission

        Returns:
            True if successful
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM shared_memory.user_permissions
                WHERE user_id = $1 AND permission = $2
            """, user_id, permission)

        logger.info(f"Revoked {permission} from {user_id} by {revoked_by}")
        return result == "DELETE 1"


async def main():
    """Test authentication system."""
    print("Authentication system requires database connection")
    print("Use with PostgreSQL connection pool")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
