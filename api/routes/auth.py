"""Authentication endpoints: email/password signup/login + session cookie.

Sessions are httpOnly cookies holding an opaque token (stored hashed in SQLite).
``get_current_user`` is the dependency that gates the chat/conversation routes;
it returns the authenticated user dict or raises 401.

Google OAuth routes (``/auth/google/login`` + ``/auth/google/callback``) are
defined below in this module.
"""
import logging
import sqlite3
from typing import Optional

import anyio
from authlib.integrations.starlette_client import OAuth, OAuthError
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
    is_admin: bool = False


def _is_admin_email(email: str) -> bool:
    """True if *email* is in the ADMIN_EMAILS allowlist (case-insensitive)."""
    admins = {e.strip().lower() for e in get_settings().ADMIN_EMAILS.split(",") if e.strip()}
    return bool(email) and email.strip().lower() in admins


def _user_out(user: dict) -> UserOut:
    """Public user payload; computes is_admin from the ADMIN_EMAILS allowlist."""
    return UserOut(
        id=user["id"], email=user["email"], name=user["name"],
        is_admin=_is_admin_email(user["email"]),
    )


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


async def get_optional_user(request: Request) -> Optional[dict]:
    """Resolve the session cookie to a user, or None when absent/invalid.

    Used by the anonymous-friendly /auth/me probe: it never raises, so a visitor
    without a session gets a 200 + null body instead of a 401 error.
    """
    token = request.cookies.get(get_settings().SESSION_COOKIE_NAME)
    if not token:
        return None
    return await anyio.to_thread.run_sync(users_store.get_user_by_session, token)


async def get_current_user(request: Request) -> dict:
    """FastAPI dependency: resolve the session cookie to a user or 401."""
    user = await get_optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency: require an authenticated user in ADMIN_EMAILS, else 403."""
    if not _is_admin_email(user.get("email", "")):
        raise HTTPException(status_code=403, detail="Admin access required")
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
    return _user_out({"id": uid, "email": body.email, "name": body.name.strip()})


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
    return _user_out(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response):
    token = request.cookies.get(get_settings().SESSION_COOKIE_NAME)
    if token:
        await anyio.to_thread.run_sync(users_store.delete_session, token)
    response.delete_cookie(get_settings().SESSION_COOKIE_NAME, path="/")


@router.get("/me", response_model=Optional[UserOut])
async def me(user: Optional[dict] = Depends(get_optional_user)):
    if user is None:
        return None
    return _user_out(user)


# --- Google OAuth -----------------------------------------------------------

@router.get("/google/login")
async def google_login(request: Request):
    s = get_settings()
    if not s.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google login is not configured")
    return await oauth.google.authorize_redirect(request, s.GOOGLE_REDIRECT_URI)


async def _google_userinfo(request: Request) -> dict:
    """Resolve the OAuth callback to a Google profile dict (sub/email/name).

    Mirrors authlib's ``authorize_access_token`` (state check + code→token
    exchange) but reads the profile from the ``userinfo`` endpoint instead of
    verifying the ``id_token`` locally. Local verification fetches Google's JWKS
    from ``www.googleapis.com/oauth2/v3/certs``, which this deploy's region gets
    HTTP 403 from — that is what surfaced as a blank 500. The token endpoint and
    the userinfo endpoint (``openidconnect.googleapis.com``) are both reachable.
    Raises on any error/invalid-state/exchange failure.
    """
    if request.query_params.get("error"):
        raise OAuthError(error=request.query_params["error"])
    state = request.query_params.get("state")
    state_data = await oauth.google.framework.get_state_data(request.session, state)
    if not state_data:
        raise OAuthError(description='Invalid "state" parameter')
    await oauth.google.framework.clear_state_data(request.session, state)
    params = {"code": request.query_params.get("code"), "state": state}
    if state_data.get("redirect_uri"):
        params["redirect_uri"] = state_data["redirect_uri"]
    if state_data.get("code_verifier"):
        params["code_verifier"] = state_data["code_verifier"]
    token = await oauth.google.fetch_access_token(**params)
    return dict(await oauth.google.userinfo(token=token))


@router.get("/google/callback")
async def google_callback(request: Request):
    s = get_settings()
    # The OAuth exchange depends on external Google state (wrong secret, lost
    # state cookie, denied consent, an unreachable Google host). Any failure
    # would otherwise reach the user as a blank 500 — fail closed instead: log
    # the real cause (visible in the server logs) and bounce back to login.
    try:
        info = await _google_userinfo(request)
    except Exception as exc:  # external OAuth boundary — degrade gracefully, never 500
        logger.warning("Google OAuth callback failed: %r", exc)
        return RedirectResponse(url=f"{s.FRONTEND_URL}/login?error=google")
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
