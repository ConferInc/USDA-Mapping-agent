"""
CrewAI Tools for USDA Nutrition Fetcher
"""

# USDA API Tools
from .usda_api_tool import search_usda_food, get_usda_food_details

# Mapping Tools
from .mapping_tool import load_curated_mappings, search_mappings, save_mapping

# Cache Tools
from .cache_tool import get_cached_search_intent, save_search_intent_cache, clear_cache

# Scoring Tools
from .scoring_tool import score_match_quality, filter_search_results

# LLM Tools
from .llm_tool import generate_search_intent

# Nutrition Extraction Tools
from .nutrition_extractor_tool import extract_nutrition_data

__all__ = [
    # USDA API
    "search_usda_food",
    "get_usda_food_details",
    # Mapping
    "load_curated_mappings",
    "search_mappings",
    "save_mapping",
    # Cache
    "get_cached_search_intent",
    "save_search_intent_cache",
    "clear_cache",
    # Scoring
    "score_match_quality",
    "filter_search_results",
    # LLM
    "generate_search_intent",
    # Nutrition Extraction
    "extract_nutrition_data",
]

