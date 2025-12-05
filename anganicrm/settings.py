from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
from django.contrib.messages import constants as messages_constants


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

# Application definition

INSTALLED_APPS = [
    "accounts", 
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "threecx",
    "domains",
    "sdwan",
    "veeam",
    "pm",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.Enforce2FAMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "anganicrm.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "anganicrm.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"


# Default is UTC
TIME_ZONE = "Africa/Nairobi"

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = BASE_DIR / "staticfiles"


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Use namespaced login URL so reverse('accounts:login') works for redirects
LOGIN_URL = 'accounts:login'


MESSAGE_TAGS = {
    messages_constants.DEBUG: "secondary",
    messages_constants.INFO: "info",
    messages_constants.SUCCESS: "success",
    messages_constants.WARNING: "warning",
    messages_constants.ERROR: "danger",
}


AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Expire activation / password reset tokens after 3 days
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 7  # 7 days in seconds  

# Session expiry: 30 minutes of inactivity
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True



# Email Setup - OAuth2 with Microsoft Graph API
EMAIL_BACKEND = "core.oauth2_email_backend.OAuth2EmailBackend"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")  # The email address that will send emails
DEFAULT_FROM_EMAIL = os.getenv("EMAIL_HOST_USER")

# OAuth2 Credentials for Microsoft Graph API
OAUTH2_CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID")
OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET")
OAUTH2_TENANT_ID = os.getenv("OAUTH2_TENANT_ID") 

# Completion certificate CC recipients
if DEBUG:
    CERTIFICATE_CC_EMAILS = [
        "uncofits@gmail.com",
        "gilbert@angani.co",
    ]
else:
    CERTIFICATE_CC_EMAILS = [
        "support@angani.co",
        "salesadmin@angani.co",
    ]


MATTERMOST_WEBHOOK_URL = os.getenv("MATTERMOST_WEBHOOK_URL")
MATTERMOST_CHANNEL = os.getenv("MATTERMOST_CHANNEL", "general")
MATTERMOST_USERNAME = os.getenv("MATTERMOST_USERNAME", "django-bot")

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
