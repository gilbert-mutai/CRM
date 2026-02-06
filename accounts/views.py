# views.py

import base64
import io
import logging

from django.urls import reverse
from django.shortcuts import HttpResponseRedirect, render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils.encoding import force_bytes

from django.utils import timezone
from datetime import timedelta

import qrcode

from .forms import SignUpForm, TOTPTokenForm, Disable2FAForm, CustomSetPasswordForm
from .utils import authenticate_user, create_inactive_user, send_confirmation_email
from .token_generator import invitation_token_generator  # Add this import
from django.contrib.auth.tokens import default_token_generator


User = get_user_model()
logger = logging.getLogger(__name__)

ACTIVATION_TOKEN_EXPIRY = 3 * 24 * 60 * 60


@require_http_methods(["GET", "POST"])
def login_user(request):
    """Handle credential step and optionally start 2FA flow."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate_user(email, password)

        if user is None:
            messages.error(request, "Invalid email or password.")
            return redirect("accounts:login")

        # If admin requires 2FA but user has not enabled it, force setup after login
        if getattr(user, "is_2fa_required", False) and not getattr(user, "is_2fa_enabled", False):
            login(request, user)
            request.session["force_2fa_next"] = request.POST.get("next", reverse("access_center"))
            return redirect("accounts:setup_2fa")

        # If user has 2FA enabled, postpone final login and ask for token
        if getattr(user, "is_2fa_enabled", False):
            # store backend to use later (use user.backend if set, else first configured backend)
            backend = getattr(user, "backend", None) or settings.AUTHENTICATION_BACKENDS[0]
            request.session["pre_2fa_user_id"] = user.pk
            request.session["pre_2fa_backend"] = backend
            request.session["pre_2fa_next"] = request.POST.get("next", reverse("access_center"))
            return redirect("accounts:verify_2fa")

        login(request, user)
        messages.success(request, "Logged in successfully.")
        return redirect(request.POST.get("next") or reverse("access_center"))

    # GET
    return render(request, "accounts/login.html")


def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def register_user(request):
    """Simple registration view. Uses create_inactive_user if available."""
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                form.add_error("email", "An account with this email already exists.")
                return render(request, "accounts/register.html", {"form": form})
            
            data = form.cleaned_data
            password = data.get("password1")
            try:
                user = create_inactive_user(
                    email=email,
                    password=password,
                    first_name=data.get("first_name", ""),
                    last_name=data.get("last_name", ""),
                )
                send_confirmation_email(user)
                messages.success(request, f"Account created for {email}. Welcome email sent.")
                return redirect("access_center")
            except Exception as exc:
                logger.exception("create_inactive_user/send_confirmation_email failed")
                messages.error(request, "Failed to create account. Please try again.")
                return render(request, "accounts/register.html", {"form": form})
    else:
        form = SignUpForm()
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def set_new_password(request, uidb64, token):
    """Allow user to set password using token from email link."""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = get_object_or_404(User, pk=uid)
        user.refresh_from_db()
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Check token validity
    token_valid = user is not None and invitation_token_generator.check_token(user, token)

    if not token_valid:
        messages.error(request, "This link is invalid or has expired.")
        return redirect("accounts:login")

    # Token is valid, proceed with form
    if request.method == "POST":
        form = CustomSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            user.is_active = True
            user.save(update_fields=["is_active"])
            messages.success(request, "Password set successfully! You can now log in.")
            return redirect("accounts:login")
    else:
        form = CustomSetPasswordForm(user)

    return render(request, "accounts/set_password.html", {"form": form})


@require_http_methods(["GET", "POST"])
def resend_activation(request):
    """Allows users to request a new activation email if the old one expired or was used."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                messages.info(request, "Account is already active. Please login.")
                return redirect("accounts:login")

            send_confirmation_email(user)
            messages.success(request, "A new activation email has been sent. Please check your inbox.")
            return redirect("accounts:login")
        except User.DoesNotExist:
            messages.error(request, "No account found with that email.")
            return redirect("accounts:resend_activation")

    return render(request, "accounts/resend_activation.html")

def verify_2fa(request):
    user_id = request.session.get("pre_2fa_user_id")
    if not user_id:
        return redirect("accounts:login")

    try:
        pending_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.pop("pre_2fa_user_id", None)
        return redirect("accounts:login")

    # simple attempt limiter
    attempts = request.session.get("pre_2fa_attempts", 0)
    if attempts >= 10:
        # lockout behavior - adjust as needed
        request.session.pop("pre_2fa_user_id", None)
        request.session.pop("pre_2fa_attempts", None)
        messages.error(request, "Too many attempts. Please login again.")
        return redirect("accounts:login")

    form = TOTPTokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        token = form.cleaned_data["token"]
        if getattr(pending_user, "verify_totp_token", None) and pending_user.verify_totp_token(token):
            backend = request.session.pop("pre_2fa_backend", None) or settings.AUTHENTICATION_BACKENDS[0]
            login(request, pending_user, backend=backend)
            request.session.pop("pre_2fa_user_id", None)
            request.session.pop("pre_2fa_next", None)
            request.session.pop("pre_2fa_attempts", None)
            messages.success(request, "Logged in with 2FA.")
            return HttpResponseRedirect(request.session.pop("pre_2fa_next", reverse("access_center")))
        # failed attempt
        request.session["pre_2fa_attempts"] = attempts + 1
        form.add_error("token", "Invalid authentication code.")
    return render(request, "accounts/verify_2fa.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def setup_2fa(request):
    """Show provisioning QR and confirm TOTP to enable 2FA for the logged-in user."""
    user = request.user
    # Ensure secret exists on user model helper
    try:
        user.ensure_totp_secret()
    except RuntimeError:
        messages.error(request, "TOTP support is not available (pyotp missing).")
        return redirect("access_center")

    uri = user.get_totp_provisioning_uri(issuer_name="Client-Manager")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    qr_data = f"data:image/png;base64,{qr_b64}"

    form = TOTPTokenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        token = form.cleaned_data["token"]
        if user.verify_totp_token(token):
            user.is_2fa_enabled = True
            user.save(update_fields=["is_2fa_enabled"])
            messages.success(request, "Two‑factor authentication enabled.")
            next_url = request.session.pop("force_2fa_next", None) or reverse("access_center")
            return redirect(next_url)
        form.add_error("token", "Invalid code. Please try again.")

    return render(request, "accounts/setup_2fa.html", {"qr_data": qr_data, "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def disable_2fa(request):
    """Disable 2FA after confirming the user's password."""
    user = request.user
    if getattr(user, "is_2fa_required", False):
        messages.error(request, "Two‑factor authentication is required for your account.")
        return redirect("accounts:profile")
    if request.method == "POST":
        form = Disable2FAForm(user=user, data=request.POST)
        if form.is_valid():
            user.is_2fa_enabled = False
            user.totp_secret = None
            user.save(update_fields=["is_2fa_enabled", "totp_secret"])
            messages.success(request, "Two‑factor authentication disabled.")
            return redirect("access_center")
    else:
        form = Disable2FAForm(user=user)
    return render(request, "accounts/disable_2fa.html", {"form": form})


@login_required
def profile(request):
    """
    Minimal account/profile page used by navbar link.
    Add more details or links (enable/disable 2FA, edit profile) as needed.
    """
    return render(request, "accounts/profile.html", {"user": request.user})
