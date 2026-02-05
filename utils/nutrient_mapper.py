"""
Nutrient Mapper - Maps USDA nutrient names to standardized nutrient IDs
"""

import csv
import os
from typing import Dict, List, Optional
from pathlib import Path


# USDA nutrient name mappings to standardized IDs
# This maps USDA API nutrient names to the nutrient IDs from nutrition_definitions_117.csv
USDA_NUTRIENT_MAPPINGS = {
    # Core Energy & Macros
    "Energy": "nutrient-calories-energy",
    "Energy (Atwater General Factors)": "nutrient-calories-energy",
    "Energy (Atwater Specific Factors)": "nutrient-calories-energy",
    "Protein": "nutrient-protein",
    "Total lipid (fat)": "nutrient-total-fat",
    "Carbohydrate, by difference": "nutrient-total-carbohydrates",
    "Fiber, total dietary": "nutrient-dietary-fiber",
    "Sugars, total including NLEA": "nutrient-total-sugars",
    "Sugars, added": "nutrient-total-sugars",
    "Water": "nutrient-water",
    
    # Fat Breakdown
    "Fatty acids, total saturated": "nutrient-saturated-fat",
    "Fatty acids, total trans": "nutrient-trans-fat",
    "Fatty acids, total monounsaturated": "nutrient-monounsaturated-fat",
    "Fatty acids, total polyunsaturated": "nutrient-polyunsaturated-fat",
    "Cholesterol": "nutrient-cholesterol",
    
    # Other Components
    "Alcohol, ethyl": "nutrient-alcohol",
    "Caffeine": "nutrient-caffeine",
    "Theobromine": "nutrient-theobromine",
    "Ash": "nutrient-ash",
    
    # Vitamins - Fat-Soluble
    "Vitamin A, RAE": "nutrient-vitamin-a-rae",
    "Retinol": "nutrient-retinol",
    "Vitamin D (D2 + D3)": "nutrient-vitamin-d",
    "Vitamin E (alpha-tocopherol)": "nutrient-vitamin-e-alpha-tocopherol",
    "Vitamin K (phylloquinone)": "nutrient-vitamin-k-phylloquinone",
    
    # Vitamins - B-Complex
    "Thiamin": "nutrient-thiamin-b1",
    "Riboflavin": "nutrient-riboflavin-b2",
    "Niacin": "nutrient-niacin-b3",
    "Pantothenic acid": "nutrient-vitamin-b5-pantothenic-acid",
    "Vitamin B-6": "nutrient-vitamin-b6",
    "Folate, total": "nutrient-folate-folic-acid",
    "Folic acid": "nutrient-folate-folic-acid",
    "Vitamin B-12": "nutrient-vitamin-b12",
    "Choline, total": "nutrient-choline",
    
    # Vitamins - Vitamin C
    "Vitamin C, total ascorbic acid": "nutrient-vitamin-c-ascorbic-acid",
    
    # Minerals - Major
    "Calcium, Ca": "nutrient-calcium",
    "Magnesium, Mg": "nutrient-magnesium",
    "Phosphorus, P": "nutrient-phosphorus",
    "Potassium, K": "nutrient-potassium",
    "Sodium, Na": "nutrient-sodium",
    
    # Minerals - Trace
    "Iron, Fe": "nutrient-iron",
    "Zinc, Zn": "nutrient-zinc",
    "Copper, Cu": "nutrient-copper",
    "Selenium, Se": "nutrient-selenium",
    "Manganese, Mn": "nutrient-manganese",
    "Fluoride, F": "nutrient-fluoride",
    
    # Carotenoids
    "Beta-carotene": "nutrient-beta-carotene",
    "Alpha-carotene": "nutrient-alpha-carotene",
    "Cryptoxanthin, beta": "nutrient-cryptoxanthin",
    "Lycopene": "nutrient-lycopene",
    "Lutein + zeaxanthin": "nutrient-lutein-zeaxanthin",
    
    # Fatty Acids - Saturated
    "4:0": "nutrient-sfa-4-0-butyric",
    "6:0": "nutrient-sfa-6-0-caproic",
    "8:0": "nutrient-sfa-8-0-caprylic",
    "10:0": "nutrient-sfa-10-0-capric",
    "12:0": "nutrient-sfa-12-0-lauric",
    "14:0": "nutrient-sfa-14-0-myristic",
    "16:0": "nutrient-sfa-16-0-palmitic",
    "18:0": "nutrient-sfa-18-0-stearic",
    
    # Fatty Acids - Monounsaturated
    "16:1": "nutrient-mufa-16-1-palmitoleic",
    "18:1": "nutrient-mufa-18-1-oleic",
    "20:1": "nutrient-mufa-20-1",
    "22:1": "nutrient-mufa-22-1",
    
    # Fatty Acids - Polyunsaturated
    "18:2 n-6 c,c": "nutrient-pufa-18-2-linoleic",
    "18:3 n-3 c,c,c (ALA)": "nutrient-pufa-18-3-alpha-linolenic",
    "18:4": "nutrient-pufa-18-4",
    "20:4 n-6": "nutrient-pufa-20-4-arachidonic",
    "20:5 n-3 (EPA)": "nutrient-pufa-20-5-epa",
    "22:5 n-3 (DPA)": "nutrient-pufa-22-5-dpa",
    "22:6 n-3 (DHA)": "nutrient-pufa-22-6-dha",
    
    # Amino Acids - Essential
    "Tryptophan": "nutrient-tryptophan",
    "Threonine": "nutrient-threonine",
    "Isoleucine": "nutrient-isoleucine",
    "Leucine": "nutrient-leucine",
    "Lysine": "nutrient-lysine",
    "Methionine": "nutrient-methionine",
    "Phenylalanine": "nutrient-phenylalanine",
    "Valine": "nutrient-valine",
    
    # Amino Acids - Conditionally Essential
    "Arginine": "nutrient-arginine",
    "Histidine": "nutrient-histidine",
    "Cystine": "nutrient-cystine",
    "Tyrosine": "nutrient-tyrosine",
    
    # Amino Acids - Non-Essential
    "Alanine": "nutrient-alanine",
    "Aspartic acid": "nutrient-aspartic-acid",
    "Glutamic acid": "nutrient-glutamic-acid",
    "Glycine": "nutrient-glycine",
    "Proline": "nutrient-proline",
    "Serine": "nutrient-serine",
}


