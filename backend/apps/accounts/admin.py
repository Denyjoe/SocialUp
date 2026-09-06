from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import DisposableEmailDomain, EmailVerificationToken, PhoneOTP, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-date_joined",)
    list_display = (
        "email",
        "phone_number",
        "status",
        "email_verified",
        "phone_verified",
        "is_staff",
        "date_joined",
    )
    list_filter = ("status", "is_staff", "is_superuser", "email_verified", "phone_verified")
    search_fields = ("email", "phone_number", "api_key", "referral_code")
    readonly_fields = (
        "api_key",
        "referral_code",
        "google_sub",
        "date_joined",
        "last_login",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("phone_number", "status", "referred_by")}),
        (
            "Verification",
            {"fields": ("email_verified", "phone_verified", "google_sub")},
        ),
        ("Panel access", {"fields": ("api_key", "referral_code")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "expires_at", "verified_at", "created_at")
    search_fields = ("user__email",)
    readonly_fields = ("token",)


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "attempts", "expires_at", "verified_at", "created_at")
    search_fields = ("user__email", "phone_number")


@admin.register(DisposableEmailDomain)
class DisposableEmailDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "created_at")
    search_fields = ("domain",)
