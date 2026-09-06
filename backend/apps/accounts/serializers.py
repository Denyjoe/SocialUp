from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .disposable_email import is_disposable_email
from .email_deliverability import domain_can_receive_email
from .tasks import send_verification_email
from .turnstile import verify_turnstile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "phone_number",
            "status",
            "referral_code",
            "is_staff",
            "email_verified",
            "phone_verified",
            "date_joined",
        )
        read_only_fields = (
            "id",
            "status",
            "referral_code",
            "is_staff",
            "email_verified",
            "phone_verified",
            "date_joined",
        )


class RegisterSerializer(serializers.ModelSerializer):
    # Declared explicitly with no validators so DRF does NOT attach its
    # automatic UniqueValidator — that one runs before validate_email() and
    # would pre-empt our more useful duplicate messages. The DB's unique
    # constraint remains the ultimate backstop.
    email = serializers.EmailField(validators=[])
    password = serializers.CharField(write_only=True, validators=[validate_password])
    referral_code = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    turnstile_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("email", "phone_number", "password", "referral_code", "turnstile_token")

    def validate_email(self, value):
        # Normalise case so "Foo@x.com" and "foo@x.com" can't become two
        # accounts — the DB unique constraint is case-sensitive on its own.
        value = value.strip().lower()

        # One account per email address. If that address already signed up
        # through Google, point them at the Google button rather than the
        # generic "already exists" — otherwise it reads like a dead end.
        existing = User.objects.filter(email__iexact=value).first()
        if existing is not None:
            if existing.google_sub:
                raise serializers.ValidationError(
                    "This email is already registered through Google. "
                    "Use the “Sign in with Google” button instead."
                )
            raise serializers.ValidationError(
                "An account with this email already exists. Try logging in, or reset your password."
            )
        if is_disposable_email(value):
            raise serializers.ValidationError(
                "Please use a real, permanent email address. Disposable or throwaway addresses are not accepted."
            )
        domain = value.rsplit("@", 1)[-1]
        if not domain_can_receive_email(domain):
            raise serializers.ValidationError(
                "This email domain does not appear to accept mail. Check for a typo, or use a different address."
            )
        return value

    def validate_referral_code(self, value):
        if not value:
            return value
        if not User.objects.filter(referral_code=value).exists():
            raise serializers.ValidationError("Unknown referral code.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        remote_ip = request.META.get("REMOTE_ADDR") if request else None
        if not verify_turnstile(attrs.get("turnstile_token", ""), remote_ip):
            raise serializers.ValidationError(
                {"turnstile_token": "Verification failed. Please try again."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("turnstile_token", None)
        referral_code = validated_data.pop("referral_code", None)
        referred_by = None
        if referral_code:
            referred_by = User.objects.filter(referral_code=referral_code).first()
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            phone_number=validated_data.get("phone_number", ""),
            referred_by=referred_by,
        )
        transaction.on_commit(lambda: send_verification_email.delay(user.id))
        return user


class MeUpdateSerializer(serializers.ModelSerializer):
    """Deliberately narrow: email changes aren't allowed through this endpoint
    since email is the login identifier (USERNAME_FIELD)."""

    class Meta:
        model = User
        fields = ("phone_number",)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds a status check and embeds the user profile in the token response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.status != User.Status.ACTIVE:
            raise serializers.ValidationError(
                f"This account is {self.user.status}. Contact support."
            )

        data["user"] = UserSerializer(self.user).data
        return data


class EmailVerifyRequestSerializer(serializers.Serializer):
    token = serializers.CharField()


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField()
    referral_code = serializers.CharField(required=False, allow_blank=True)


class PhoneSendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=False, allow_blank=True)


class PhoneVerifyOTPSerializer(serializers.Serializer):
    code = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])


