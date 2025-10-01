# --- config.py (NEW) ---
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key')
    
    # Firebase Configuration
    FIREBASE_SERVICE_ACCOUNT = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    
    # Celery Configuration
    # Use Redis as the message broker and result backend
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    # OpenAI / OpenRouter Configuration
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_MODELS = {
        "deepseek": "deepseek/deepseek-chat",
        "maverick": "anthropic/claude-3-opus",
        "qwen": "qwen/qwen-2.5-72b",
        "glm": "glm-4.5-air",
        "grok": "xai/grok-4"
    }
    
    # Algolia Configuration (from original code)
    ALGOLIA_APP_ID = os.environ.get('ALGOLIA_APP_ID', '')
    ALGOLIA_SEARCH_KEY = os.environ.get('ALGOLIA_SEARCH_KEY', '')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config_by_name = dict(
    development=DevelopmentConfig,
    production=ProductionConfig
)