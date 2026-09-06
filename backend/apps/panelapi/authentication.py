from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class ApiKeyAuthentication(BaseAuthentication):
    """JAP-style auth: the API key travels as a `key` field in the POST body
    (or query string, for convenience), not an Authorization header — this
    matches the convention docs/provider-api-assumptions.md documents for
    every other panel in this space, so existing reseller scripts/tools
    pointed at this panel need no special-casing."""

    def authenticate(self, request):
        key = request.data.get("key") or request.query_params.get("key")
        if not key:
            return None  # let DRF fall through to "no credentials" / 401 from permissions

        try:
            user = User.objects.select_related("wallet").get(api_key=key)
        except User.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid API key.") from exc

        if user.status != User.Status.ACTIVE:
            raise AuthenticationFailed(f"This account is {user.status}.")

        return (user, None)

    def authenticate_header(self, request):
        # Without this, DRF has no way to tell an auth failure (401) apart
        # from a plain permission denial (403) and defaults to 403 for both.
        return "Api-Key"
