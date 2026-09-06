class PaymentGatewayError(Exception):
    """Raised for any failure talking to a payment gateway — a bad
    request, a network failure, or an unexpected response shape."""
