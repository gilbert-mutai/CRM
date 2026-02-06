from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class Enforce2FAMiddleware:
    """Redirect users to 2FA setup if admin requires it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            if getattr(user, "is_2fa_required", False) and not getattr(user, "is_2fa_enabled", False):
                setup_path = reverse("accounts:setup_2fa")
                logout_path = reverse("accounts:logout")
                login_path = reverse("accounts:login")
                verify_path = reverse("accounts:verify_2fa")

                if request.path not in {setup_path, logout_path, login_path, verify_path}:
                    static_url = getattr(settings, "STATIC_URL", "/static/")
                    media_url = getattr(settings, "MEDIA_URL", None)
                    if request.path.startswith(static_url):
                        return self.get_response(request)
                    if media_url and request.path.startswith(media_url):
                        return self.get_response(request)
                    return redirect("accounts:setup_2fa")

        return self.get_response(request)
