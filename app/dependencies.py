from fastapi import Header, HTTPException, status

from app.config import settings


def require_user_auth(authorization: str | None = Header(default=None)) -> str | None:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    token = authorization.split("Bearer ")[-1] if "Bearer " in authorization else authorization
    return token