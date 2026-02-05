"""
Mapping Tools for Curated Ingredient Mappings
"""

import os
import json
from typing import Dict, Optional


CURATED_MAPPING_FILE = "common_ingredients_mapping.json"
_mappings_cache: Optional[Dict] = None


def _load_mappings() -> Dict:
    """Load curated mappings from file (with caching)"""
    global _mappings_cache
    
    if _mappings_cache is not None:
        return _mappings_cache
    
    # Try to load from nutrition_usda directory first (existing location)
    possible_paths = [
        CURATED_MAPPING_FILE,
        f"../nutrition_usda/{CURATED_MAPPING_FILE}",
        os.path.join(os.path.dirname(__file__), "..", "..", "nutrition_usda", CURATED_MAPPING_FILE)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    _mappings_cache = json.load(f)
                    print(f"Loaded {len(_mappings_cache)} curated ingredient mappings from {path}")
                    return _mappings_cache
            except Exception as e:
                print(f"Warning: Could not load mappings from {path}: {e}")
                continue
    
    print("Note: No curated mapping file found. Will use search for all ingredients.")
    _mappings_cache = {}
    return _mappings_cache


def _fuzzy_match(ingredient: str, mappings: Dict) -> Optional[str]:
    """
    Perform fuzzy matching to find ingredient in mappings.
    Handles:
    - Exact match (case-insensitive)
    - Plural/singular variations
    - Common variations
    """
    ingredient_lower = ingredient.lower().strip()
    
    # Exact match
    if ingredient_lower in mappings:
        return ingredient_lower
    
    # Try with/without 's' (plural/singular)
    if ingredient_lower.endswith('s'):
        singular = ingredient_lower[:-1]
        if singular in mappings:
            return singular
    else:
        plural = ingredient_lower + 's'
        if plural in mappings:
            return plural
        # Also try 'es' plural
        plural_es = ingredient_lower + 'es'
        if plural_es in mappings:
            return plural_es
    
    # Try common variations
    variations = [
        ingredient_lower.replace(' ', '_'),
        ingredient_lower.replace('_', ' '),
        ingredient_lower.replace('-', ' '),
        ingredient_lower.replace(' ', '-'),
    ]
    
    for variation in variations:
        if variation in mappings:
            return variation
    
    return None


def load_curated_mappings(file_path: Optional[str] = None) -> Dict:
    """
    Load curated ingredient mappings from JSON file.
    
    Args:
        file_path: Optional path to mapping file. If not provided, uses default location.
    
    Returns:
        Dictionary mapping ingredient names (lowercase) to mapping data:
        {
            "ingredient_name": {
                "fdc_id": int,
                "description": str,
                "data_type": str,
                "verified": bool,
                "notes": str
            }
        }
    """
    global _mappings_cache
    
    if file_path:
        # Reset cache if custom path provided
        _mappings_cache = None
        global CURATED_MAPPING_FILE
        CURATED_MAPPING_FILE = file_path
    
    return _load_mappings()


def search_mappings(ingredient: str, mappings: Optional[Dict] = None) -> Optional[Dict]:
    """
    Search for ingredient in curated mappings with fuzzy matching.
    
    Args:
        ingredient: Ingredient name to search for
        mappings: Optional mappings dictionary. If not provided, loads from file.
    
    Returns:
        Mapping data if found, None otherwise:
        {
            "fdc_id": int,
            "description": str,
            "data_type": str,
            "verified": bool,
            "notes": str
        }
    """
    if mappings is None:
        mappings = _load_mappings()
    
    # Try fuzzy match
    matched_key = _fuzzy_match(ingredient, mappings)
    
    if matched_key:
        return mappings[matched_key]
    
    return None


def save_mapping(ingredient: str, fdc_id: int, description: str, 
                 data_type: str = "Foundation", verified: bool = False, 
                 notes: str = "", file_path: Optional[str] = None) -> bool:
    """
    Save a new mapping to the curated mappings file.
    
    Args:
        ingredient: Ingredient name (will be lowercased)
        fdc_id: FoodData Central ID
        description: Food description from USDA
        data_type: Type of data (Foundation, SR Legacy, Branded)
        verified: Whether this mapping has been verified
        notes: Optional notes about the mapping
        file_path: Optional path to mapping file
    
    Returns:
        True if saved successfully, False otherwise
    """
    global _mappings_cache
    
    if file_path:
        global CURATED_MAPPING_FILE
        CURATED_MAPPING_FILE = file_path
    
    mappings = _load_mappings()
    
    ingredient_lower = ingredient.lower().strip()
    mappings[ingredient_lower] = {
        "fdc_id": fdc_id,
        "description": description,
        "data_type": data_type,
        "verified": verified,
        "notes": notes
    }
    
    # Save to file
    possible_paths = [
        CURATED_MAPPING_FILE,
        f"../nutrition_usda/{CURATED_MAPPING_FILE}",
        os.path.join(os.path.dirname(__file__), "..", "..", "nutrition_usda", CURATED_MAPPING_FILE)
    ]
    
    for path in possible_paths:
        if os.path.exists(path) or path == CURATED_MAPPING_FILE:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(mappings, f, indent=2, ensure_ascii=False)
                _mappings_cache = mappings  # Update cache
                print(f"✓ Saved mapping for '{ingredient_lower}' to {path}")
                return True
            except Exception as e:
                print(f"Error saving mapping to {path}: {e}")
                continue
    
    print(f"Error: Could not find mapping file to save to")
    return False

