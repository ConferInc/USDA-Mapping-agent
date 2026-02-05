"""
Search Strategy Agent - LLM-powered semantic search intent generation
"""

from crewai import Agent
from tools.llm_tool import generate_search_intent
from tools.cache_tool import get_cached_search_intent, save_search_intent_cache
from tools.tool_wrapper import create_tool


search_strategy_agent = Agent(
    role="Search Strategy Expert",
    goal="Generate optimal search strategies for USDA API queries using semantic understanding",
    backstory="""You are a nutrition database expert specializing in semantic understanding of ingredient names.
    You understand how ingredient names map to USDA FoodData Central database formats. You generate search
    queries that maximize match accuracy by understanding ingredient semantics, preferred forms, and avoiding
    incorrect matches. You use LLM-powered analysis to understand ingredient context and generate the best
    search terms. You also cache your results to avoid redundant LLM calls.""",
    tools=[
        create_tool(generate_search_intent, description="Generate search intent for an ingredient using LLM"),
        create_tool(get_cached_search_intent, description="Get cached search intent for an ingredient"),
        create_tool(save_search_intent_cache, description="Save search intent to cache")
    ],
    verbose=True,
    allow_delegation=False
)

