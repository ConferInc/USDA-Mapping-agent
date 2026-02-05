"""
CrewAI Tasks for USDA Nutrition Fetcher
"""

from .lookup_task import create_lookup_task
from .search_task import create_search_strategy_task, create_usda_search_task
from .scoring_task import create_scoring_task
from .extraction_task import create_extraction_task

__all__ = [
    "create_lookup_task",
    "create_search_strategy_task",
    "create_usda_search_task",
    "create_scoring_task",
    "create_extraction_task",
]

