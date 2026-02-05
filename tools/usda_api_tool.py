"""
USDA FoodData Central API Tools for CrewAI
Enhanced with fast-path nutrition profile function
"""

import os
import time
import requests
from typing import List, Dict, Optional, Any


class USDAApiClient:
    """Client for USDA FoodData Central API"""
    
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    SEARCH_ENDPOINT = f"{BASE_URL}/foods/search"
    FOOD_ENDPOINT = f"{BASE_URL}/food"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("USDA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set USDA_API_KEY environment variable.\n"
                "Get your free API key at: https://api.data.gov/signup/"
            )
        self.session = requests.Session()
        self.rate_limit_delay = 0.5  # 500ms delay between requests
        self.max_retries = 3
        self.timeout = 45
    
    def search_food(self, query: str, page_size: int = 50, data_type_filter: str = None) -> List[Dict]:
        """Search for foods matching the query."""
        params = {
            "query": query,
            "pageSize": min(page_size, 200),
            "api_key": self.api_key
        }
        
        if data_type_filter:
            params["dataType"] = data_type_filter
        else:
            params["dataType"] = "Foundation,SR Legacy"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    self.SEARCH_ENDPOINT,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                return data.get("foods", [])
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"  Timeout searching for '{query}', retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Error searching for '{query}': Request timed out")
                    return []
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"  Error searching for '{query}', retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Error searching for '{query}': {e}")
                    return []
            finally:
                if attempt == self.max_retries - 1:
                    time.sleep(self.rate_limit_delay)
        
        return []
    
    def get_food_details(self, fdc_id: int) -> Optional[Dict]:
        """Get detailed nutrition information for a specific FDC ID."""
        params = {"api_key": self.api_key}
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    f"{self.FOOD_ENDPOINT}/{fdc_id}",
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"    Timeout fetching FDC ID {fdc_id}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"    Error fetching FDC ID {fdc_id}: Request timed out")
                    return None
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 2
                    print(f"    Error fetching FDC ID {fdc_id}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"    Error fetching FDC ID {fdc_id}: {e}")
                    return None
            finally:
                if attempt == self.max_retries - 1:
                    time.sleep(self.rate_limit_delay)
        
        return None


# Global client instance
_api_client = None

def get_api_client() -> USDAApiClient:
    """Get or create USDA API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = USDAApiClient()
    return _api_client


def search_usda_food(query: str, page_size: int = 50, data_type: str = "Foundation,SR Legacy") -> List[Dict]:
    """
    Search USDA FoodData Central API for foods matching the query.
    
    Args:
        query: Food name or search terms
        page_size: Number of results to return (max 200, default 50)
        data_type: Filter by data type (default: "Foundation,SR Legacy")
    
    Returns:
        List of food items from search results, each containing:
        - fdcId: FoodData Central ID
        - description: Food description
        - dataType: Type of data (Foundation, SR Legacy, Branded)
        - foodNutrients: Optional nutrient data
    """
    client = get_api_client()
    return client.search_food(query, page_size, data_type)


def search_usda_food_multi_tier(query: str, page_size: int = 50, ingredient: str = None) -> List[Dict]:
    """
    Multi-tier search strategy to find foods across different data types.
    This ensures we capture Survey (FNDDS) items like "Tzatziki dip", "Guacamole, NFS", etc.
    
    Strategy:
    1. Tier 1: Search Foundation,SR Legacy (preferred generic foods)
    2. Tier 2: Search Survey (FNDDS) if Tier 1 has < 10 results or no good matches
    3. Tier 3: Search all types (excluding Branded) if still no good matches
    4. Merge and deduplicate results, prioritizing Foundation/SR Legacy but including Survey if better match
    
    Args:
        query: Food name or search terms
        page_size: Number of results per tier (max 200, default 50)
        ingredient: Original ingredient name (for enhanced scoring)
    
    Returns:
        List of food items from search results, merged and deduplicated
    """
    from .scoring_tool import _score_relevance_advanced
    
    client = get_api_client()
    all_results = []
    seen_fdc_ids = set()
    
    # Tier 1: Foundation,SR Legacy (preferred)
    tier1_results = client.search_food(query, page_size, data_type_filter="Foundation,SR Legacy")
    for result in tier1_results:
        fdc_id = result.get("fdcId")
        if fdc_id and fdc_id not in seen_fdc_ids:
            result["_search_tier"] = 1  # Mark tier for prioritization
            all_results.append(result)
            seen_fdc_ids.add(fdc_id)
    
    # Tier 2: Survey (FNDDS) - important for items like "Tzatziki dip", "Guacamole, NFS"
    # Only search if Tier 1 has < 10 results (might be missing Survey items)
    if len(tier1_results) < 10:
        tier2_results = client.search_food(query, page_size, data_type_filter="Survey (FNDDS)")
        for result in tier2_results:
            fdc_id = result.get("fdcId")
            if fdc_id and fdc_id not in seen_fdc_ids:
                result["_search_tier"] = 2
                all_results.append(result)
                seen_fdc_ids.add(fdc_id)
    
    # Tier 3: All types (excluding Branded) - fallback
    # Only search if we have very few results
    if len(all_results) < 5:
        tier3_results = client.search_food(query, page_size, data_type_filter=None)
        for result in tier3_results:
            fdc_id = result.get("fdcId")
            data_type = result.get("dataType", "")
            # Exclude Branded products
            if fdc_id and fdc_id not in seen_fdc_ids and data_type != "Branded":
                result["_search_tier"] = 3
                all_results.append(result)
                seen_fdc_ids.add(fdc_id)
    
    # Score and rank all results using enhanced scoring
    # This ensures Foundation/SR Legacy are prioritized, but Survey items can rank higher if better match
    if ingredient:
        scored_results = [
            (result, _score_relevance_advanced(result, ingredient, idx))
            for idx, result in enumerate(all_results)
        ]
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        # Return top results (up to page_size)
        return [result for result, score in scored_results[:page_size]]
    else:
        # If no ingredient provided, prioritize by tier and return top results
        # Tier 1 (Foundation/SR Legacy) first, then Tier 2 (Survey), then Tier 3
        all_results.sort(key=lambda x: (x.get("_search_tier", 999), x.get("fdcId", 0)))
        return all_results[:page_size]


def search_usda_food_multi_tier_comprehensive(query: str, ingredient: str = None) -> List[Dict]:
    """
    Comprehensive 4-tier search strategy - ALWAYS searches all tiers with fixed limits.
    This ensures comprehensive coverage of all data types in a single search.
    
    Strategy:
    1. Tier 1: Foundation,SR Legacy - 30 results (preferred generic foods)
    2. Tier 2: Survey (FNDDS) - 20 results (prepared foods like "Tzatziki dip", "Guacamole, NFS")
    3. Tier 3: Branded - 20 results (branded products for rare ingredients)
    4. Tier 4: All types - 10 results (catch-all for anything missed)
    
    Total: Up to 80 results, merged, deduplicated, and scored
    
    Args:
        query: Food name or search terms
        ingredient: Original ingredient name (for enhanced scoring)
    
    Returns:
        List of up to 80 food items, merged from all tiers, deduplicated, and scored
    """
    from .scoring_tool import _score_relevance_advanced
    
    client = get_api_client()
    all_results = []
    seen_fdc_ids = set()
    
    # Tier 1: Foundation,SR Legacy - 30 results (ALWAYS)
    tier1_results = client.search_food(query, page_size=30, data_type_filter="Foundation,SR Legacy")
    for result in tier1_results:
        fdc_id = result.get("fdcId")
        if fdc_id and fdc_id not in seen_fdc_ids:
            result["_search_tier"] = 1  # Mark tier for prioritization
            all_results.append(result)
            seen_fdc_ids.add(fdc_id)
    
    # Tier 2: Survey (FNDDS) - 20 results (ALWAYS)
    tier2_results = client.search_food(query, page_size=20, data_type_filter="Survey (FNDDS)")
    for result in tier2_results:
        fdc_id = result.get("fdcId")
        if fdc_id and fdc_id not in seen_fdc_ids:
            result["_search_tier"] = 2
            all_results.append(result)
            seen_fdc_ids.add(fdc_id)
    
    # Tier 3: Branded - 20 results (ALWAYS) - NEW
    tier3_results = client.search_food(query, page_size=20, data_type_filter="Branded")
    for result in tier3_results:
        fdc_id = result.get("fdcId")
        if fdc_id and fdc_id not in seen_fdc_ids:
            result["_search_tier"] = 3
            all_results.append(result)
            seen_fdc_ids.add(fdc_id)
    
    # Tier 4: All types (no filter) - 10 results (ALWAYS)
    tier4_results = client.search_food(query, page_size=10, data_type_filter=None)
    for result in tier4_results:
        fdc_id = result.get("fdcId")
        if fdc_id and fdc_id not in seen_fdc_ids:
            result["_search_tier"] = 4
            all_results.append(result)
            seen_fdc_ids.add(fdc_id)
    
    # Score and rank all results using enhanced scoring
    # This ensures Foundation/SR Legacy are prioritized, but other tiers can rank higher if better match
    if ingredient:
        scored_results = [
            (result, _score_relevance_advanced(result, ingredient, idx))
            for idx, result in enumerate(all_results)
        ]
        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        # Return top 80 results
        return [result for result, score in scored_results[:80]]
    else:
        # If no ingredient provided, prioritize by tier and return top 80
        # Tier 1 (Foundation/SR Legacy) first, then Tier 2 (Survey), then Tier 3 (Branded), then Tier 4
        all_results.sort(key=lambda x: (x.get("_search_tier", 999), x.get("fdcId", 0)))
        return all_results[:80]


def get_usda_food_details(fdc_id: int) -> Optional[Dict]:
    """
    Get detailed nutrition information for a specific FDC ID.
    
    Args:
        fdc_id: FoodData Central ID
    
    Returns:
        Detailed food information including:
        - fdcId: FoodData Central ID
        - description: Food description
        - dataType: Type of data
        - foodNutrients: Complete nutrient data array
        - brandOwner: Brand owner (if applicable)
    """
    client = get_api_client()
    return client.get_food_details(fdc_id)


def get_ingredient_nutrition_profile_fast(query: str) -> Optional[Dict[str, Any]]:
    """
    Fast-path function to get generic nutrition profile for an ingredient.
    Uses intelligent relevance scoring to find the best match.
    Prioritizes Foundation, SR Legacy, or Survey data types for generic nutrition information.
    
    This is a convenience function that combines search + scoring + selection in one call.
    Useful as a fast-path before going through the full LLM-based verification workflow.
    
    Note: Nutritional values are standardized per 100 grams for Foundation, SR Legacy, and Survey data types.
    
    Args:
        query: Search query string (e.g., "whole milk", "apple")
    
    Returns:
        Dictionary containing generic ingredient nutrition profile with:
        - fdcId: FoodData Central ID
        - description: Food description
        - dataType: Type of data
        - foodNutrients: Complete nutrient data array
        - foodCategory: Food category information
        Returns None if not found
    """
    from .scoring_tool import _score_relevance_advanced
    
    client = get_api_client()
    
    # Priority order: Foundation > SR Legacy > Survey (FNDDS)
    # First, try to get Foundation or SR Legacy foods (most generic)
    foods = client.search_food(query, page_size=50, data_type_filter="Foundation,SR Legacy")
    
    # If no Foundation/SR Legacy found, try Survey foods
    if not foods:
        foods = client.search_food(query, page_size=50, data_type_filter="Survey (FNDDS)")
    
    # If still no results, search all types but filter out branded
    if not foods:
        all_foods = client.search_food(query, page_size=50, data_type_filter=None)
        foods = [f for f in all_foods if f.get("dataType") != "Branded"]
    
    # Score and rank all foods by relevance
    if not foods:
        return None
    
    # Score each food item using advanced relevance scoring
    scored_foods = [
        (food, _score_relevance_advanced(food, query, idx))
        for idx, food in enumerate(foods)
    ]
    
    # Sort by score (highest first) and take the best match
    scored_foods.sort(key=lambda x: x[1], reverse=True)
    best_food, best_score = scored_foods[0]
    
    # Get full details for the best match (includes all nutrients)
    fdc_id = best_food.get("fdcId")
    if fdc_id:
        full_details = client.get_food_details(fdc_id)
        if full_details:
            return full_details
    
    # Fallback: return the search result with nutrients if available
    return best_food

