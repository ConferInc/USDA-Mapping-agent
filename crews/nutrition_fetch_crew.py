"""
Nutrition Fetch Crew - Main crew for fetching nutrition data
"""

from crewai import Crew, Process
from agents import (
    mapping_lookup_agent,
    search_strategy_agent,
    usda_search_agent,
    match_scoring_agent,
    nutrition_extractor_agent
)
from tasks import (
    create_lookup_task,
    create_search_strategy_task,
    create_usda_search_task,
    create_scoring_task,
    create_extraction_task
)


def create_nutrition_fetch_crew(ingredient: str) -> Crew:
    """
    Create a crew for fetching nutrition data for a single ingredient.
    
    Args:
        ingredient: Ingredient name to process
    
    Returns:
        Crew instance configured for this ingredient
    """
    # Create tasks in sequence
    lookup_task = create_lookup_task(ingredient)
    
    # Search strategy task (runs if lookup fails)
    search_strategy_task = create_search_strategy_task(ingredient)
    search_strategy_task.context = [lookup_task]  # Depends on lookup task
    
    # USDA search task (depends on search strategy)
    # Note: We'll need to handle this dynamically based on lookup result
    # For now, create it but it may not be used if lookup succeeds
    
    # Create crew with all agents
    crew = Crew(
        agents=[
            mapping_lookup_agent,
            search_strategy_agent,
            usda_search_agent,
            match_scoring_agent,
            nutrition_extractor_agent
        ],
        tasks=[
            lookup_task,
            search_strategy_task,
        ],
        process=Process.sequential,
        verbose=True
    )
    
    return crew


# For now, we'll use a simpler approach - process ingredients directly
# without full crew orchestration, since task dependencies are complex


