import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .google_oauth import GoogleTokenError, verify_google_id_token
from .models import EmailVerificationToken, PhoneOTP, User
from .phone_otp import BeemOTPClient, PhoneOTPError
from .serializers import (
    ChangePasswordSerializer,
    EmailTokenObtainPairSerializer,
    EmailVerifyRequestSerializer,
    GoogleAuthSerializer,
    MeUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PhoneSendOTPSerializer,
    PhoneVerifyOTPSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .tasks import send_password_reset_email, send_verification_email

RESEND_COOLDOWN = timedelta(seconds=60)
OTP_SEND_COOLDOWN = timedelta(seconds=60)
OTP_SOFT_EXPIRY = timedelta(minutes=10)
MAX_OTP_ATTEMPTS = 5

logger = logging.getLogger(__name__)


def _otp_error_response(exc: "PhoneOTPError", context: str) -> Response:
    # Beem's raw error body (e.g. AUTH_INVALID_CREDENTIALS) is useful for us
    # to see while wiring this up, but it's a vendor implementation detail —
    # never worth showing a real customer. Full detail always goes to the
    # log; the response is only detailed in DEBUG (local dev).
    logger.error("Beem OTP error (%s): %s", context, exc)
    detail = str(exc) if settings.DEBUG else "Could not process your verification code right now. Please try again shortly."
    return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class EmailTokenObtainPairView(TokenObtainPairView):
    """Login: POST {email, password} -> {access, refresh, user}."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = EmailTokenObtainPairSerializer


class LogoutView(APIView):
    """POST {refresh} -> blacklists the refresh token so it can't be reused."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "refresh is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or already-expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        return MeUpdateSerializer if self.request.method in ("PUT", "PATCH") else UserSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        # Respond with the full profile (including read-only fields), not
        # just the narrow set MeUpdateSerializer accepts as input.
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})


class ApiKeyView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return Response({"api_key": request.user.api_key})


class ApiKeyRegenerateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        user.api_key = ""
        user.save()  # User.save() regenerates a fresh unique api_key when blank
        return Response({"api_key": user.api_key})


class EmailVerifyView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = EmailVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_row = (
            EmailVerificationToken.objects.select_related("user")
            .filter(token=serializer.validated_data["token"])
            .first()
        )
        if not token_row:
            return Response({"detail": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)
        if token_row.expires_at < timezone.now():
            return Response(
                {"detail": "This verification link has expired. Request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token_row.verified_at = timezone.now()
        token_row.save(update_fields=["verified_at"])
        token_row.user.email_verified = True
        token_row.user.save(update_fields=["email_verified"])
        return Response({"detail": "Email verified."})


class ResendVerificationEmailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.email_verified:
            return Response({"detail": "Email is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        existing = EmailVerificationToken.objects.filter(user=user).first()
        if existing and timezone.now() - existing.created_at < RESEND_COOLDOWN:
            return Response(
                {"detail": "Please wait a moment before requesting another email."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        send_verification_email.delay(user.id)
        return Response({"detail": "Verification email sent."})


class GoogleAuthView(APIView):
    """POST {id_token, referral_code?} -> {access, refresh, user}. Links to
    an existing account by email if one exists (and trusts Google's own
    email_verified claim in that case), otherwise creates a new one."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            google_user = verify_google_id_token(serializer.validated_data["id_token"])
        except GoogleTokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Normalised to match RegisterSerializer.validate_email(), so a
        # Google sign-in always lands on the existing account rather than
        # creating a case-variant duplicate.
        google_email = google_user.email.strip().lower()

        user = User.objects.filter(google_sub=google_user.sub).first()
        if user is None:
            user = User.objects.filter(email__iexact=google_email).first()
            if user is not None:
                user.google_sub = google_user.sub
                if google_user.email_verified:
                    user.email_verified = True
                user.save(update_fields=["google_sub", "email_verified"])

        if user is None:
            referral_code = serializer.validated_data.get("referral_code")
            referred_by = User.objects.filter(referral_code=referral_code).first() if referral_code else None
            user = User.objects.create_user(
                email=google_email,
                password=None,
                referred_by=referred_by,
            )
            user.set_unusable_password()
            user.google_sub = google_user.sub
            user.email_verified = google_user.email_verified
            user.save(update_fields=["password", "google_sub", "email_verified"])

        if user.status != User.Status.ACTIVE:
            return Response(
                {"detail": f"This account is {user.status}. Contact support."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh), "user": UserSerializer(user).data}
        )


class PhoneSendOTPView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = PhoneSendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        phone_number = serializer.validated_data.get("phone_number") or user.phone_number
        if not phone_number:
            return Response({"detail": "A phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        last_otp = PhoneOTP.objects.filter(user=user).first()  # Meta.ordering = -created_at
        if last_otp and timezone.now() - last_otp.created_at < OTP_SEND_COOLDOWN:
            return Response(
                {"detail": "Please wait a moment before requesting another code."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if phone_number != user.phone_number:
            user.phone_number = phone_number
            user.save(update_fields=["phone_number"])

        try:
            pin_id = BeemOTPClient().send_otp(phone_number)
        except PhoneOTPError as exc:
            return _otp_error_response(exc, "send")

        PhoneOTP.objects.create(
            user=user,
            phone_number=phone_number,
            provider_reference=pin_id,
            expires_at=timezone.now() + OTP_SOFT_EXPIRY,
        )
        return Response({"detail": f"A verification code was sent to {phone_number}."})


class PhoneVerifyOTPView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = PhoneVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        otp = PhoneOTP.objects.filter(user=user, verified_at__isnull=True).first()
        if not otp:
            return Response({"detail": "No pending verification code. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)
        if otp.expires_at < timezone.now():
            return Response({"detail": "This code has expired. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)
        if otp.attempts >= MAX_OTP_ATTEMPTS:
            return Response({"detail": "Too many attempts. Request a new code."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            valid = BeemOTPClient().verify_otp(otp.provider_reference, serializer.validated_data["code"])
        except PhoneOTPError as exc:
            return _otp_error_response(exc, "verify")

        if not valid:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            return Response({"detail": "Incorrect code."}, status=status.HTTP_400_BAD_REQUEST)

        otp.verified_at = timezone.now()
        otp.save(update_fields=["verified_at"])
        user.phone_verified = True
        user.save(update_fields=["phone_verified"])
        return Response({"detail": "Phone verified."})


GENERIC_RESET_RESPONSE = {
    "detail": "If an account exists for that email, a reset link is on its way."
}


class PasswordResetRequestView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is not None and user.status == User.Status.ACTIVE:
            send_password_reset_email.delay(user.id)

        # Always the same response whether or not the account exists —
        # otherwise this endpoint becomes a way to enumerate which emails
        # are registered.
        return Response(GENERIC_RESET_RESPONSE)


class PasswordResetConfirmView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user_id = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(
            user, serializer.validated_data["token"]
        ):
            return Response(
                {"detail": "This reset link is invalid or has expired. Request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated. You can now log in."})

