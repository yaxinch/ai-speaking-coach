import secrets

from fastapi import HTTPException, Request, status

from app.config import get_settings


UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def secure_text_equal(left: str, right: str) -> bool:
    return secrets.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def current_session_username(request: Request) -> str | None:
    settings = get_settings()
    username = request.session.get("username")
    if request.session.get("authenticated") is not True or not isinstance(username, str):
        return None
    if not settings.admin_username or not secure_text_equal(username, settings.admin_username):
        return None
    return username


def require_auth(request: Request) -> str:
    username = current_session_username(request)
    if username is None:
        raise UNAUTHORIZED
    return username
