# config/settings/prod.py
"""
Paramètres de production.
Usage : DJANGO_SETTINGS_MODULE=config.settings.prod

Variables d'environnement requises :
  DJANGO_SECRET_KEY       — clé secrète aléatoire (≥ 50 caractères)
  DATABASE_URL            — URL complète PostgreSQL (format Render : postgresql://user:pass@host:port/db)
                            OU les variables individuelles ci-dessous :
  DB_NAME                 — nom de la base PostgreSQL
  DB_USER                 — utilisateur PostgreSQL
  DB_PASSWORD             — mot de passe PostgreSQL
  DB_HOST                 — hôte PostgreSQL (ex: localhost)
  DB_PORT                 — port PostgreSQL (ex: 5432)
  ALLOWED_HOSTS           — domaines autorisés, séparés par des virgules
"""

import os
import dj_database_url
from .base import *  # noqa: F401, F403

# Whitenoise — servir les fichiers statiques directement depuis Gunicorn
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← juste après SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# ---------------------------------------------------------------------------
# Sécurité
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Plante au démarrage si absent — voulu.

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]

# ---------------------------------------------------------------------------
# Base de données — PostgreSQL
# Render injecte DATABASE_URL automatiquement. Les variables individuelles
# (DB_NAME, DB_USER, etc.) sont acceptées comme alternative.
# ---------------------------------------------------------------------------
_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ['DB_USER'],
            'PASSWORD': os.environ['DB_PASSWORD'],
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }

# ---------------------------------------------------------------------------
# HTTPS & cookies sécurisés
# ---------------------------------------------------------------------------
# Render / Cloudflare terminent le TLS avant le serveur — on fait confiance
# au header X-Forwarded-Proto pour détecter HTTPS côté Django.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [
    f"https://{h.strip()}"
    for h in os.environ.get('ALLOWED_HOSTS', '').split(',')
    if h.strip()
]
SECURE_HSTS_SECONDS = 31536000          # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ---------------------------------------------------------------------------
# Emails — SMTP en production
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.example.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@ensmg.sn')

# ---------------------------------------------------------------------------
# Logging minimal en production — console uniquement (compatible Render)
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
