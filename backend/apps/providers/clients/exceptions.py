class ProviderAPIError(Exception):
    """Base class for anything that goes wrong talking to an upstream provider."""


class ProviderTimeoutError(ProviderAPIError):
    pass


class InsufficientProviderBalanceError(ProviderAPIError):
    pass
