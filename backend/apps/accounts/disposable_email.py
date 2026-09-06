from .models import DisposableEmailDomain


def is_disposable_email(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1].lower().strip()
    return DisposableEmailDomain.objects.filter(domain=domain).exists()
