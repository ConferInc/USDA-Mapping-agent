"""
Lookup Task - Check curated mappings
"""

from crewai import Task
from agents.mapping_lookup_agent import mapping_lookup_agent


def create_lookup_task(ingredient: str) -> Task:
    """
    Create a lookup task for checking curated mappings.
    
    Args:
        ingredient: Ingredient name to look up
    
    Returns:
        Task for mapping lookup
    """
    return Task(
        description=f"""Check if the ingredient '{ingredient}' exists in curated mappings.
        
        Use the search_mappings tool to find the ingredient. The tool will:
        1. Try exact match (case-insensitive)
        2. Try plural/singular variations
        3. Try common name variations
        
        If found, return the mapping data including:
        - fdc_id: The FoodData Central ID
        - description: The food description
        - data_type: Type of data (Foundation, SR Legacy, etc.)
        - verified: Whether this mapping has been verified
        
        If not found, return None.
        
        Expected output format:
        - If found: {{"fdc_id": 123456, "description": "...", "data_type": "...", "verified": true}}
        - If not found: None""",
        agent=mapping_lookup_agent,
        expected_output="Mapping data dictionary with fdc_id, description, data_type, verified fields, or None if not found"
    )


