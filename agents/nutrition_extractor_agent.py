"""
Nutrition Extractor Agent - Data extraction and normalization
"""

from crewai import Agent
from tools.nutrition_extractor_tool import extract_nutrition_data
from tools.tool_wrapper import create_tool


nutrition_extractor_agent = Agent(
    role="Nutrition Data Extraction Specialist",
    goal="Extract and normalize nutrition data from USDA API responses",
    backstory="""You are an expert at extracting and normalizing nutrition data from USDA API responses.
    You understand USDA nutrient data structures and can extract all relevant nutrition information,
    normalizing it to per-100g format for consistency. You handle different nutrient naming conventions
    and extract both detailed nutrient data and common nutrients (calories, protein, fat, carbs, etc.)
    for easy access. Your output is structured and ready for storage or further processing.""",
    tools=[
        create_tool(extract_nutrition_data, description="Extract and normalize nutrition data from USDA API food data")
    ],
    verbose=True,
    allow_delegation=False
)

