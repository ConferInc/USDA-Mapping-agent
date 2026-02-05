"""
Test script for enhanced scoring functionality
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.usda_api_tool import search_usda_food, get_ingredient_nutrition_profile_fast
from tools.scoring_tool import score_match_quality, score_match_quality_enhanced, filter_search_results

def test_enhanced_scoring():
    """Test enhanced scoring vs original scoring"""
    
    test_ingredients = [
        "whole milk",
        "apple",
        "bread",
        "cheese crackers"  # Should be penalized as compound food
    ]
    
    print("="*80)
    print("TESTING ENHANCED SCORING")
    print("="*80)
    
    for ingredient in test_ingredients:
        print(f"\n{'='*80}")
        print(f"Testing: {ingredient}")
        print(f"{'='*80}")
        
        # Search USDA API
        print(f"\n[1] Searching USDA API...")
        search_results = search_usda_food(ingredient, page_size=10, data_type="Foundation,SR Legacy")
        
        if not search_results:
            print(f"  No results found for '{ingredient}'")
            continue
        
        print(f"  Found {len(search_results)} results")
        
        # Compare original vs enhanced scoring
        print(f"\n[2] Comparing Original vs Enhanced Scoring:")
        print(f"\n  Top 3 Results Comparison:")
        print(f"  {'-'*76}")
        print(f"  {'Rank':<6} {'Description':<40} {'Original':<12} {'Enhanced':<12}")
        print(f"  {'-'*76}")
        
        # Original scoring
        original_scored = filter_search_results(search_results, ingredient, max_score=200, use_enhanced=False)
        # Enhanced scoring
        enhanced_scored = filter_search_results(search_results, ingredient, max_score=200, use_enhanced=True)
        
        # Show top 3 from each
        for i in range(min(3, len(original_scored), len(enhanced_scored))):
            orig_score, orig_item = original_scored[i]
            enh_score, enh_item = enhanced_scored[i]
            
            orig_desc = orig_item.get("description", "")[:38]
            enh_desc = enh_item.get("description", "")[:38]
            
            orig_base = orig_score[0]
            enh_base = enh_score[0]
            
            print(f"  {i+1:<6} {orig_desc:<40} {orig_base:<12} {enh_base:<12}")
            
            # Show if they differ
            if orig_item.get("fdcId") != enh_item.get("fdcId"):
                print(f"         Enhanced: {enh_desc}")
        
        # Check for compound food detection
        print(f"\n[3] Compound Food Detection Test:")
        if "cheese" in ingredient.lower() or "crackers" in ingredient.lower():
            print(f"  Testing compound food penalty for '{ingredient}'...")
            for idx, result in enumerate(search_results[:5]):
                desc = result.get("description", "").lower()
                if desc.startswith("cheese") or desc.startswith("crackers"):
                    # This should be heavily penalized in enhanced scoring
                    orig_score = score_match_quality(result, ingredient)
                    enh_score = score_match_quality_enhanced(result, ingredient, position=idx)
                    print(f"    '{result.get('description', '')[:50]}'")
                    print(f"      Original score: {orig_score[0]}")
                    print(f"      Enhanced score: {enh_score[0]} (should be higher = worse match)")


def test_fast_path():
    """Test the fast-path nutrition profile function"""
    
    print("\n" + "="*80)
    print("TESTING FAST-PATH FUNCTION")
    print("="*80)
    
    test_ingredients = ["whole milk", "apple"]
    
    for ingredient in test_ingredients:
        print(f"\n{'='*80}")
        print(f"Testing fast-path for: {ingredient}")
        print(f"{'='*80}")
        
        try:
            profile = get_ingredient_nutrition_profile_fast(ingredient)
            
            if profile:
                print(f"\n[OK] Fast-path successful!")
                print(f"  Description: {profile.get('description', 'N/A')}")
                print(f"  FDC ID: {profile.get('fdcId', 'N/A')}")
                print(f"  Data Type: {profile.get('dataType', 'N/A')}")
                
                nutrients = profile.get("foodNutrients", [])
                if nutrients:
                    print(f"  Nutrients: {len(nutrients)} found")
                    # Show first 5 nutrients
                    print(f"  Sample nutrients:")
                    for nut in nutrients[:5]:
                        name = nut.get("nutrientName", "Unknown")
                        value = nut.get("value", "N/A")
                        unit = nut.get("unitName", "")
                        print(f"    - {name}: {value} {unit}")
            else:
                print(f"[WARNING] Fast-path returned None for '{ingredient}'")
        except Exception as e:
            print(f"[ERROR] Fast-path failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    try:
        test_enhanced_scoring()
        test_fast_path()
        print("\n" + "="*80)
        print("TESTING COMPLETE")
        print("="*80)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
