"""Authentication endpoints: email/password signup/login + session cookie.

Sessions are httpOnly cookies holding an opaque token (stored hashed in SQLite).
``get_current_user`` is the dependency that gates the chat/conversation routes;
it returns the authenticated user dict or raises 401.

Google OAuth routes are added in auth_google.py / registered separately.
"""
import logging
import sqlite3

import anyio
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator

from config import get_settings
from rag import users as users_store
from api.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


def _login_rate_limit() -> str:
    return get_settings().AUTH_LOGIN_RATE_LIMIT


def _signup_rate_limit() -> str:
    return get_settings().AUTH_SIGNUP_RATE_LIMIT

# Google OIDC client. Registration is network-free (metadata is fetched lazily on
# the first authorize call), so it is safe even when the credentials are unset.
oauth = OAuth()
oauth.register(
    name="google",
    client_id=get_settings().GOOGLE_CLIENT_ID,
    client_secret=get_settings().GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# --- schemas ----------------------------------------------------------------

class SignupIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=72)  # bcrypt 72-byte cap
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("invalid email address")
        return v


class LoginIn(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    id: str
    email: str
    name: str


# --- cookie helpers ---------------------------------------------------------

def _set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        key=s.SESSION_COOKIE_NAME,
        value=token,
        max_age=s.SESSION_TTL_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=s.SESSION_COOKIE_SECURE,
        path="/",
    )


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: resolve the session cookie to a user or 401."""
    token = request.cookies.get(get_settings().SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await anyio.to_thread.run_sync(users_store.get_user_by_session, token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# --- endpoints --------------------------------------------------------------

@router.post("/signup", response_model=UserOut)
@limiter.limit(_signup_rate_limit)
async def signup(request: Request, body: SignupIn, response: Response):
    try:
        uid = await anyio.to_thread.run_sync(
            users_store.create_user, body.email, body.name.strip(), body.password
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    token = await anyio.to_thread.run_sync(
        users_store.create_session, uid, get_settings().SESSION_TTL_HOURS
    )
    _set_session_cookie(response, token)
    return UserOut(id=uid, email=body.email, name=body.name.strip())


@router.post("/login", response_model=UserOut)
@limiter.limit(_login_rate_limit)
async def login(request: Request, body: LoginIn, response: Response):
    user = await anyio.to_thread.run_sync(users_store.get_user_by_email, body.email)
    # Always run bcrypt — against the real hash, or a dummy when the email is unknown
    # or password-less — so response time never reveals whether an email is registered.
    stored_hash = user["password_hash"] if (user and user["password_hash"]) else users_store.DUMMY_PASSWORD_HASH
    valid = await anyio.to_thread.run_sync(users_store.verify_password, body.password, stored_hash)
    if not user or not valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = await anyio.to_thread.run_sync(
        users_store.create_session, user["id"], get_settings().SESSION_TTL_HOURS
    )
    _set_session_cookie(response, token)
    return UserOut(id=user["id"], email=user["email"], name=user["name"])


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    token = request.cookies.get(get_settings().SESSION_COOKIE_NAME)
    if token:
        await anyio.to_thread.run_sync(users_store.delete_session, token)
    response.delete_cookie(get_settings().SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return UserOut(id=user["id"], email=user["email"], name=user["name"])


# --- Google OAuth -----------------------------------------------------------

@router.get("/google/login")
async def google_login(request: Request):
    s = get_settings()
    if not s.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google login is not configured")
    return await oauth.google.authorize_redirect(request, s.GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request):
    s = get_settings()
    # The token exchange depends entirely on external state: a wrong
    # GOOGLE_CLIENT_SECRET surfaces as OAuthError(invalid_client), a lost state
    # cookie as MismatchingStateError, a denied consent as access_denied — and a
    # raw token-endpoint failure can even bubble up as a transport error. Any of
    # these would otherwise reach the user as a blank 500. Fail closed instead:
    # log the real cause (visible in the server logs) and send the user back to
    # the login page with an error flag.
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:  # external OAuth boundary — degrade gracefully, never 500
        logger.warning("Google OAuth callback failed: %r", exc)
        return RedirectResponse(url=f"{s.FRONTEND_URL}/login?error=google")
    info = token.get("userinfo") or {}
    sub, email = info.get("sub"), info.get("email")
    name = info.get("name") or email
    if not sub or not email:
        logger.warning("Google OAuth callback returned no userinfo")
        return RedirectResponse(url=f"{s.FRONTEND_URL}/login?error=google")
    user = await anyio.to_thread.run_sync(
        users_store.get_or_create_google_user, sub, email, name
    )
    session_token = await anyio.to_thread.run_sync(
        users_store.create_session, user["id"], s.SESSION_TTL_HOURS
    )
    resp = RedirectResponse(url=f"{s.FRONTEND_URL}/app")
    _set_session_cookie(resp, session_token)
    return resp
