"""
Nutrition Extraction Tools
"""

import os
import sys
from typing import Dict, List, Optional

# Add utils to path for nutrient_mapper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.nutrient_mapper import extract_all_nutrients, load_nutrient_definitions


def extract_nutrition_data(food_data: Dict) -> Dict:
    """
    Extract and normalize nutrition data from USDA API food data.
    
    Args:
        food_data: Full food data from USDA API containing foodNutrients array
    
    Returns:
        Dictionary with extracted nutrition information:
        {
            "fdc_id": int,
            "description": str,
            "data_type": str,
            "brand_owner": str,
            "normalized_to": "100g",
            "nutrients": Dict[str, {"amount": float, "unit": str}],
            "common_nutrients": Dict[str, Optional[Dict]]
        }
    """
    # USDA API returns all values per 100g by default
    nutrition = {
        "fdc_id": food_data.get("fdcId"),
        "description": food_data.get("description", ""),
        "data_type": food_data.get("dataType", ""),
        "brand_owner": food_data.get("brandOwner", ""),
        "normalized_to": "100g",
        "note": "All nutrition values are per 100g (USDA FoodData Central standard)"
    }
    
    # Extract nutrients
    nutrients = {}
    food_nutrients = food_data.get("foodNutrients", [])
    
    if not food_nutrients:
        print(f"    Warning: foodNutrients array is empty or missing")
    
    for nutrient in food_nutrients:
        # Handle different possible structures
        nutrient_info = nutrient.get("nutrient", {})
        if not nutrient_info:
            # Sometimes nutrient data is at top level
            nutrient_info = nutrient
        
        nutrient_name = nutrient_info.get("name", "")
        amount = nutrient.get("amount")
        unit = nutrient_info.get("unitName", "")
        
        # Skip if amount is None, 0, or nutrient name is missing
        # Values are already per 100g from USDA API
        if amount is not None and nutrient_name:
            nutrients[nutrient_name] = {
                "amount": amount,  # Already per 100g
                "unit": unit
            }
    
    nutrition["nutrients"] = nutrients  # Keep raw USDA nutrients for reference
    
    # Extract all 117 standardized nutrients
    nutrient_definitions = load_nutrient_definitions()
    standardized_nutrients = extract_all_nutrients(nutrients, nutrient_definitions)
    nutrition["standardized_nutrients"] = standardized_nutrients
    
    # Extract common nutrients for easy access (backward compatibility)
    common_nutrients = {
        "calories": standardized_nutrients.get("nutrient-calories-energy"),
        "protein": standardized_nutrients.get("nutrient-protein"),
        "fat": standardized_nutrients.get("nutrient-total-fat"),
        "carbs": standardized_nutrients.get("nutrient-total-carbohydrates"),
        "fiber": standardized_nutrients.get("nutrient-dietary-fiber"),
        "sugar": standardized_nutrients.get("nutrient-total-sugars"),
        "sodium": standardized_nutrients.get("nutrient-sodium"),
        "calcium": standardized_nutrients.get("nutrient-calcium"),
        "iron": standardized_nutrients.get("nutrient-iron"),
        "vitamin_c": standardized_nutrients.get("nutrient-vitamin-c-ascorbic-acid"),
    }
    
    nutrition["common_nutrients"] = common_nutrients
    
    return nutrition


def _get_nutrient_value(nutrients: Dict, possible_names: List[str]) -> Optional[Dict]:
    """Get nutrient value by trying multiple possible names."""
    for name in possible_names:
        if name in nutrients:
            return nutrients[name]
    return None

