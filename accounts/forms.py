from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import SetPasswordForm
from .models import CustomUser


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email Address"}
        ),
    )
    first_name = forms.CharField(
        label="",
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "First Name"}
        ),
    )
    last_name = forms.CharField(
        label="",
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Last Name"}
        ),
    )
    password1 = forms.CharField(
        label="",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Password"}
        ),
        help_text="",
    )
    password2 = forms.CharField(
        label="",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm Password"}
        ),
        help_text="",
    )

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name", "password1", "password2")


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter new password"}
        ),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Confirm new password"}
        ),
    )

# --- TOTP / 2FA forms ---
class TOTPTokenForm(forms.Form):
    token = forms.CharField(
        label="Authentication code",
        max_length=8,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter 6-digit code",
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
            }
        ),
    )

    def clean_token(self):
        token = self.cleaned_data.get("token", "").strip()
        if not token.isdigit() or not (4 <= len(token) <= 8):
            raise forms.ValidationError("Enter a valid authentication code.")
        return token


class Disable2FAForm(forms.Form):
    """
    Simple confirmation form to disable 2FA; requires the user's password.
    Pass the current user to the form via `Disable2FAForm(user=request.user, data=...)`.
    """

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Enter your password"}
        ),
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        pw = self.cleaned_data.get("password", "")
        if self.user and not self.user.check_password(pw):
            raise forms.ValidationError("Incorrect password.")
        return pw
