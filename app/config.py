from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


class BaseConfig:
    _SITE_MIRROR = Path(os.getenv("SITE_CONTENT_ROOT", "/eftx_site"))
    if not _SITE_MIRROR.is_dir():
        _SITE_MIRROR = None

    PROJECT_ROOT = str(Path(__file__).resolve().parents[1])

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
            "Quando solicitar que voce execute uma acao no sistema (ex.: criar um projeto), responda normalmente e inclua tambem "
            "uma linha no formato <action type=\"create_project\">{...}</action> com os parametros em JSON (ex.: name, "
            "antenna_name, frequency_mhz, v_count, h_count). O backend executara a acao e retornara um resumo ao usuario.\n"
            "Seus conhecimentos incluem dipolos, monopolos, Yagi-Uda, patch, microstrip, antenas parabolicas; parametros como "
            "ganho, eficiencia, largura de banda, frente-costas; ferramentas como Smith Chart e padroes de radiacao; e dicas de "
            "simulacao (malha, contorno, excitacao). Comece a conversa se apresentando de forma breve e profissional."
        ),
    )
    ASSISTANT_GREETING = os.getenv(
        "ASSISTANT_GREETING",
        "Ola! Eu sou o AntennaExpert, seu assistente para design e simulacao de antenas. Como posso ajuda-lo hoje?",
    )
    KNOWLEDGE_INDEX_DIR = os.getenv("KNOWLEDGE_INDEX_DIR", "vector_store")
    KNOWLEDGE_MODEL = os.getenv("KNOWLEDGE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    KNOWLEDGE_TOPK = int(os.getenv("KNOWLEDGE_TOPK", "3"))
    SITE_CONTENT_ROOT = os.getenv("SITE_CONTENT_ROOT", str(_SITE_MIRROR) if _SITE_MIRROR else "") or None
    COMPANY_NAME = os.getenv("COMPANY_NAME", "EFTX Telecom")
    COMPANY_PHONE = os.getenv("COMPANY_PHONE", "(19) 98145-6085 / (19) 4117-0270")
    COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "contato@eftx.com.br")
    COMPANY_WHATSAPP = os.getenv("COMPANY_WHATSAPP", "5519998537007")
    COMPANY_ADDRESS = os.getenv(
        "COMPANY_ADDRESS",
        "Rua Higyno Guilherme Costato, 298 - Jardim Pinheiros - Valinhos/SP",
    )
    COMPANY_INSTAGRAM = os.getenv("COMPANY_INSTAGRAM", "https://www.instagram.com/iftx_broadcast/")
    COMPANY_FACEBOOK = os.getenv("COMPANY_FACEBOOK", "https://www.facebook.com/iftxbroadcast")
    COMPANY_LINKEDIN = os.getenv(
        "COMPANY_LINKEDIN",
        "https://www.linkedin.com/company/iftx-broadcast-television-radio",
    )
    COMPANY_MAP_EMBED = os.getenv(
        "COMPANY_MAP_EMBED",
        "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d918.4187471130787!2d-46.981851682980846!3d-22.962193779764863!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x94c8cd8a8bcf404d%3A0xdec6808ca80b75c6!2sR.%20Higyno%20Guilherme%20Costato%2C%20298%20-%20Jardim%20Pinheiros%2C%20Valinhos%20-%20SP%2C%2013274-410!5e0!3m2!1spt-BR!2sbr!4v1653476192489!5m2!1spt-BR!2sbr",
    )
    SITE_UPLOAD_ROOT = os.getenv("SITE_UPLOAD_ROOT", "site_uploads")


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
