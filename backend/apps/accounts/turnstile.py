import requests
from django.conf import settings

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
REQUEST_TIMEOUT_SECONDS = 10


def verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    """True if the Turnstile token is valid. Always True when Turnstile isn't
    configured (TURNSTILE_ENABLED=False), so local dev works with no
    Cloudflare account — see docs/turnstile-setup.md."""
    if not settings.TURNSTILE_ENABLED:
        return True
    if not token:
        return False

    payload = {"secret": settings.TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        response = requests.post(VERIFY_URL, data=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        return bool(response.json().get("success"))
    except (requests.RequestException, ValueError):
        return False
