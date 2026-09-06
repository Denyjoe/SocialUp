"""
Settings shared by every environment. Do not import this module directly —
use one of local / production / test, which layer environment-specific
overrides on top of this.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    # local apps
    "apps.common",
    "apps.accounts",
    "apps.providers",
    "apps.catalog",
    "apps.wallet",
    "apps.orders",
    "apps.support",
    "apps.affiliate",
    "apps.panelapi",
    "apps.announcements",
    "apps.promotions",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Falls back to a local SQLite file when DATABASE_URL isn't set, so the
# project boots with zero external services for a quick sanity check.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SocialUp API",
    "DESCRIPTION": "Wallet-funded social media growth service ordering platform.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"]
)

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Defaults to True so `.delay()` runs synchronously in-process with no Redis/
# worker needed — lets the whole app work with nothing but `manage.py
# runserver`. docker-compose.yml sets this to False for the backend/worker/
# beat services, where a real broker + worker are actually running.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=True)

# --- Phase 7: registration hardening ---

FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:5173")
# This backend's own public URL — needed to build an absolute callback URL
# for external services that POST back to us (currently: NOWPayments IPN).
BACKEND_BASE_URL = env("BACKEND_BASE_URL", default="http://localhost:8000")

# Google Sign-In (docs/google-signin-setup.md)
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")

# Beem Africa OTP (docs/beem-otp-assumptions.md)
BEEM_API_KEY = env("BEEM_API_KEY", default="")
BEEM_SECRET_KEY = env("BEEM_SECRET_KEY", default="")
BEEM_APP_ID = env("BEEM_APP_ID", default="")

# Cloudflare Turnstile (docs/turnstile-setup.md) — disabled by default so
# local dev works with no Cloudflare account; verify_turnstile() always
# returns True while this is False.
TURNSTILE_ENABLED = env.bool("TURNSTILE_ENABLED", default=False)
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")

# Transactional email (docs/transactional-email-setup.md) — any SMTP
# provider works (Brevo recommended for its free tier); local/test settings
# override EMAIL_BACKEND to the console backend so nothing is actually sent.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@socialup.local")

# Crypto payments via NOWPayments (docs/nowpayments-crypto-setup.md) — the
# interim deposit option while PesaPal verification is pending. Empty
# falls back to a mock gateway that instantly completes, so the whole
# deposit flow works in local dev and tests with no external setup.
NOWPAYMENTS_API_KEY = env("NOWPAYMENTS_API_KEY", default="")
NOWPAYMENTS_IPN_SECRET = env("NOWPAYMENTS_IPN_SECRET", default="")
NOWPAYMENTS_IPN_CALLBACK_URL = env(
    "NOWPAYMENTS_IPN_CALLBACK_URL",
    default=f"{BACKEND_BASE_URL}/api/payments/webhooks/nowpayments/",
)
