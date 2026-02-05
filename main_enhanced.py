"""
Main entry point for Enhanced USDA Nutrition Fetcher
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator_enhanced import EnhancedNutritionFetchOrchestrator, main as orchestrator_main

if __name__ == "__main__":
    orchestrator_main()


