"""
Configuration Utilities
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for USDA Nutrition Fetcher"""
    
    # USDA API Configuration
    USDA_API_KEY: Optional[str] = os.getenv("USDA_API_KEY")
    USDA_BASE_URL: str = "https://api.nal.usda.gov/fdc/v1"
    
    # OpenAI/LLM Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL")
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    
    # File Paths
    CURATED_MAPPING_FILE: str = os.getenv("CURATED_MAPPING_FILE", "common_ingredients_mapping.json")
    CACHE_FILE: str = os.getenv("CACHE_FILE", "ingredient_search_mapping.json")
    
    # API Settings
    RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "0.5"))  # seconds
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    TIMEOUT: int = int(os.getenv("TIMEOUT", "45"))  # seconds
    
    # Search Settings
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    DEFAULT_DATA_TYPE: str = os.getenv("DEFAULT_DATA_TYPE", "Foundation,SR Legacy")
    
    # Scoring Settings
    MAX_ACCEPTABLE_SCORE: int = int(os.getenv("MAX_ACCEPTABLE_SCORE", "50"))
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.USDA_API_KEY:
            raise ValueError(
                "USDA_API_KEY is required. Set it in .env file or environment variable.\n"
                "Get your free API key at: https://api.data.gov/signup/"
            )
        return True
    
    @classmethod
    def get_llm_config(cls) -> dict:
        """Get LLM configuration dictionary"""
        config = {
            "api_key": cls.OPENAI_API_KEY,
            "model_name": cls.OPENAI_MODEL_NAME
        }
        if cls.OPENAI_BASE_URL:
            config["base_url"] = cls.OPENAI_BASE_URL
        return config


