from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


# Create your models here.
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # 2FA / TOTP fields
    totp_secret = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Base32 TOTP secret (used for authenticator apps).",
    )
    is_2fa_enabled = models.BooleanField(
        default=False, help_text="Whether the user has TOTP 2FA enabled."
    )
    is_2fa_required = models.BooleanField(
        default=False,
        help_text="Whether the user must enable 2FA before accessing the system.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        """Return first_name + last_name or empty string."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Return first name or email as fallback."""
        return self.first_name or self.email

    # Helpers for TOTP (optional; requires pyotp)
    def ensure_totp_secret(self):
        """
        Ensure a totp_secret exists for this user. Generates and saves one if missing.
        Requires pyotp installed when called.
        """
        if not self.totp_secret:
            try:
                import pyotp
            except ImportError:
                raise RuntimeError("pyotp is required to generate TOTP secrets.")
            self.totp_secret = pyotp.random_base32()
            self.save(update_fields=["totp_secret"])
        return self.totp_secret

    def get_totp_provisioning_uri(self, issuer_name="Client-Manager"):
        """
        Return the provisioning URI to render as a QR code in authenticator apps.
        Requires pyotp.
        """
        try:
            import pyotp
        except ImportError:
            raise RuntimeError("pyotp is required to build provisioning URI.")
        if not self.totp_secret:
            self.ensure_totp_secret()
        totp = pyotp.TOTP(self.totp_secret)
        return totp.provisioning_uri(name=self.email, issuer_name=issuer_name)

    def verify_totp_token(self, token, valid_window=1):
        """
        Verify a provided TOTP token. Returns True/False.
        Requires pyotp.
        """
        try:
            import pyotp
        except ImportError:
            raise RuntimeError("pyotp is required to verify TOTP tokens.")
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return bool(totp.verify(token, valid_window=valid_window))
