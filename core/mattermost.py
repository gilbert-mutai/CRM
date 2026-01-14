import requests
from django.conf import settings

def send_to_mattermost(message: str):
    payload = {
        "text": message,
    }
    try:
        response = requests.post(settings.MATTERMOST_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print(f"[Mattermost] Message sent successfully")
    except requests.RequestException as e:
        print(f"[Mattermost] Failed: {e}")

def send_email_alert_to_mattermost(
    subject: str,
    recipient_count: int,
    user_display: str,
    context: str = "client",
):
    """
    Send notification alerts to Mattermost for different apps.
    """

    # Map context to readable labels
    context_labels = {
        "client": "client(s)",
        "threecx": "3CX client(s)",
        "domain": "Domain & Hosting client(s)",
        "sdwan": "SD-WAN client(s)",
        "veeam": "Veeam client(s)",
    }

    label = context_labels.get(context, "client(s)")

    message = (
        f'CRM Updates: A notification with the subject "{subject}" '
        f"was successfully sent to {recipient_count} {label} by {user_display}."
    )

    payload = {
        "text": message,
    }

    try:
        response = requests.post(
            settings.MATTERMOST_WEBHOOK_URL, json=payload, timeout=10
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[Mattermost] Email Alert Failed: {e}")
