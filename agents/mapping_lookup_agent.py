"""
Mapping Lookup Agent - Fast path for curated mappings
"""

from crewai import Agent
from tools.mapping_tool import load_curated_mappings, search_mappings
from tools.tool_wrapper import create_tool


mapping_lookup_agent = Agent(
    role="Mapping Lookup Specialist",
    goal="Quickly find ingredients in curated mappings database for fast, accurate lookups",
    backstory="""You are an expert at retrieving pre-verified ingredient mappings from curated databases.
    You have access to a comprehensive database of verified ingredient-to-FDC-ID mappings and can find
    exact or near-exact matches instantly. Your job is to provide fast, accurate lookups without needing
    to query external APIs. You use fuzzy matching to handle variations like plural/singular forms and
    common name variations.""",
    tools=[
        create_tool(load_curated_mappings, description="Load curated ingredient mappings from JSON file"),
        create_tool(search_mappings, description="Search for ingredient in curated mappings with fuzzy matching")
    ],
    verbose=True,
    allow_delegation=False
)

