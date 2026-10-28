import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "django.contrib.postgres",
    "rest_framework", "corsheaders", "datapilot",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

def database_config():
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return {"ENGINE": "django.db.backends.postgresql", "NAME": parsed.path.lstrip("/"), "USER": parsed.username or "",
                "PASSWORD": parsed.password or "", "HOST": parsed.hostname or "localhost", "PORT": parsed.port or 5432,
                "CONN_MAX_AGE": 60}
    return {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}

DATABASES = {"default": database_config()}
AUTH_PASSWORD_VALIDATORS = []
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MEDIA_ROOT = BASE_DIR / "private_uploads"
MEDIA_URL = None
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DATASET_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE
REST_FRAMEWORK = {"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication", "rest_framework.authentication.BasicAuthentication"],
                  "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]}
CORS_ALLOWED_ORIGINS = [origin for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [origin for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin]
SESSION_COOKIE_SECURE = os.getenv("DJANGO_SECURE_COOKIES", "0") == "1"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "0") == "1"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
LOGIN_REDIRECT_URL = FRONTEND_URL
LOGOUT_REDIRECT_URL = FRONTEND_URL
DATASET_MAX_UPLOAD_BYTES = int(os.getenv("DATASET_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
DATASET_MAX_ROWS = int(os.getenv("DATASET_MAX_ROWS", "100000"))
DATASET_MAX_COLUMNS = int(os.getenv("DATASET_MAX_COLUMNS", "200"))
DATASET_MAX_SCHEMA_CHARS = int(os.getenv("DATASET_MAX_SCHEMA_CHARS", "20000"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_REQUEST_TIMEOUT_SECONDS = int(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "20"))
ANALYSIS_MAX_CODE_CHARS = int(os.getenv("ANALYSIS_MAX_CODE_CHARS", "12000"))
ANALYSIS_TIMEOUT_SECONDS = int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "30"))
ANALYSIS_MAX_RESULT_ROWS = int(os.getenv("ANALYSIS_MAX_RESULT_ROWS", "1000"))
ANALYSIS_MAX_RESULT_COLUMNS = int(os.getenv("ANALYSIS_MAX_RESULT_COLUMNS", "100"))
ANALYSIS_MAX_OUTPUT_BYTES = int(os.getenv("ANALYSIS_MAX_OUTPUT_BYTES", "500000"))
ANALYSIS_MAX_RETRIES = min(3, max(0, int(os.getenv("ANALYSIS_MAX_RETRIES", "3"))))
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_EMBEDDING_DIMENSIONS = int(os.getenv("GEMINI_EMBEDDING_DIMENSIONS", "768"))
DATASET_RAG_COLUMN_THRESHOLD = int(os.getenv("DATASET_RAG_COLUMN_THRESHOLD", "30"))
ANALYSIS_RAG_TOP_K = int(os.getenv("ANALYSIS_RAG_TOP_K", "15"))
ANALYSIS_RAG_MAX_COSINE_DISTANCE = float(os.getenv("ANALYSIS_RAG_MAX_COSINE_DISTANCE", "0.7"))
