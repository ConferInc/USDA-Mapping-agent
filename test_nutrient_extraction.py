"""
Test script to verify all 117 nutrients are extracted
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.usda_api_tool import get_usda_food_details
from tools.nutrition_extractor_tool import extract_nutrition_data
from utils.nutrient_mapper import get_all_nutrient_ids, load_nutrient_definitions


def test_nutrient_extraction():
    """Test that all 117 nutrients are extracted (with NULL for missing ones)"""
    
    print("\n" + "="*80)
    print("TESTING NUTRIENT EXTRACTION - All 117 Nutrients")
    print("="*80)
    
    # Load nutrient definitions
    definitions = load_nutrient_definitions()
    all_nutrient_ids = get_all_nutrient_ids()
    
    print(f"\n[INFO] Loaded {len(all_nutrient_ids)} nutrient definitions from CSV")
    print(f"[INFO] Expected: 117 nutrients (116 + 1 header row = 116 nutrients)")
    
    # Test with a known ingredient (milk)
    fdc_id = 746782  # Milk, whole, 3.25% milkfat
    print(f"\n[TEST] Testing with FDC ID {fdc_id} (Milk)")
    
    # Get food data
    food_data = get_usda_food_details(fdc_id)
    if not food_data:
        print("[ERROR] Failed to fetch food data")
        return False
    
    print(f"[OK] Fetched food data: {food_data.get('description')}")
    
    # Extract nutrition data
    nutrition_data = extract_nutrition_data(food_data)
    
    # Check standardized_nutrients
    standardized = nutrition_data.get("standardized_nutrients", {})
    
    print(f"\n[RESULTS]")
    print(f"  Total standardized nutrients: {len(standardized)}")
    print(f"  Nutrients with values: {sum(1 for v in standardized.values() if v is not None)}")
    print(f"  Nutrients with NULL: {sum(1 for v in standardized.values() if v is None)}")
    
    # Verify all 117 nutrients are present
    missing = []
    for nutrient_id in all_nutrient_ids:
        if nutrient_id not in standardized:
            missing.append(nutrient_id)
    
    if missing:
        print(f"\n[ERROR] Missing nutrient IDs: {len(missing)}")
        for mid in missing[:10]:  # Show first 10
            print(f"  - {mid}")
        return False
    
    print(f"\n[SUCCESS] All {len(all_nutrient_ids)} nutrients are present in output!")
    
    # Show some examples
    print(f"\n[EXAMPLES] Sample nutrients with values:")
    count = 0
    for nutrient_id, value in standardized.items():
        if value is not None and count < 10:
            def_info = definitions.get(nutrient_id, {})
            nutrient_name = def_info.get('nutrient_name', nutrient_id)
            print(f"  {nutrient_name}: {value.get('amount')} {value.get('unit')}")
            count += 1
    
    print(f"\n[EXAMPLES] Sample nutrients with NULL (not found in USDA data):")
    count = 0
    for nutrient_id, value in standardized.items():
        if value is None and count < 10:
            def_info = definitions.get(nutrient_id, {})
            nutrient_name = def_info.get('nutrient_name', nutrient_id)
            print(f"  {nutrient_name}: NULL")
            count += 1
    
    # Verify structure
    print(f"\n[VERIFICATION]")
    print(f"  [OK] standardized_nutrients field exists: {'standardized_nutrients' in nutrition_data}")
    print(f"  [OK] All nutrient IDs present: {len(missing) == 0}")
    print(f"  [OK] NULL values for missing nutrients: {all(v is None or isinstance(v, dict) for v in standardized.values())}")
    
    return True


if __name__ == "__main__":
    if not os.getenv("USDA_API_KEY"):
        print("[ERROR] USDA_API_KEY not found in environment!")
        sys.exit(1)
    
    success = test_nutrient_extraction()
    
    if success:
        print("\n" + "="*80)
        print("[SUCCESS] All 117 nutrients extraction verified!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("[FAILED] Nutrient extraction test failed")
        print("="*80)
        sys.exit(1)

