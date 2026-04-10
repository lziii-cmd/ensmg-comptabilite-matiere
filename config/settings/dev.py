# config/settings/dev.py
"""
Paramètres de développement local.
Usage : DJANGO_SETTINGS_MODULE=config.settings.dev  (valeur par défaut dans manage.py)
"""

import os
from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Sécurité — mode développement uniquement
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-key-a-ne-jamais-utiliser-en-production'
)

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# ---------------------------------------------------------------------------
# Base de données — SQLite locale
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ---------------------------------------------------------------------------
# Emails — affichés dans la console en dev
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ---------------------------------------------------------------------------
# Logging — niveau DEBUG en développement
# On surcharge les niveaux définis dans base.py pour tout voir dans la console.
# ---------------------------------------------------------------------------
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
for _app in ('core', 'inventory', 'purchasing', 'catalog', 'documents', 'frontend'):
    if _app in LOGGING['loggers']:
        LOGGING['loggers'][_app]['level'] = 'DEBUG'

# Silence le watcher de fichiers qui génère des centaines de lignes DEBUG au rechargement
LOGGING['loggers']['django.utils.autoreload'] = {
    'handlers': ['console'],
    'level': 'WARNING',
    'propagate': False,
}
