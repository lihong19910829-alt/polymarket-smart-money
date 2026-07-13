from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_admin_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_api_key
    if not expected or expected == "change-me":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="admin key unset")
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")

