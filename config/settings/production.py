from .base import *

required = ["SECRET_KEY", "ALLOWED_HOSTS", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "SIGNATURE_HMAC_KEY"]
missing = [name for name in required if not os.getenv(name)]
if not os.getenv("AUDIT_HMAC_KEY") and not (os.getenv("AUDIT_HMAC_KEYS") and os.getenv("AUDIT_ACTIVE_KEY_ID")):
    missing.append("AUDIT_HMAC_KEY or AUDIT_HMAC_KEYS + AUDIT_ACTIVE_KEY_ID")
if missing:
    raise RuntimeError(f"운영 환경 필수 환경변수가 없습니다: {', '.join(missing)}")

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": os.environ["POSTGRES_DB"], "USER": os.environ["POSTGRES_USER"], "PASSWORD": os.environ["POSTGRES_PASSWORD"], "HOST": os.environ["POSTGRES_HOST"], "PORT": os.getenv("POSTGRES_PORT", "5432")}}
