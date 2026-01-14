from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    # Authentication
    path("login/", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("register/", views.register_user, name="register"),
    path("profile/", views.profile, name="profile"),
    
    # 2FA / TOTP
    path("setup-2fa/", views.setup_2fa, name="setup_2fa"),
    path("verify-2fa/", views.verify_2fa, name="verify_2fa"),
    path("disable-2fa/", views.disable_2fa, name="disable_2fa"),
    
    # User activation (for new users invited by admin)
    path("set-password/<uidb64>/<token>/", views.set_new_password, name="set_new_password"),
    path("resend-activation/", views.resend_activation, name="resend_activation"),

    # Password reset flow (for existing users who forgot password)
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]

