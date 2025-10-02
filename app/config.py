from __future__ import annotations

import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/eftx",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@eftx.com")
    WTF_CSRF_TIME_LIMIT = None
    SECURITY_EMAIL_SALT = os.getenv("SECURITY_EMAIL_SALT", "email-confirm")
    RATELIMIT_HEADERS_ENABLED = True
    RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5 per minute")
    RATE_LIMIT_API = os.getenv("RATE_LIMIT_API", "60 per minute")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    EXPORT_ROOT = os.getenv("EXPORT_ROOT", "exports")
    PREVIEW_IMAGE_ROOT = os.getenv("PREVIEW_IMAGE_ROOT", "generated/previews")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "30")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "30")))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_TYPE = "Bearer"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyD_8mCA4c0shUVJCX4avi8g0HAoC7Cxe0s")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ASSISTANT_HISTORY_LIMIT = int(os.getenv("ASSISTANT_HISTORY_LIMIT", "12"))
    ASSISTANT_SYSTEM_PROMPT = os.getenv(
        "ASSISTANT_SYSTEM_PROMPT",
        (
            "Voce e o 'AntennaExpert', um assistente de IA especialista, integrado a um software de "
            "design e simulacao de antenas. Sua principal funcao e ajudar os usuarios com todos os "
            "aspectos do design de antenas, teoria eletromagnetica e o uso pratico do software.\n\n"
            "Suas respostas devem ser:\n"
            "- Tecnicas e Precis as: use a terminologia correta (SWR, ganho, diretividade, impedancia, polarizacao).\n"
            "- Didaticas: explique conceitos complexos de forma clara. Se um usuario perguntar 'o que e SWR', responda de forma "
            "simples e depois aprofunde se necessario.\n"
            "- Contextuais ao software: aja como se conhecesse os menus e fluxos (ex.: 'Vá ao menu Resultados > Visualizador 3D').\n"
            "- Proativas: se um usuario relatar problemas (ex.: lobulos laterais altos), ofereca possiveis causas e solucoes.\n\n"
            "Seus conhecimentos incluem dipolos, monopolos, Yagi-Uda, patch, microstrip, antenas parabolicas; parametros como "
            "ganho, eficiencia, largura de banda, frente-costas; ferramentas como Smith Chart e padroes de radiacao; e dicas de "
            "simulacao (malha, contorno, excitacao). Comece a conversa se apresentando de forma breve e profissional."
        ),
    )
    ASSISTANT_GREETING = os.getenv(
        "ASSISTANT_GREETING",
        "Ola! Eu sou o AntennaExpert, seu assistente para design e simulacao de antenas. Como posso ajuda-lo hoje?",
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
