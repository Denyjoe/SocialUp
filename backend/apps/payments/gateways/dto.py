from dataclasses import dataclass


@dataclass
class CheckoutResult:
    checkout_url: str
    gateway_reference: str
    # Mock gateway only: a redirect-based flow has no meaningful way to
    # "instantly complete" like the reseller API's mock client does, since
    # the real thing is a hosted page a browser navigates to. Setting this
    # lets the mock skip straight to a finished result instead, which is
    # the closest honest equivalent — everything else stays None/blank and
    # waits for a real webhook.
    immediate_status: str | None = None


@dataclass
class WebhookResult:
    internal_reference: str
    status: str
    pay_currency: str = ""
