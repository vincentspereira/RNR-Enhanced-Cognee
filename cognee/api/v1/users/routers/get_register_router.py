import os
from fastapi import APIRouter, HTTPException


def get_register_router():
    if os.getenv("COGNEE_PUBLIC_REGISTRATION_ENABLED", "0").lower() not in {"1", "true"}:
        router = APIRouter()

        @router.post("/register")
        async def registration_disabled():
            raise HTTPException(status_code=403, detail="Public registration is disabled")

        return router
    from cognee.modules.users.get_fastapi_users import get_fastapi_users
    from cognee.modules.users.models.User import UserRead, UserCreate
    return get_fastapi_users().get_register_router(UserRead, UserCreate)
