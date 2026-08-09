from .base import *

DEBUG = True
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-local-development-only")
AUDIT_HMAC_KEY = os.getenv("AUDIT_HMAC_KEY") or SECRET_KEY
SIGNATURE_HMAC_KEY = os.getenv("SIGNATURE_HMAC_KEY") or SECRET_KEY
