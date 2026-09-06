from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.EmailTokenObtainPairView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path(
        "change-password/",
        views.ChangePasswordView.as_view(),
        name="auth-change-password",
    ),
    path("api-key/", views.ApiKeyView.as_view(), name="auth-api-key"),
    path(
        "api-key/regenerate/",
        views.ApiKeyRegenerateView.as_view(),
        name="auth-api-key-regenerate",
    ),
    path("verify-email/", views.EmailVerifyView.as_view(), name="auth-verify-email"),
    path(
        "resend-verification-email/",
        views.ResendVerificationEmailView.as_view(),
        name="auth-resend-verification-email",
    ),
    path("google/", views.GoogleAuthView.as_view(), name="auth-google"),
    path("phone/send-otp/", views.PhoneSendOTPView.as_view(), name="auth-phone-send-otp"),
    path("phone/verify-otp/", views.PhoneVerifyOTPView.as_view(), name="auth-phone-verify-otp"),
    path(
        "password-reset/",
        views.PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
