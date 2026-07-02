import bcrypt
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import current_session_username, secure_text_equal
from app.config import get_settings


router = APIRouter()
INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid username or password.",
)


class LoginRequest(BaseModel):
    username: str = Field(max_length=200)
    password: str = Field(max_length=1000)


class AuthenticatedResponse(BaseModel):
    authenticated: bool
    username: str


class LoggedOutResponse(BaseModel):
    authenticated: bool = False


def password_matches(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


@router.post("/login", response_model=AuthenticatedResponse)
def login(payload: LoginRequest, request: Request) -> AuthenticatedResponse:
    settings = get_settings()
    username_matches = bool(settings.admin_username) and secure_text_equal(payload.username, settings.admin_username)
    valid_password = password_matches(payload.password, settings.admin_password_hash)
    if not username_matches or not valid_password:
        raise INVALID_CREDENTIALS
    request.session.clear()
    request.session["authenticated"] = True
    request.session["username"] = settings.admin_username
    return AuthenticatedResponse(authenticated=True, username=settings.admin_username)


@router.post("/logout", response_model=LoggedOutResponse)
def logout(request: Request) -> LoggedOutResponse:
    request.session.clear()
    return LoggedOutResponse()


@router.get("/me", response_model=AuthenticatedResponse)
def me(request: Request) -> AuthenticatedResponse:
    username = current_session_username(request)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return AuthenticatedResponse(authenticated=True, username=username)
