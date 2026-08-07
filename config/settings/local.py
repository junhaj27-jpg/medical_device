from .base import *

DEBUG = True
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-local-development-only")
