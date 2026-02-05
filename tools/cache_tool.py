"""
Cache Tools for LLM Search Intent
"""

import os
import json
import threading
from typing import Dict, Optional
from datetime import datetime


CACHE_FILE = "ingredient_search_mapping.json"
_cache_lock = threading.Lock()
_cache: Optional[Dict] = None


def _load_cache() -> Dict:
    """Load cache from file (with in-memory caching)"""
    global _cache
    
    if _cache is not None:
        return _cache
    
    # Try multiple possible paths
    possible_paths = [
        CACHE_FILE,
        f"../nutrition_usda/{CACHE_FILE}",
        os.path.join(os.path.dirname(__file__), "..", "..", "nutrition_usda", CACHE_FILE)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    _cache = data.get("mappings", {})
                    return _cache
            except Exception as e:
                print(f"Warning: Could not load cache from {path}: {e}")
                continue
    
    _cache = {}
    return _cache


def _save_cache():
    """Save cache to file (thread-safe)"""
    global _cache
    
    with _cache_lock:
        if _cache is None:
            return
        
        cache_data = {
            "metadata": {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "total_ingredients": len(_cache)
            },
            "mappings": _cache
        }
        
        # Try multiple possible paths
        possible_paths = [
            CACHE_FILE,
            f"../nutrition_usda/{CACHE_FILE}",
            os.path.join(os.path.dirname(__file__), "..", "..", "nutrition_usda", CACHE_FILE)
        ]
        
        for path in possible_paths:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                return
            except Exception as e:
                if path == possible_paths[-1]:  # Last attempt
                    print(f"Warning: Could not save cache to {path}: {e}")


def get_cached_search_intent(ingredient: str) -> Optional[Dict]:
    """
    Get cached search intent for an ingredient.
    
    Args:
        ingredient: Ingredient name
    
    Returns:
        Cached search intent dictionary if found, None otherwise:
        {
            "search_query": str,
            "is_phrase": bool,
            "preferred_form": str,
            "avoid": List[str],
            "expected_pattern": str
        }
    """
    cache = _load_cache()
    ingredient_lower = ingredient.lower().strip()
    return cache.get(ingredient_lower)


def save_search_intent_cache(ingredient: str, search_intent: Dict) -> bool:
    """
    Save search intent to cache.
    
    Args:
        ingredient: Ingredient name
        search_intent: Search intent dictionary:
        {
            "search_query": str,
            "is_phrase": bool,
            "preferred_form": str,
            "avoid": List[str],
            "expected_pattern": str
        }
    
    Returns:
        True if saved successfully
    """
    global _cache
    
    cache = _load_cache()
    ingredient_lower = ingredient.lower().strip()
    cache[ingredient_lower] = search_intent
    _cache = cache
    _save_cache()
    return True


def clear_cache() -> bool:
    """
    Clear the search intent cache.
    
    Returns:
        True if cleared successfully
    """
    global _cache
    _cache = {}
    _save_cache()
    return True

