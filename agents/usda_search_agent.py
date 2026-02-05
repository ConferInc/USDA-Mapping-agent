"""
USDA Search Agent - API interaction and rate limiting
"""

from crewai import Agent
from tools.usda_api_tool import search_usda_food, get_usda_food_details
from tools.tool_wrapper import create_tool


usda_search_agent = Agent(
    role="USDA API Search Specialist",
    goal="Execute searches and retrieve food data from USDA API efficiently with proper rate limiting",
    backstory="""You are an expert at querying the USDA FoodData Central API efficiently. You know the API
    endpoints, parameters, and best practices for efficient searching. You handle rate limiting, retries,
    and error recovery to ensure reliable data retrieval. You understand data types (Foundation, SR Legacy,
    Branded) and can filter results appropriately. Your job is to get the best search results while being
    respectful of API rate limits.""",
    tools=[
        create_tool(search_usda_food, description="Search USDA FoodData Central API for foods matching the query"),
        create_tool(get_usda_food_details, description="Get detailed nutrition information for a specific FDC ID")
    ],
    verbose=True,
    allow_delegation=False
)

