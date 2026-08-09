import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.getenv("SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "rest_framework", "drf_spectacular",
    "apps.accounts", "apps.compliance", "apps.devices", "apps.adverse_events", "apps.investigations", "apps.capa",
    "apps.approvals", "apps.reports", "apps.audit", "apps.dashboard", "apps.ai_assistant",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "apps.audit.middleware.RequestIdMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
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
PRIVATE_MEDIA_ROOT = Path(os.getenv("PRIVATE_MEDIA_ROOT", BASE_DIR / "private_media"))
AUDIT_HMAC_KEY = os.getenv("AUDIT_HMAC_KEY", "")
AUDIT_HMAC_KEYS = os.getenv("AUDIT_HMAC_KEYS", "")
AUDIT_ACTIVE_KEY_ID = os.getenv("AUDIT_ACTIVE_KEY_ID", "")
AUDIT_RETENTION_DAYS = int(os.getenv("AUDIT_RETENTION_DAYS", "2555"))
SIGNATURE_HMAC_KEY = os.getenv("SIGNATURE_HMAC_KEY", "")
ATTACHMENT_MAX_SIZE = int(os.getenv("ATTACHMENT_MAX_SIZE", str(20 * 1024 * 1024)))
ATTACHMENT_MAX_FILES_PER_USER = int(os.getenv("ATTACHMENT_MAX_FILES_PER_USER", "1000"))
ATTACHMENT_MAX_UNCOMPRESSED_SIZE = int(os.getenv("ATTACHMENT_MAX_UNCOMPRESSED_SIZE", str(100 * 1024 * 1024)))
ATTACHMENT_MAX_COMPRESSION_RATIO = int(os.getenv("ATTACHMENT_MAX_COMPRESSION_RATIO", "100"))
CLAMAV_HOST = os.getenv("CLAMAV_HOST", "")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))
CLAMAV_SCAN_MAX_ATTEMPTS = int(os.getenv("CLAMAV_SCAN_MAX_ATTEMPTS", "3"))
CLAMAV_SCAN_BACKOFF_SECONDS = int(os.getenv("CLAMAV_SCAN_BACKOFF_SECONDS", "30"))
OBJECT_STORAGE_BUCKET = os.getenv("OBJECT_STORAGE_BUCKET", "")
OBJECT_STORAGE_KMS_KEY_ID = os.getenv("OBJECT_STORAGE_KMS_KEY_ID", "")
SIGNED_URL_EXPIRY_SECONDS = min(int(os.getenv("SIGNED_URL_EXPIRY_SECONDS", "300")),900)
AUDIT_EXPORT_MAX_ATTEMPTS = int(os.getenv("AUDIT_EXPORT_MAX_ATTEMPTS", "5"))
AUDIT_EXPORT_BACKOFF_SECONDS = int(os.getenv("AUDIT_EXPORT_BACKOFF_SECONDS", "60"))
AUDIT_JSONL_EXPORT_PATH = os.getenv("AUDIT_JSONL_EXPORT_PATH", str(BASE_DIR / "work" / "audit-export.jsonl"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"; LOGIN_REDIRECT_URL = "dashboard"; LOGOUT_REDIRECT_URL = "login"
REST_FRAMEWORK = {"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema", "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]}
SPECTACULAR_SETTINGS = {"TITLE": "의료기기 이상사례 API", "VERSION": "1.0.0"}
AI_ASSISTANT_ENABLED = os.getenv("AI_ASSISTANT_ENABLED", "false").lower() == "true"
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "apps.accounts.validators.KoreanUserAttributeSimilarityValidator"},
    {"NAME": "apps.accounts.validators.KoreanMinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "apps.accounts.validators.KoreanCommonPasswordValidator"},
    {"NAME": "apps.accounts.validators.PasswordComplexityValidator"},
]
