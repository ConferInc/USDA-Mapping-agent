"""
Main entry point for USDA Nutrition Fetcher - CrewAI Version
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import NutritionFetchOrchestrator, main as orchestrator_main

if __name__ == "__main__":
    orchestrator_main()


