# config/settings/base.py
"""
Paramètres communs à tous les environnements.
Ne pas inclure ici : SECRET_KEY, DEBUG, ALLOWED_HOSTS, DATABASES.
Ces valeurs sensibles sont définies dans dev.py ou prod.py.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps projet (ordre logique)
    'core',
    'catalog',
    # 'projects',  # App en cours de développement — décommenter quand les modèles seront définis
    'audit',
    'inventory.apps.InventoryConfig',
    'purchasing.apps.PurchasingConfig',
    'documents',
    'frontend.apps.FrontendConfig',
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', BASE_DIR / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.exercices_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# Validation des mots de passe
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------------------------------------------------------------------------
# Médias (factures, pièces justificatives, etc.)
# ---------------------------------------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Clé primaire par défaut
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Logging — configuration complète avec rotation de fichiers
# Le répertoire logs/ est créé automatiquement s'il n'existe pas.
# En développement, dev.py surcharge les niveaux à DEBUG.
# Ne jamais utiliser print() dans le code — toujours logger.info/warning/error.
# ---------------------------------------------------------------------------
(BASE_DIR / 'logs').mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} — {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 Mo par fichier
            'backupCount': 5,              # 5 archives conservées
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'file_errors': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'ERROR',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Loggers applicatifs — remontent toutes les erreurs dans errors.log
        'core': {
            'handlers': ['console', 'file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['console', 'file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
        'purchasing': {
            'handlers': ['console', 'file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
        'catalog': {
            'handlers': ['console', 'file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
        'documents': {
            'handlers': ['console', 'file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
        'frontend': {
            'handlers': ['console', 'file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
