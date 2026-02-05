"""
Test the orchestrator workflow
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import NutritionFetchOrchestrator


def test_single_ingredient():
    """Test processing a single ingredient"""
    print("\n" + "="*80)
    print("TESTING ORCHESTRATOR - Single Ingredient")
    print("="*80)
    
    orchestrator = NutritionFetchOrchestrator()
    
    # Test with an ingredient
    ingredient = "chicken"
    result = orchestrator.fetch_nutrition_for_ingredient(ingredient)
    
    if result:
        print(f"\n[SUCCESS] Retrieved nutrition data for '{ingredient}'")
        print(f"  FDC ID: {result.get('fdc_id')}")
        print(f"  Description: {result.get('description')}")
        print(f"  Source: {result.get('source')}")
        print(f"  Total nutrients: {len(result.get('nutrients', {}))}")
        print(f"  Standardized nutrients: {len(result.get('standardized_nutrients', {}))}")
        print(f"  Nutrients with values: {sum(1 for v in result.get('standardized_nutrients', {}).values() if v is not None)}")
        return True
    else:
        print(f"\n[FAILED] Could not retrieve nutrition data for '{ingredient}'")
        return False


def test_multiple_ingredients():
    """Test processing multiple ingredients"""
    print("\n" + "="*80)
    print("TESTING ORCHESTRATOR - Multiple Ingredients")
    print("="*80)
    
    orchestrator = NutritionFetchOrchestrator()
    
    ingredients = ["milk", "eggs", "bread"]
    results = orchestrator.process_ingredients(
        ingredients,
        output_file="test_nutrition_data.csv",
        format="csv",
        limit=3
    )
    
    print(f"\n[RESULTS]")
    print(f"  Total: {results['total']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"  From mappings: {results['from_mappings']}")
    print(f"  From search: {results['from_search']}")
    
    return results['successful'] > 0


if __name__ == "__main__":
    if not os.getenv("USDA_API_KEY"):
        print("[ERROR] USDA_API_KEY not found!")
        sys.exit(1)
    
    print("\n" + "="*80)
    print("ORCHESTRATOR TEST SUITE")
    print("="*80)
    
    # Test single ingredient
    test1 = test_single_ingredient()
    
    # Test multiple ingredients
    test2 = test_multiple_ingredients()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Single ingredient test: {'[PASS]' if test1 else '[FAIL]'}")
    print(f"Multiple ingredients test: {'[PASS]' if test2 else '[FAIL]'}")
    print("="*80)