def load_nutrient_definitions() -> Dict[str, Dict]:
    """
    Load nutrient definitions from CSV file.
    
    Returns:
        Dictionary mapping nutrient_id to nutrient definition
    """
    # Try multiple possible paths
    possible_paths = [
        "../nutrition_usda/nutrition_definitions_117.csv",
        "nutrition_definitions_117.csv",
        os.path.join(os.path.dirname(__file__), "..", "..", "nutrition_usda", "nutrition_definitions_117.csv")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            definitions = {}
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    nutrient_id = row.get('id', '').strip()
                    if nutrient_id:
                        definitions[nutrient_id] = {
                            'id': nutrient_id,
                            'nutrient_name': row.get('nutrient_name', ''),
                            'category': row.get('category', ''),
                            'subcategory': row.get('subcategory', ''),
                            'unit_name': row.get('unit_name', ''),
                            'unit_abbreviation': row.get('unit_abbreviation', ''),
                        }
            return definitions
    
    return {}


def get_all_nutrient_ids() -> List[str]:
    """
    Get list of all 117 nutrient IDs from definitions.
    
    Returns:
        List of nutrient IDs in order
    """
    definitions = load_nutrient_definitions()
    # Sort by the order they appear in CSV (or by ID)
    return sorted(definitions.keys())


def map_usda_nutrient_to_standard(usda_nutrient_name: str) -> Optional[str]:
    """
    Map USDA nutrient name to standardized nutrient ID.
    
    Args:
        usda_nutrient_name: Nutrient name from USDA API
    
    Returns:
        Standardized nutrient ID or None if not found
    """
    # Direct mapping
    if usda_nutrient_name in USDA_NUTRIENT_MAPPINGS:
        return USDA_NUTRIENT_MAPPINGS[usda_nutrient_name]
    
    # Try case-insensitive match
    usda_lower = usda_nutrient_name.lower()
    for usda_name, nutrient_id in USDA_NUTRIENT_MAPPINGS.items():
        if usda_name.lower() == usda_lower:
            return nutrient_id
    
    # Try partial matching for some nutrients
    # (This is a fallback - may need refinement based on actual USDA data)
    if "energy" in usda_lower or "calorie" in usda_lower:
        return "nutrient-calories-energy"
    if "protein" in usda_lower:
        return "nutrient-protein"
    if "fat" in usda_lower and "total" in usda_lower:
        return "nutrient-total-fat"
    if "carbohydrate" in usda_lower:
        return "nutrient-total-carbohydrates"
    if "fiber" in usda_lower or "fibre" in usda_lower:
        return "nutrient-dietary-fiber"
    if "sugar" in usda_lower:
        return "nutrient-total-sugars"
    if "sodium" in usda_lower:
        return "nutrient-sodium"
    if "calcium" in usda_lower:
        return "nutrient-calcium"
    if "iron" in usda_lower:
        return "nutrient-iron"
    if "vitamin c" in usda_lower or "ascorbic" in usda_lower:
        return "nutrient-vitamin-c-ascorbic-acid"
    
    return None


def extract_all_nutrients(usda_nutrients: Dict[str, Dict], nutrient_definitions: Dict[str, Dict] = None) -> Dict[str, Optional[Dict]]:
    """
    Extract all 117 nutrients from USDA nutrients, mapping to standardized IDs.
    Missing nutrients will be set to None.
    
    Args:
        usda_nutrients: Dictionary of USDA nutrients {name: {amount, unit}}
        nutrient_definitions: Optional nutrient definitions (will load if not provided)
    
    Returns:
        Dictionary mapping standardized nutrient_id to {amount, unit} or None
    """
    if nutrient_definitions is None:
        nutrient_definitions = load_nutrient_definitions()
    
    # Get all nutrient IDs
    all_nutrient_ids = get_all_nutrient_ids()
    
    # Initialize result with all nutrients set to None
    result = {nutrient_id: None for nutrient_id in all_nutrient_ids}
    
    # Map USDA nutrients to standardized IDs
    for usda_name, nutrient_data in usda_nutrients.items():
        nutrient_id = map_usda_nutrient_to_standard(usda_name)
        if nutrient_id and nutrient_id in result:
            result[nutrient_id] = nutrient_data
    
    return result


