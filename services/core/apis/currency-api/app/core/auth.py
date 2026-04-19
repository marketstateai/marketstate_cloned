import secrets

from fastapi import Header, HTTPException, status

from app.core.config import get_settings

def require_api_token(
    x_api_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if x_api_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token",
        )

    if not secrets.compare_digest(x_api_token, settings.api_auth_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
        )
