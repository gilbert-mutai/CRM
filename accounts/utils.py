from django.contrib.auth import authenticate, get_user_model
from .token_generator import invitation_token_generator  # Add this import
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def authenticate_user(email, password):
    """
    Use Django's authenticate to get a user with backend set.
    Returns user or None.
    """
    if not email or not password:
        return None
    return authenticate(username=email, password=password)


def create_inactive_user(email, password=None, first_name="", last_name=""):
    
    with transaction.atomic():
        user = User(
            email=email,
            first_name=first_name or "",
            last_name=last_name or "",
            is_active=False,  
        )
        user.set_password(password)
        user.save()

    return user


def send_confirmation_email(user, domain=None):
    """
    Send a welcome / set-password email with token link.
    """
    try:
        if not user.pk:
            user.save()
        
        user.refresh_from_db()
        
        domain = domain or getattr(settings, "SITE_URL", "https://clientmanager.angani.co.ke")
        token = invitation_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        activate_url = f"{domain}{reverse('accounts:set_new_password', args=[uid, token])}"

        subject = "Welcome to Client Manager"
        context = {
            "user": user,
            "user_name": user.get_full_name() or user.email,
            "activate_url": activate_url,
            "cta_link": activate_url,
            "current_year": timezone.now().year,
        }
        text = render_to_string("accounts/welcome_email.txt", context)
        html = render_to_string("accounts/welcome_email.html", context)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or f"noreply@{domain.split('//')[-1]}"
        msg = EmailMultiAlternatives(subject, text, from_email, [user.email])
        msg.attach_alternative(html, "text/html")
        msg.send()
        logger.info(f"Welcome email sent to {user.email}")
    except Exception as e:
        logger.exception(f"Failed to send welcome email to {user.email}: {e}")
        raise
