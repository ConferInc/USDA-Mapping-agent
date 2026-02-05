"""
Match Scoring Agent - Quality assessment and ranking
"""

from crewai import Agent
from tools.scoring_tool import score_match_quality, filter_search_results
from tools.tool_wrapper import create_tool


match_scoring_agent = Agent(
    role="Match Quality Assessment Expert",
    goal="Score and rank search results to find the best match for each ingredient",
    backstory="""You are an expert at evaluating the quality and accuracy of ingredient matches. You understand
    USDA food description formats and can identify when a match is accurate versus when it's a different product.
    You use sophisticated scoring algorithms that consider:
    - Whether the ingredient is the primary subject
    - Description complexity (simpler = better)
    - Compound food detection
    - Data type preference (Foundation > SR Legacy > Branded)
    - LLM intent guidance (avoid words, preferred forms)
    
    Your scoring helps ensure we get the most accurate nutrition data for each ingredient.""",
    tools=[
        create_tool(score_match_quality, description="Score a food item match quality for an ingredient"),
        create_tool(filter_search_results, description="Filter and score search results, returning ranked list")
    ],
    verbose=True,
    allow_delegation=False
)

