"""
Scoring Task - Score and rank search results
"""

from crewai import Task
from agents.match_scoring_agent import match_scoring_agent


def create_scoring_task(ingredient: str, search_results: list, search_intent: dict = None) -> Task:
    """
    Create a scoring task for ranking search results.
    
    Args:
        ingredient: Original ingredient name
        search_results: List of search results from USDA API
        search_intent: Optional search intent for better scoring
    
    Returns:
        Task for match scoring
    """
    return Task(
        description=f"""Score and rank the search results for ingredient '{ingredient}'.
        
        Use the filter_search_results tool to:
        1. Score each result using score_match_quality
        2. Filter out poor matches (score >= 50)
        3. Rank results by score (lower is better)
        
        The scoring considers:
        - Whether ingredient is primary subject (first word)
        - Description complexity (simpler = better)
        - Compound food detection
        - Data type preference (Foundation > SR Legacy > Branded)
        - LLM intent guidance (avoid words, preferred forms)
        
        Return the top 10 best matches, sorted by score.
        
        Expected output: List of tuples: ((base_score, type_score, description), food_item)
        Sorted by score (lower is better), filtered to top 10 matches.""",
        agent=match_scoring_agent,
        expected_output="List of top 10 scored and ranked matches, each as ((base_score, type_score, description), food_item) tuple"
    )


