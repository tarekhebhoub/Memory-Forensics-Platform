"""
Django settings for the Memory Forensics Platform (MFP).

Production-ready, environment-driven configuration.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import environ

# ──────────────────────────────────────────────────────────────────────
# Paths & environment
# ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    AI_ENABLED=(bool, False),
    JWT_ACCESS_LIFETIME_MIN=(int, 30),
    JWT_REFRESH_LIFETIME_DAYS=(int, 7),
    MAX_UPLOAD_SIZE_MB=(int, 8192),
    VOLATILITY_TIMEOUT=(int, 1800),
)
# Load .env from project root if it exists
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# ──────────────────────────────────────────────────────────────────────
# Applications
# ──────────────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.authentication",
    "apps.audit",
    "apps.cases",
    "apps.evidence",
    "apps.analysis",
    "apps.reports",
    "apps.timeline",
    "apps.ioc",
    "apps.ai_engine",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.audit.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "mfp.urls"
WSGI_APPLICATION = "mfp.wsgi.application"
ASGI_APPLICATION = "mfp.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ──────────────────────────────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'data' / 'db.sqlite3'}",
    )
}

# ──────────────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "authentication.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ──────────────────────────────────────────────────────────────────────
# I18N / Static / Media
# ──────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "data" / "media")))
EVIDENCE_ROOT = Path(env("EVIDENCE_ROOT", default=str(BASE_DIR / "data" / "evidence")))
REPORT_ROOT = Path(env("REPORT_ROOT", default=str(BASE_DIR / "data" / "reports")))
for _p in (MEDIA_ROOT, EVIDENCE_ROOT, REPORT_ROOT):
    _p.mkdir(parents=True, exist_ok=True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Upload limits
MAX_UPLOAD_SIZE_MB = env("MAX_UPLOAD_SIZE_MB")
DATA_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024  # 25 MiB in memory then stream
FILE_UPLOAD_MAX_MEMORY_SIZE = 25 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# ──────────────────────────────────────────────────────────────────────
# DRF + JWT
# ──────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("RATE_LIMIT_ANON", default="30/min"),
        "user": env("RATE_LIMIT_USER", default="120/min"),
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("JWT_ACCESS_LIFETIME_MIN")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_LIFETIME_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Memory Forensics Platform API",
    "DESCRIPTION": "REST API for the MFP DFIR platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ──────────────────────────────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost", "http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_CREDENTIALS = True

# ──────────────────────────────────────────────────────────────────────
# Celery
# ──────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 60 * 60 * 2  # 2h hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 60

# ──────────────────────────────────────────────────────────────────────
# Volatility
# ──────────────────────────────────────────────────────────────────────
VOLATILITY_BIN = env("VOLATILITY_BIN", default="vol")
VOLATILITY_TIMEOUT = env("VOLATILITY_TIMEOUT")
VOLATILITY_SYMBOLS_DIR = env(
    "VOLATILITY_SYMBOLS_DIR",
    default=str(BASE_DIR / "data" / "volatility_symbols"),
)
Path(VOLATILITY_SYMBOLS_DIR).mkdir(parents=True, exist_ok=True)
VOLATILITY_PLUGINS = env.list(
    "VOLATILITY_PLUGINS",
    default=[
        "windows.pslist", "windows.pstree", "windows.netscan",
        "windows.cmdline", "windows.dlllist", "windows.handles",
        "windows.malfind", "windows.filescan", "windows.hashdump",
        "windows.sessions", "windows.svcscan",
    ],
)
VOLATILITY_PLUGINS_DEEP = env.list(
    "VOLATILITY_PLUGINS_DEEP",
    default=[
        # All standard plugins …
        "windows.pslist", "windows.pstree", "windows.psscan",
        "windows.cmdline", "windows.dlllist", "windows.handles",
        "windows.ldrmodules", "windows.malfind", "windows.vadinfo",
        "windows.netscan", "windows.netstat",
        "windows.svcscan", "windows.sessions",
        # … plus the deep / kernel-level set
        "windows.modules", "windows.modscan", "windows.driverscan",
        "windows.callbacks", "windows.ssdt", "windows.driverirp",
        "windows.mutantscan", "windows.envars", "windows.privileges",
        "windows.filescan", "windows.hashdump", "windows.cachedump",
        "windows.lsadump", "windows.getsids",
        "windows.registry.hivelist", "windows.registry.userassist",
    ],
)

# ──────────────────────────────────────────────────────────────────────
# AI engine
# ──────────────────────────────────────────────────────────────────────
AI_ENABLED = env("AI_ENABLED")
AI_PROVIDER = env("AI_PROVIDER", default="openai")
AI_API_KEY = env("AI_API_KEY", default="")
AI_MODEL = env("AI_MODEL", default="gpt-4o-mini")

# ──────────────────────────────────────────────────────────────────────
# Security headers
# ──────────────────────────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # frontend reads it
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ──────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "mfp": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
