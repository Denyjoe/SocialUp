from apps.orders.models import Order


def test_progress_percent_none_remains_and_not_completed_returns_none():
    order = Order(quantity=1000, remains=None, status=Order.Status.PENDING)
    assert order.progress_percent is None


def test_progress_percent_none_remains_but_completed_returns_100():
    order = Order(quantity=1000, remains=None, status=Order.Status.COMPLETED)
    assert order.progress_percent == 100


def test_progress_percent_partial_delivery():
    order = Order(quantity=1000, remains=400, status=Order.Status.IN_PROGRESS)
    assert order.progress_percent == 60


def test_progress_percent_fully_delivered():
    order = Order(quantity=1000, remains=0, status=Order.Status.COMPLETED)
    assert order.progress_percent == 100


def test_progress_percent_clamps_when_remains_exceeds_quantity():
    # Defensive: a provider reporting a bad remains value should never
    # produce a negative percentage.
    order = Order(quantity=1000, remains=1500, status=Order.Status.IN_PROGRESS)
    assert order.progress_percent == 0


def test_progress_percent_zero_quantity_returns_none():
    order = Order(quantity=0, remains=0, status=Order.Status.PENDING)
    assert order.progress_percent is None
