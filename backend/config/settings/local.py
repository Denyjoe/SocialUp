from .base import *  # noqa: F401,F403

DEBUG = True

# Emails just print to the console in local dev (password resets, etc. in later phases).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
