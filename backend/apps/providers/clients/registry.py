from apps.providers.models import Provider

from .base import BaseProviderClient
from .mock_client import MockProviderClient


def get_client_for_provider(provider: Provider) -> BaseProviderClient:
    if provider.provider_type == Provider.ProviderType.MOCK:
        return MockProviderClient()
    if provider.provider_type == Provider.ProviderType.JAP_STYLE:
        # Phase 3: real HTTP client, built against docs/provider-api-assumptions.md.
        from .jap_client import JAPStyleClient

        return JAPStyleClient(provider)
    raise ValueError(f"No client registered for provider_type={provider.provider_type!r}")
