import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
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


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
