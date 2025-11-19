from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from datetime import datetime
from django.utils.crypto import get_random_string

User = get_user_model()


def authenticate_user(email, password):
    """
    Use Django's authenticate to get a user with backend set.
    Returns user or None.
    """
    if not email or not password:
        return None
    # adjust kwargs if your auth backend expects 'username' instead of 'email'
    return authenticate(username=email, password=password)


def create_inactive_user(email, first_name, last_name):
    temp_password = get_random_string(10)
    user = User.objects.create_user(
        email=email, password=temp_password, first_name=first_name, last_name=last_name
    )
    user.is_active = False
    user.save()
    return user, temp_password


def send_confirmation_email(user, domain="http://localhost:8000"):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = (
        f"{domain}{reverse('set_new_password', kwargs={'uidb64': uid, 'token': token})}"
    )

    context = {
        "user_name": user.get_short_name(),
        "cta_link": link,
        "current_year": datetime.now().year,
    }

    subject = "Welcome to Angani Client Manager - Set your New Password"
    from_email = "Angani Client Manager <noreply.anganicrm@gmail.com>"
    to_email = [user.email]
    text_content = f"Hello {context['user_name']},\n\nPlease click the link below to set your password:\n{link}\n\nAngani CRM Team"
    html_content = render_to_string("welcome_email.html", context)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()
