import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _production_secret_key():
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key or secret_key == "dev-secret-key-change-me":
        raise RuntimeError("SECRET_KEY must be set to a non-development value in production.")
    return secret_key


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    WTF_CSRF_TIME_LIMIT = None
    FORCE_SECURE_COOKIES = os.environ.get("FORCE_SECURE_COOKIES", "false").lower() == "true"
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'samlovesbooks.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Reading progress / font-size cookies
    READER_TOKEN_COOKIE = "reader_token"
    FONT_SIZE_COOKIE = "font_size"
    FONT_SIZE_CHOICES = ("sm", "md", "lg")
    FONT_SIZE_DEFAULT = "md"

    # Flask-Caching
    CACHE_TYPE = os.environ.get("CACHE_TYPE", "SimpleCache")
    CACHE_DEFAULT_TIMEOUT = 300

    COMPRESS_MIMETYPES = ["text/html", "text/css", "text/javascript", "application/json"]
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
    SECRET_KEY = Config.SECRET_KEY
    FORCE_SECURE_COOKIES = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
