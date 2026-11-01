"""Strict administrator authentication for process-wide upstream settings.

Never use get_authenticated_user here: its optional-auth mode can create an
anonymous default superuser. Global provider configuration must always require
a real active authenticated administrator, including in local development.
"""
from fastapi import Depends, HTTPException

from cognee.modules.users.get_fastapi_users import get_fastapi_users
from cognee.modules.users.models import User

_authenticated = get_fastapi_users().current_user(active=True, optional=False)


async def require_global_admin(user: User = Depends(_authenticated)) -> User:
    if getattr(user, "is_superuser", False) is not True:
        raise HTTPException(status_code=403, detail="Only an authenticated administrator may access global settings")
    return user
