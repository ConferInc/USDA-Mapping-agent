"""Verify CSV output has all nutrients"""
import csv
import os

csv_file = "test_nutrition_data.csv"
if not os.path.exists(csv_file):
    csv_file = "../test_nutrition_data.csv"

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    nutrient_cols = [c for c in cols if c.startswith("nutrient-")]
    
    print(f"Total columns: {len(cols)}")
    print(f"Standardized nutrient columns: {len(nutrient_cols)}")
    print(f"Expected: 116 nutrients")
    print(f"Match: {'YES' if len(nutrient_cols) == 116 else 'NO'}")
    
    # Check a few sample rows
    rows = list(reader)
    if rows:
        print(f"\nSample row - ingredient: {rows[0].get('ingredient')}")
        print(f"Nutrients with values: {sum(1 for c in nutrient_cols if rows[0].get(c) and rows[0].get(c).strip())}")
        print(f"Nutrients with NULL: {sum(1 for c in nutrient_cols if not rows[0].get(c) or not rows[0].get(c).strip())}")


