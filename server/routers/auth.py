from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from config import COOKIE_SECURE, REFRESH_TOKEN_EXPIRE_DAYS
from dependencies import AuthSvc
from schemas import Token
from services import AuthenticationError, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
# Only sent to /auth/* (refresh and logout), never with ordinary API calls.
_COOKIE = {"path": "/auth", "httponly": True, "secure": COOKIE_SECURE, "samesite": "lax"}


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE, raw_token, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, **_COOKIE
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, **_COOKIE)


def _token_body(pair: TokenPair) -> Token:
    return Token(access_token=pair.access_token, expires_in=pair.expires_in)


@router.post("/login", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response, service: AuthSvc
):
    """OAuth2 password flow: form fields `username` (the email) and `password`.

    Returns a short-lived access token in the body and sets the refresh token as an HttpOnly cookie.
    """
    pair = service.login(form.username, form.password)
    _set_refresh_cookie(response, pair.refresh_token)
    return _token_body(pair)


@router.post("/refresh", response_model=Token)
def refresh(
    response: Response,
    service: AuthSvc,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    """Trade the refresh cookie for a new access token. The refresh token is rotated every time."""
    try:
        if not refresh_token:
            raise AuthenticationError("Missing refresh token")
        pair = service.refresh(refresh_token)
    except AuthenticationError as exc:
        # A dead refresh token is useless to the browser: drop the cookie along with the 401.
        failure = JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": exc.message})
        _clear_refresh_cookie(failure)
        return failure
    _set_refresh_cookie(response, pair.refresh_token)
    return _token_body(pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    service: AuthSvc,
    refresh_token: Annotated[str | None, Cookie()] = None,
):
    """Revoke this session's refresh token and clear the cookie. Safe to call when logged out."""
    service.logout(refresh_token)
    _clear_refresh_cookie(response)
