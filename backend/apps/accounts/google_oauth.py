from dataclasses import dataclass

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


class GoogleTokenError(Exception):
    pass


@dataclass
class GoogleUserInfo:
    sub: str
    email: str
    email_verified: bool
    name: str = ""


def verify_google_id_token(token: str) -> GoogleUserInfo:
    """Verifies a Google Identity Services ID token server-side (signature,
    audience, expiry — all handled by the google-auth library) and returns
    the claims we care about. Raises GoogleTokenError on anything invalid."""
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise GoogleTokenError("Google sign-in is not configured on this server.")

    try:
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError as exc:
        raise GoogleTokenError(f"Invalid Google token: {exc}") from exc

    email = claims.get("email")
    if not email:
        raise GoogleTokenError("Google token did not include an email address.")

    return GoogleUserInfo(
        sub=claims["sub"],
        email=email,
        email_verified=bool(claims.get("email_verified", False)),
        name=claims.get("name", ""),
    )
