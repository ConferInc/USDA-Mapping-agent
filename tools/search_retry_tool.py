"""
Search Retry Tool - Generates alternative search strategies for retries
"""

import os
from typing import Dict, Optional
from tools.llm_tool import generate_search_intent


def generate_retry_search_strategy(ingredient: str, attempt: int, previous_queries: list = None) -> Dict:
    """
    Generate alternative search strategy for retry attempts.
    
    Args:
        ingredient: Ingredient name
        attempt: Retry attempt number (1, 2, or 3)
        previous_queries: List of previous search queries tried
    
    Returns:
        Search intent dictionary with alternative strategy
    """
    previous_queries = previous_queries or []
    
    # Try LLM first
    intent = generate_search_intent(ingredient)
    if not intent:
        intent = {}
    
    # Strategy variations based on attempt number
    base_query = intent.get("search_query", ingredient)
    
    if attempt == 1:
        # Strategy 1: Try with common synonyms/variations
        # Split into words and try different combinations
        words = ingredient.lower().split()
        if len(words) > 1:
            # Try reverse order
            new_query = " ".join(reversed(words))
        else:
            # Try plural/singular variations
            if words[0].endswith('s'):
                new_query = words[0][:-1]
            else:
                new_query = words[0] + "s"
        
        intent["search_query"] = new_query
        intent["retry_reason"] = f"Attempt {attempt}: Trying word order/singular-plural variation"
    
    elif attempt == 2:
        # Strategy 2: Try variations and synonyms
        words = ingredient.lower().split()
        
        # Special handling for compound foods and sauces
        ingredient_lower = ingredient.lower()
        
        # Try variations for common items
        variations = {
            "tzatziki": ["tzatziki", "tzatziki dip", "tzatziki sauce"],
            "guacamole": ["guacamole", "guacamole nfs", "avocado guacamole"],
            "chutney": ["chutney", "chutney nfs", "mango chutney"],
            "brandy": ["brandy", "brandy distilled", "alcoholic beverage brandy"],
            "sorbet": ["sorbet", "sorbet frozen", "fruit sorbet"],
            "gelato": ["gelato", "gelato ice cream", "italian gelato"],
        }
        
        # Check if ingredient matches any variation pattern
        for key, variants in variations.items():
            if key in ingredient_lower:
                # Try first variation not in previous queries
                for variant in variants:
                    if variant not in previous_queries:
                        intent["search_query"] = variant
                        intent["retry_reason"] = f"Attempt {attempt}: Trying variation '{variant}'"
                        break
                if "retry_reason" in intent:
                    break
        
        # If no special variation found, try with modifiers
        if "retry_reason" not in intent:
            modifiers = ["raw", "fresh", "dried", "whole"]
            for mod in modifiers:
                if mod not in base_query.lower():
                    intent["search_query"] = f"{base_query} {mod}"
                    intent["retry_reason"] = f"Attempt {attempt}: Adding modifier '{mod}'"
                    break
            else:
                # Try without any modifiers (simpler query)
                intent["search_query"] = words[0] if words else ingredient
                intent["retry_reason"] = f"Attempt {attempt}: Simplifying query"
    
    elif attempt == 3:
        # Strategy 3: Try with category-based search
        # Try to identify category and search with category term
        category_map = {
            "rice": "grain",
            "lentil": "legume",
            "pepper": "spice",
            "cheese": "dairy",
            "oil": "fat",
            "vinegar": "condiment",
            "herb": "spice",
            "spice": "spice",
        }
        
        words = ingredient.lower().split()
        for word in words:
            for key, category in category_map.items():
                if key in word:
                    intent["search_query"] = f"{category} {word}"
                    intent["retry_reason"] = f"Attempt {attempt}: Category-based search ({category})"
                    break
            if "retry_reason" in intent:
                break
        else:
            # Last resort: just the first word
            intent["search_query"] = words[0] if words else ingredient
            intent["retry_reason"] = f"Attempt {attempt}: Minimal query (last resort)"
    
    # Ensure we don't repeat previous queries
    if intent["search_query"] in previous_queries:
        # Generate a completely different query
        words = ingredient.lower().split()
        if len(words) > 1:
            intent["search_query"] = words[-1]  # Use last word
        else:
            intent["search_query"] = ingredient  # Original as fallback
    
    return intent


