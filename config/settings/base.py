from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-development-key-change-me")
DEBUG = False
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "rest_framework", "drf_spectacular",
    "apps.accounts", "apps.devices", "apps.adverse_events", "apps.investigations", "apps.capa",
    "apps.approvals", "apps.reports", "apps.audit", "apps.dashboard", "apps.ai_assistant",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "accounts.User"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
LANGUAGE_CODE = "ko-kr"; TIME_ZONE = "Asia/Seoul"; USE_I18N = True; USE_TZ = True
STATIC_URL = "static/"; STATIC_ROOT = BASE_DIR / "staticfiles"; STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"; MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"; LOGIN_REDIRECT_URL = "dashboard"; LOGOUT_REDIRECT_URL = "login"
REST_FRAMEWORK = {"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema", "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]}
SPECTACULAR_SETTINGS = {"TITLE": "의료기기 이상사례 API", "VERSION": "1.0.0"}
AI_ASSISTANT_ENABLED = os.getenv("AI_ASSISTANT_ENABLED", "false").lower() == "true"
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
