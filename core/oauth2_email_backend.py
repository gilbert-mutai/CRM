"""
Custom OAuth2 Email Backend for Microsoft Graph API
Uses MSAL (Microsoft Authentication Library) to authenticate and send emails via Microsoft Graph.
"""
import logging
import msal
import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address

logger = logging.getLogger(__name__)


class OAuth2EmailBackend(BaseEmailBackend):
    """
    Email backend that uses Microsoft Graph API with OAuth2 authentication.
    Requires OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET, and OAUTH2_TENANT_ID in settings.
    """

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.access_token = None

    def _get_access_token(self):
        """Acquire access token using client credentials flow."""
        try:
            authority = f"https://login.microsoftonline.com/{settings.OAUTH2_TENANT_ID}"
            app = msal.ConfidentialClientApplication(
                settings.OAUTH2_CLIENT_ID,
                authority=authority,
                client_credential=settings.OAUTH2_CLIENT_SECRET,
            )

            # Request token with Mail.Send scope
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )

            if "access_token" in result:
                logger.info("Successfully acquired OAuth2 access token")
                return result["access_token"]
            else:
                error_msg = result.get("error_description", result.get("error", "Unknown error"))
                logger.error(f"Failed to acquire token: {error_msg}")
                raise Exception(f"OAuth2 token acquisition failed: {error_msg}")

        except Exception as e:
            logger.exception(f"Error acquiring OAuth2 token: {e}")
            if not self.fail_silently:
                raise
            return None

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of messages sent.
        """
        if not email_messages:
            return 0

        # Get access token
        self.access_token = self._get_access_token()
        if not self.access_token:
            return 0

        num_sent = 0
        for message in email_messages:
            if self._send_message(message):
                num_sent += 1

        return num_sent

    def _send_message(self, message):
        """Send a single email message using Microsoft Graph API."""
        try:
            # Prepare email data for Microsoft Graph
            email_data = self._prepare_email_data(message)

            # Get sender email from settings or message
            sender_email = settings.EMAIL_HOST_USER

            # Microsoft Graph API endpoint
            url = f"https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=email_data, timeout=30)

            if response.status_code == 202:
                logger.info(f"Email sent successfully: {message.subject}")
                return True
            else:
                error_msg = response.text
                logger.error(f"Failed to send email: {response.status_code} - {error_msg}")
                if not self.fail_silently:
                    raise Exception(f"Failed to send email: {response.status_code} - {error_msg}")
                return False

        except Exception as e:
            logger.exception(f"Error sending email: {e}")
            if not self.fail_silently:
                raise
            return False

    def _prepare_email_data(self, message):
        """Convert Django EmailMessage to Microsoft Graph API format."""
        # Get email body
        if message.content_subtype == "html":
            body_content = message.body
            body_type = "HTML"
        else:
            # Check if there's an HTML alternative
            body_content = message.body
            body_type = "Text"
            for content, mimetype in getattr(message, "alternatives", []):
                if mimetype == "text/html":
                    body_content = content
                    body_type = "HTML"
                    break

        # Prepare recipients
        to_recipients = [{"emailAddress": {"address": addr}} for addr in message.to]
        cc_recipients = [{"emailAddress": {"address": addr}} for addr in message.cc]
        bcc_recipients = [{"emailAddress": {"address": addr}} for addr in message.bcc]

        # Build email data structure
        email_data = {
            "message": {
                "subject": message.subject,
                "body": {"contentType": body_type, "content": body_content},
                "toRecipients": to_recipients,
            }
        }

        if cc_recipients:
            email_data["message"]["ccRecipients"] = cc_recipients

        if bcc_recipients:
            email_data["message"]["bccRecipients"] = bcc_recipients

        # Handle reply-to
        if message.reply_to:
            email_data["message"]["replyTo"] = [
                {"emailAddress": {"address": addr}} for addr in message.reply_to
            ]

        # Note: Attachments handling can be added here if needed
        # Microsoft Graph API supports attachments via the attachments property

        return email_data
