"""
Search Task - Generate search strategy and execute USDA search
"""

from crewai import Task
from agents.search_strategy_agent import search_strategy_agent
from agents.usda_search_agent import usda_search_agent


def create_search_strategy_task(ingredient: str) -> Task:
    """
    Create a search strategy task using LLM.
    
    Args:
        ingredient: Ingredient name to generate search strategy for
    
    Returns:
        Task for search strategy generation
    """
    return Task(
        description=f"""Generate optimal search strategy for the ingredient '{ingredient}'.
        
        First, check the cache using get_cached_search_intent. If cached, return the cached intent.
        If not cached, use generate_search_intent to create a new search intent using LLM.
        
        The search intent should include:
        - search_query: Best search terms for USDA keyword search
        - is_phrase: Whether this is a compound name (multi-word)
        - preferred_form: Standard form (e.g., "whole" for milk, "raw" for produce)
        - avoid: Words indicating wrong matches
        - expected_pattern: Expected USDA description format
        
        After generating, save it to cache using save_search_intent_cache.
        
        Expected output: Search intent dictionary with all 5 fields.""",
        agent=search_strategy_agent,
        expected_output="Search intent dictionary with search_query, is_phrase, preferred_form, avoid, and expected_pattern fields"
    )


def create_usda_search_task(ingredient: str, search_intent: dict) -> Task:
    """
    Create a USDA API search task.
    
    Args:
        ingredient: Original ingredient name
        search_intent: Search intent from search_strategy_agent
    
    Returns:
        Task for USDA API search
    """
    search_query = search_intent.get("search_query", ingredient)
    data_type = "Foundation,SR Legacy"
    
    return Task(
        description=f"""Search USDA FoodData Central API for the ingredient '{ingredient}'.
        
        Use the search_usda_food tool with:
        - query: '{search_query}' (from search intent)
        - page_size: 50 (to get enough results for scoring)
        - data_type: '{data_type}' (prefer Foundation and SR Legacy foods)
        
        Return the list of search results. Each result should contain:
        - fdcId: FoodData Central ID
        - description: Food description
        - dataType: Type of data
        - foodNutrients: Optional nutrient data (if available in search results)
        
        Expected output: List of food items from USDA API search results.""",
        agent=usda_search_agent,
        expected_output="List of food items from USDA API, each with fdcId, description, dataType, and optionally foodNutrients"
    )


