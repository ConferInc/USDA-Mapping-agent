import requests
import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def search_foods(query: str, api_key: Optional[str] = None, data_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Search foods in the USDA FoodData Central API.
    
    Args:
        query: Search query string (e.g., "milk")
        api_key: USDA API key (optional, will use USDA_API_KEY from .env if not provided)
        data_type: Filter by data type (e.g., "Foundation,SR Legacy" for generic foods, excludes branded)
    
    Returns:
        Dictionary containing the API response with food data
    
    Raises:
        requests.RequestException: If the API request fails
    """
    base_url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    
    # Build query parameters
    params = {
        "query": query
    }
    
    # Add data type filter if provided
    if data_type:
        params["dataType"] = data_type
    
    # Get API key from parameter or environment variable
    if api_key:
        params["api_key"] = api_key
    elif os.getenv("USDA_API_KEY"):
        params["api_key"] = os.getenv("USDA_API_KEY")
    
    # Set headers
    headers = {
        "accept": "application/json"
    }
    
    # Make the API request
    response = requests.get(base_url, params=params, headers=headers)
    response.raise_for_status()  # Raise an exception for bad status codes
    
    return response.json()


def extract_ingredient_info(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract essential ingredient information from USDA API response.
    
    Args:
        api_response: The JSON response from search_foods() function
    
    Returns:
        List of dictionaries containing essential ingredient information
    """
    extracted_data = []
    foods = api_response.get("foods", [])
    
    for food in foods:
        # Extract basic food information
        ingredient_info = {
            "fdcId": food.get("fdcId"),
            "description": food.get("description"),
            "brandName": food.get("brandName"),
            "brandOwner": food.get("brandOwner"),
            "ingredients": food.get("ingredients"),
            "dataType": food.get("dataType"),
            "foodCategory": food.get("foodCategory"),
            "publishedDate": food.get("publishedDate"),
            "gtinUpc": food.get("gtinUpc"),
            "servingSize": food.get("servingSize"),
            "servingSizeUnit": food.get("servingSizeUnit"),
            "householdServingFullText": food.get("householdServingFullText"),
            "nutrients": []
        }
        
        # Extract nutrient information
        food_nutrients = food.get("foodNutrients", [])
        for nutrient in food_nutrients:
            nutrient_info = {
                "nutrientId": nutrient.get("nutrientId"),
                "nutrientName": nutrient.get("nutrientName"),
                "nutrientNumber": nutrient.get("nutrientNumber"),
                "value": nutrient.get("value"),
                "unitName": nutrient.get("unitName"),
                "percentDailyValue": nutrient.get("percentDailyValue"),
                "rank": nutrient.get("rank")
            }
            ingredient_info["nutrients"].append(nutrient_info)
        
        extracted_data.append(ingredient_info)
    
    return extracted_data


def get_ingredient_info(query: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search for foods and extract essential ingredient information.
    
    Args:
        query: Search query string (e.g., "milk")
        api_key: USDA API key (optional, will use USDA_API_KEY from .env if not provided)
    
    Returns:
        List of dictionaries containing essential ingredient information
    """
    api_response = search_foods(query, api_key)
    return extract_ingredient_info(api_response)


def _score_relevance(food: Dict[str, Any], query: str, position: int) -> float:
    """
    Score how relevant a food item is to the search query.
    Higher scores indicate better matches.
    
    Args:
        food: Food item from USDA API
        query: Original search query
        position: Position in the API results (0 = first, most relevant)
    
    Returns:
        Relevance score (higher is better)
    """
    description = food.get("description", "").lower()
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    score = 1000.0  # Base score
    
    # Position penalty (API orders by relevance, so earlier is better)
    score -= position * 10
    
    # Exact match bonus (huge boost)
    if description == query_lower:
        score += 500
    # Starts with query (very good match)
    elif description.startswith(query_lower):
        score += 300
    # Starts with main ingredient word (good match for "Milk, whole" when query is "whole milk")
    # For multi-word queries, the last word is often the main ingredient
    query_word_list = query_lower.split()
    main_ingredient = query_word_list[-1] if query_word_list else ""
    if main_ingredient and description.startswith(main_ingredient):
        score += 250
        # If it also contains the full query phrase, give additional bonus
        if query_lower in description:
            score += 100
    # Exact phrase match (only if didn't already match above)
    elif query_lower in description:
        score += 200
    
    # Word-level matching
    desc_words = set(description.replace(",", " ").split())
    matching_words = query_words.intersection(desc_words)
    if matching_words:
        # All query words present (excellent)
        if matching_words == query_words:
            score += 150
        else:
            # Partial word match
            score += len(matching_words) * 30
    
    # Penalize compound foods when searching for base ingredients
    # If query is simple (1-2 words) but description is complex (3+ words), penalize
    query_word_count = len(query_words)
    desc_words_list = description.replace(",", " ").split()
    desc_word_count = len(desc_words_list)
    
    # Common compound food indicators to penalize (especially when they start the description)
    compound_indicators = ["cheese", "crackers", "bread", "cookies", "cake", 
                          "soup", "sauce", "dressing", "cereal", "bar", "drink",
                          "juice", "spread", "butter", "yogurt"]
    
    # Processed/preserved forms to penalize when searching for fresh/liquid
    processed_forms = ["dry", "powdered", "powder", "dehydrated", "canned", "frozen", 
                       "concentrated", "evaporated", "condensed"]
    
    if query_word_count <= 2:  # Simple query (e.g., "whole milk", "apple")
        # Strongly penalize if description STARTS with compound indicators
        # This indicates a processed food MADE WITH the ingredient, not the ingredient itself
        first_word = desc_words_list[0] if desc_words_list else ""
        if first_word in compound_indicators:
            score -= 800  # Heavy penalty for starting with compound food
        
        # Also penalize if compound indicator appears anywhere
        elif any(indicator in description for indicator in compound_indicators):
            score -= 500  # Increased penalty
        
        # Penalize processed/preserved forms when searching for fresh/liquid (unless query specifies it)
        # For "whole milk", prefer liquid over "dry milk" or "powdered milk"
        if not any(form in query_lower for form in processed_forms):
            if any(form in description for form in processed_forms):
                score -= 300  # Penalize processed forms when searching for fresh
        
        # Penalize if description is much longer than query (likely a compound food)
        if desc_word_count > query_word_count + 1:
            score -= 150  # Increased penalty
    
    # Data type priority (Foundation > SR Legacy > Survey > others)
    data_type = food.get("dataType", "")
    if data_type == "Foundation":
        score += 100
    elif data_type == "SR Legacy":
        score += 50
    elif data_type == "Survey (FNDDS)":
        score += 25
    
    # Food category relevance (e.g., searching "milk" should prefer "Dairy" category)
    food_category_obj = food.get("foodCategory", {})
    if isinstance(food_category_obj, dict):
        food_category = food_category_obj.get("description", "").lower()
    elif isinstance(food_category_obj, str):
        food_category = food_category_obj.lower()
    else:
        food_category = ""
    
    if "milk" in query_lower and "dairy" in food_category:
        score += 50
    if "fruit" in query_lower and "fruit" in food_category:
        score += 50
    
    return score


def get_ingredient_nutrition_profile(query: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get generic nutrition profile for an ingredient (excludes branded products).
    Uses intelligent relevance scoring to find the best match.
    Prioritizes Foundation, SR Legacy, or Survey data types for generic nutrition information.
    
    Note: Nutritional values are standardized per 100 grams for Foundation, SR Legacy, and Survey data types.
    This is the standard USDA reference serving size for generic foods.
    
    Args:
        query: Search query string (e.g., "whole milk", "apple")
        api_key: USDA API key (optional, will use USDA_API_KEY from .env if not provided)
    
    Returns:
        Dictionary containing generic ingredient nutrition profile with:
        - Nutritional values per 100g (standard serving size)
        - All nutrients with values, units, and daily values
        - Ingredient description and metadata
        Returns None if not found
    """
    # Priority order: Foundation > SR Legacy > Survey (FNDDS)
    # These are generic, non-branded foods
    priority_types = [
        "Foundation",
        "SR Legacy", 
        "Survey (FNDDS)"
    ]
    
    # First, try to get Foundation or SR Legacy foods (most generic)
    api_response = search_foods(query, api_key, data_type="Foundation,SR Legacy")
    foods = api_response.get("foods", [])
    
    # If no Foundation/SR Legacy found, try Survey foods
    if not foods:
        api_response = search_foods(query, api_key, data_type="Survey (FNDDS)")
        foods = api_response.get("foods", [])
    
    # If still no results, search all types but filter out branded
    if not foods:
        api_response = search_foods(query, api_key)
        foods = [f for f in api_response.get("foods", []) if f.get("dataType") != "Branded"]
    
    # Score and rank all foods by relevance
    if not foods:
        return None
    
    # Score each food item
    scored_foods = [
        (food, _score_relevance(food, query, idx))
        for idx, food in enumerate(foods)
    ]
    
    # Sort by score (highest first) and take the best match
    scored_foods.sort(key=lambda x: x[1], reverse=True)
    food, best_score = scored_foods[0]
    
    # Extract nutrition profile
    # Note: Foundation, SR Legacy, and Survey data types use standard 100g serving size
    nutrition_profile = {
        "ingredientName": food.get("description"),
        "description": food.get("description"),
        "fdcId": food.get("fdcId"),
        "dataType": food.get("dataType"),
        "foodCategory": food.get("foodCategory"),
        "commonNames": food.get("commonNames"),
        "additionalDescriptions": food.get("additionalDescriptions"),
        "servingSize": 100,  # Standard serving size for Foundation/SR Legacy/Survey data
        "servingSizeUnit": "g",  # Grams - standard unit for USDA reference data
        "nutrients": []
    }
    
    # Extract all nutrients
    food_nutrients = food.get("foodNutrients", [])
    for nutrient in food_nutrients:
        nutrient_value = nutrient.get("value")
        # Skip nutrients with None or missing values
        if nutrient_value is not None:
            nutrient_info = {
                "nutrientId": nutrient.get("nutrientId"),
                "nutrientName": nutrient.get("nutrientName"),
                "nutrientNumber": nutrient.get("nutrientNumber"),
                "value": nutrient_value,
                "unitName": nutrient.get("unitName"),
                "percentDailyValue": nutrient.get("percentDailyValue"),
                "rank": nutrient.get("rank")
            }
            nutrition_profile["nutrients"].append(nutrient_info)
    
    # Sort nutrients by rank (most important first)
    nutrition_profile["nutrients"].sort(key=lambda x: x.get("rank", 9999))
    
    return nutrition_profile


if __name__ == "__main__":
    # Get query from user input
    query = input("Enter an ingredient name (e.g., 'whole milk', 'apple', 'bread'): ").strip()
    
    if not query:
        print("Error: Query cannot be empty!")
        exit(1)
    
    print(f"\nFetching generic nutrition profile for '{query}'...\n")
    
    try:
        nutrition_profile = get_ingredient_nutrition_profile(query)
        
        if not nutrition_profile:
            print(f"Sorry, no generic nutrition data found for '{query}'.")
            print("Try searching with a different name or check if the ingredient exists in the USDA database.")
            exit(1)
        
        print("="*80)
        print("GENERIC NUTRITION PROFILE")
        print("="*80)
        print(f"\nIngredient: {nutrition_profile.get('ingredientName')}")
        print(f"Description: {nutrition_profile.get('description')}")
        if nutrition_profile.get('commonNames'):
            print(f"Common Names: {nutrition_profile.get('commonNames')}")
        if nutrition_profile.get('additionalDescriptions'):
            print(f"Additional Info: {nutrition_profile.get('additionalDescriptions')}")
        print(f"FDC ID: {nutrition_profile.get('fdcId')}")
        print(f"Data Type: {nutrition_profile.get('dataType')}")
        print(f"Food Category: {nutrition_profile.get('foodCategory', 'N/A')}")
        print(f"\nServing Size: {nutrition_profile.get('servingSize')} {nutrition_profile.get('servingSizeUnit', 'g')}")
        print(f"Total Nutrients: {len(nutrition_profile.get('nutrients', []))}")
        
        print("\n" + "-"*80)
        print(f"NUTRITION INFORMATION (per {nutrition_profile.get('servingSize', 100)}{nutrition_profile.get('servingSizeUnit', 'g')})")
        print("-"*80)
        
        # Display all nutrients
        nutrients = nutrition_profile.get('nutrients', [])
        for nutrient in nutrients:
            value = nutrient.get('value')
            unit = nutrient.get('unitName', '')
            name = nutrient.get('nutrientName')
            daily_value = nutrient.get('percentDailyValue')
            
            display = f"  • {name}: {value} {unit}"
            if daily_value is not None:
                display += f" ({daily_value}% DV)"
            print(display)
        
        print("\n" + "="*80)
        
        # Automatically save to JSON file
        filename = f"{query.replace(' ', '_').lower()}_nutrition_profile.json"
        with open(filename, 'w') as f:
            json.dump(nutrition_profile, f, indent=2)
        print(f"\n✅ Nutrition profile automatically saved to: {filename}")
        
        # Option to display as JSON
        show_json = input("\nDisplay full JSON output? (y/n): ").strip().lower()
        if show_json == 'y':
            print("\n" + "="*80)
            print("FULL JSON OUTPUT:")
            print("="*80)
            print(json.dumps(nutrition_profile, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

