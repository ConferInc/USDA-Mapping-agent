"""
Extraction Task - Extract nutrition data from food details
"""

from crewai import Task
from agents.nutrition_extractor_agent import nutrition_extractor_agent
from agents.usda_search_agent import usda_search_agent


def create_extraction_task(fdc_id: int, ingredient: str) -> Task:
    """
    Create an extraction task for getting detailed nutrition data.
    
    Args:
        fdc_id: FoodData Central ID
        ingredient: Original ingredient name
    
    Returns:
        Task for nutrition data extraction
    """
    return Task(
        description=f"""Extract detailed nutrition data for ingredient '{ingredient}' with FDC ID {fdc_id}.
        
        First, use get_usda_food_details to fetch the complete food data for FDC ID {fdc_id}.
        Then, use extract_nutrition_data to extract and normalize the nutrition information.
        
        The extracted data should include:
        - fdc_id: FoodData Central ID
        - description: Food description
        - data_type: Type of data
        - brand_owner: Brand owner (if applicable)
        - normalized_to: "100g" (all values are per 100g)
        - nutrients: Dictionary of all nutrients with amounts and units
        - common_nutrients: Dictionary with common nutrients (calories, protein, fat, carbs, etc.)
        
        Add the original ingredient name to the result: ingredient: '{ingredient}'
        
        Expected output: Complete nutrition data dictionary with all fields listed above.""",
        agent=nutrition_extractor_agent,
        expected_output="Complete nutrition data dictionary with fdc_id, description, data_type, nutrients, common_nutrients, and ingredient name"
    )


