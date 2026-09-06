import requests
from django.conf import settings

REQUEST_TIMEOUT_SECONDS = 15


class PhoneOTPError(Exception):
    pass


class BeemOTPClient:
    """Client for Beem Africa's OTP API — confirmed contract (2026-09-04) at
    docs.beem.africa/api-reference/{request,verify}-otp: Basic Auth,
    POST-only, response wrapped in {"data": {...}}. The exact field name for
    the code on the verify call wasn't shown in the fetched docs (assumed
    "pin" below) — see docs/beem-otp-assumptions.md, confirm against a real
    sandbox call before relying on this in production."""

    BASE_URL = "https://apiotp.beem.africa/v1"

    def __init__(self):
        self.api_key = settings.BEEM_API_KEY
        self.secret_key = settings.BEEM_SECRET_KEY
        self.app_id = settings.BEEM_APP_ID

    def _post(self, path: str, payload: dict) -> dict:
        try:
            response = requests.post(
                f"{self.BASE_URL}/{path}",
                json=payload,
                auth=(self.api_key, self.secret_key),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise PhoneOTPError(f"Beem request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise PhoneOTPError(f"Beem returned a non-JSON response: {response.text[:300]}") from exc

        if not response.ok and not data.get("data"):
            raise PhoneOTPError(f"Beem HTTP {response.status_code}: {response.text[:300]}")

        return data.get("data", {})

    def send_otp(self, phone_number: str) -> str:
        """Returns Beem's pinId, used to correlate the follow-up verify call."""
        data = self._post("request", {"appId": self.app_id, "msisdn": phone_number})
        message = data.get("message", {})
        if message.get("code") != 100:
            raise PhoneOTPError(message.get("message", "Failed to send OTP."))
        pin_id = data.get("pinId")
        if not pin_id:
            raise PhoneOTPError(f"Beem response missing pinId: {data!r}")
        return pin_id

    def verify_otp(self, pin_id: str, code: str) -> bool:
        # ASSUMED field name "pin" for the code — see module docstring.
        data = self._post("verify", {"pinId": pin_id, "pin": code})
        message = data.get("message", {})
        return message.get("code") == 117
