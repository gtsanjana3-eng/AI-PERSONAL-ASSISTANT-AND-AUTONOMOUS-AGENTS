import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./assistant.db")
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", 8000))
    
    # LLM Settings
    LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    
    # Search Settings
    SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "wikipedia")
    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")

settings = Settings()
