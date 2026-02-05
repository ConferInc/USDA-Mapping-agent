"""
Test script for CrewAI agents
Tests each agent individually and demonstrates the workflow
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Note: Agents require proper tool wrapping which we'll handle in Phase 3
# For now, we test the tools directly
from tools.mapping_tool import search_mappings
from tools.usda_api_tool import search_usda_food, get_usda_food_details
from tools.llm_tool import generate_search_intent
from tools.scoring_tool import filter_search_results
from tools.nutrition_extractor_tool import extract_nutrition_data


def test_mapping_lookup():
    """Test MappingLookupAgent"""
    print("\n" + "="*80)
    print("TEST 1: Mapping Lookup Agent")
    print("="*80)
    
    ingredient = "milk"
    print(f"\nTesting lookup for: '{ingredient}'")
    
    # Test the tool directly
    mapping = search_mappings(ingredient)
    
    if mapping:
        print(f"[OK] Found in mappings!")
        print(f"  FDC ID: {mapping.get('fdc_id')}")
        print(f"  Description: {mapping.get('description')}")
        print(f"  Data Type: {mapping.get('data_type')}")
        print(f"  Verified: {mapping.get('verified')}")
        return mapping
    else:
        print(f"[NOT FOUND] Not found in mappings")
        return None


def test_search_strategy():
    """Test SearchStrategyAgent"""
    print("\n" + "="*80)
    print("TEST 2: Search Strategy Agent")
    print("="*80)
    
    ingredient = "black pepper"
    print(f"\nTesting search strategy for: '{ingredient}'")
    
    # Test the tool directly
    intent = generate_search_intent(ingredient)
    
    if intent:
        print(f"[OK] Generated search intent!")
        print(f"  Search Query: {intent.get('search_query')}")
        print(f"  Is Phrase: {intent.get('is_phrase')}")
        print(f"  Preferred Form: {intent.get('preferred_form')}")
        print(f"  Avoid Words: {intent.get('avoid')}")
        print(f"  Expected Pattern: {intent.get('expected_pattern')}")
        return intent
    else:
        print(f"[WARNING] Failed to generate search intent (LLM may not be configured)")
        # Return a fallback
        return {
            "search_query": ingredient,
            "is_phrase": " " in ingredient,
            "preferred_form": "",
            "avoid": [],
            "expected_pattern": ""
        }


def test_usda_search():
    """Test USDASearchAgent"""
    print("\n" + "="*80)
    print("TEST 3: USDA Search Agent")
    print("="*80)
    
    query = "milk"
    print(f"\nTesting USDA search for: '{query}'")
    
    # Test the tool directly
    results = search_usda_food(query, page_size=10)
    
    if results:
        print(f"[OK] Found {len(results)} results!")
        print(f"\nTop 3 results:")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result.get('description')} (FDC ID: {result.get('fdcId')})")
        return results
    else:
        print(f"[ERROR] No results found")
        return []


def test_scoring():
    """Test MatchScoringAgent"""
    print("\n" + "="*80)
    print("TEST 4: Match Scoring Agent")
    print("="*80)
    
    ingredient = "milk"
    print(f"\nTesting scoring for: '{ingredient}'")
    
    # Get some search results first
    search_results = search_usda_food(ingredient, page_size=20)
    
    if not search_results:
        print("[ERROR] No search results to score")
        return []
    
    print(f"Scoring {len(search_results)} results...")
    
    # Test the scoring tool
    scored_results = filter_search_results(search_results, ingredient, max_score=50)
    
    if scored_results:
        print(f"[OK] Scored and filtered to {len(scored_results)} good matches!")
        print(f"\nTop 3 scored matches:")
        for i, ((base_score, type_score, desc), food_item) in enumerate(scored_results[:3], 1):
            print(f"  {i}. Score: {base_score} | {desc}")
            print(f"     FDC ID: {food_item.get('fdcId')}")
        return scored_results
    else:
        print(f"[WARNING] No good matches found (all scores >= 50)")
        return []


def test_extraction():
    """Test NutritionExtractorAgent"""
    print("\n" + "="*80)
    print("TEST 5: Nutrition Extractor Agent")
    print("="*80)
    
    # Use a known FDC ID (milk)
    fdc_id = 746782  # Milk, whole, 3.25% milkfat
    print(f"\nTesting extraction for FDC ID: {fdc_id}")
    
    # Get food details
    food_data = get_usda_food_details(fdc_id)
    
    if not food_data:
        print("[ERROR] Failed to fetch food details")
        return None
    
    print(f"[OK] Fetched food data: {food_data.get('description')}")
    
    # Extract nutrition data
    nutrition_data = extract_nutrition_data(food_data)
    
    if nutrition_data:
        print(f"[OK] Extracted nutrition data!")
        print(f"  FDC ID: {nutrition_data.get('fdc_id')}")
        print(f"  Description: {nutrition_data.get('description')}")
        print(f"  Data Type: {nutrition_data.get('data_type')}")
        print(f"  Total Nutrients: {len(nutrition_data.get('nutrients', {}))}")
        
        # Show common nutrients
        common = nutrition_data.get('common_nutrients', {})
        print(f"\n  Common Nutrients:")
        for key, value in common.items():
            if value:
                print(f"    {key}: {value.get('amount')} {value.get('unit')}")
        
        return nutrition_data
    else:
        print(f"[ERROR] Failed to extract nutrition data")
        return None


def test_full_workflow():
    """Test the full workflow for a single ingredient"""
    print("\n" + "="*80)
    print("TEST 6: Full Workflow (End-to-End)")
    print("="*80)
    
    ingredient = "eggs"
    print(f"\nTesting full workflow for: '{ingredient}'")
    
    # Step 1: Check mappings
    print(f"\n[Step 1] Checking curated mappings...")
    mapping = search_mappings(ingredient)
    
    if mapping:
        print(f"[OK] Found in mappings! FDC ID: {mapping.get('fdc_id')}")
        fdc_id = mapping.get('fdc_id')
        
        # Step 5: Extract nutrition data
        print(f"\n[Step 5] Extracting nutrition data...")
        food_data = get_usda_food_details(fdc_id)
        if food_data:
            nutrition_data = extract_nutrition_data(food_data)
            if nutrition_data:
                nutrition_data["ingredient"] = ingredient
                nutrition_data["source"] = "curated_mapping"
                print(f"[SUCCESS] Extracted nutrition data for '{ingredient}'")
                return nutrition_data
    
    # Step 2: Generate search strategy
    print(f"\n[Step 2] Generating search strategy...")
    intent = generate_search_intent(ingredient)
    if not intent:
        intent = {
            "search_query": ingredient,
            "is_phrase": " " in ingredient,
            "preferred_form": "",
            "avoid": [],
            "expected_pattern": ""
        }
    
    # Step 3: Search USDA API
    print(f"\n[Step 3] Searching USDA API...")
    search_results = search_usda_food(intent.get('search_query', ingredient), page_size=30)
    
    if not search_results:
        print(f"[ERROR] No search results found")
        return None
    
    print(f"[OK] Found {len(search_results)} search results")
    
    # Step 4: Score and rank
    print(f"\n[Step 4] Scoring and ranking results...")
    scored_results = filter_search_results(search_results, ingredient, max_score=50)
    
    if not scored_results:
        print(f"[WARNING] No good matches found")
        return None
    
    best_match = scored_results[0][1]  # Get the food item from the best match
    fdc_id = best_match.get('fdcId')
    print(f"[OK] Best match: {best_match.get('description')} (FDC ID: {fdc_id})")
    
    # Step 5: Extract nutrition data
    print(f"\n[Step 5] Extracting nutrition data...")
    food_data = get_usda_food_details(fdc_id)
    if food_data:
        nutrition_data = extract_nutrition_data(food_data)
        if nutrition_data:
            nutrition_data["ingredient"] = ingredient
            nutrition_data["source"] = "search"
            print(f"[SUCCESS] Extracted nutrition data for '{ingredient}'")
            return nutrition_data
    
    print(f"[ERROR] Failed to extract nutrition data")
    return None


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CREWAI AGENTS TEST SUITE")
    print("="*80)
    print("\nThis script tests each agent and tool individually.")
    print("Note: Some tests require API keys in .env file")
    print("="*80)
    
    # Check for API key
    if not os.getenv("USDA_API_KEY"):
        print("\n⚠️  WARNING: USDA_API_KEY not found in environment!")
        print("   Some tests will fail. Please add it to .env file.")
        return
    
    try:
        # Test individual agents/tools
        test_mapping_lookup()
        test_search_strategy()
        test_usda_search()
        test_scoring()
        test_extraction()
        
        # Test full workflow
        result = test_full_workflow()
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print("[OK] All individual agent tests completed")
        if result:
            print("[SUCCESS] Full workflow test completed successfully!")
        else:
            print("[WARNING] Full workflow test had issues (check API keys and network)")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

