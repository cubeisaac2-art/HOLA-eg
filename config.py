import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def database_url():
    configured_url = os.environ.get("DATABASE_URL")
    if not configured_url:
        return f"sqlite:///{BASE_DIR / 'app.db'}"
    if configured_url.startswith("postgres://"):
        return configured_url.replace("postgres://", "postgresql+psycopg://", 1)
    if configured_url.startswith("postgresql://"):
        return configured_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return configured_url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True

    UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    APP_NAME = "HOLA GUINEA"
    APP_VERSION = "1.0.0"

    # VAPID keys for local development; override via env in production.
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "BB8uqv7ZxSbbU3Yrxx1wP7UAapacZqhCgce8JNwPoxt2Ese9Zk9nP8EnlO9dLFD1Mo82B7c0OWYzB5QaT2DOQ_E")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgAIZgDqxgG7zrgY62\n9AQ79j3vAVwsr3nC+Obpo89j9U+hRANCAAQfLqr+2cUm21N2K8cdcD+1AGqWnGao\nQoHHvCTcD6MbdhLHvWZPZz/BJ5TvXSxQ9TKPNge3NDlmMweUGk9gzkPx\n-----END PRIVATE KEY-----")
    VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "admin@holaguinea.com")
    EMBASSY_VISA_URL = os.environ.get("EMBASSY_VISA_URL", "https://www.guineaecuatorialembassy.com/")

    LANGUAGES = ["es", "fr"]
    DEFAULT_LANGUAGE = "es"

    # PWA defaults
    PWA_NAME = "HOLA GUINEA"
    PWA_SHORT_NAME = "HOLA GUINEA"
    PWA_THEME_COLOR = "#0f172a"
    PWA_BACKGROUND_COLOR = "#f8fafc"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
