"""Check nutrient count in CSV"""
import csv
import os

path = "../nutrition_usda/nutrition_definitions_117.csv"
if not os.path.exists(path):
    path = "nutrition_usda/nutrition_definitions_117.csv"

with open(path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    ids = [r.get('id', '').strip() for r in rows if r.get('id', '').strip()]
    print(f"Total rows: {len(rows)}")
    print(f"Rows with ID: {len(ids)}")
    print(f"Unique IDs: {len(set(ids))}")
    if len(ids) != len(set(ids)):
        print("WARNING: Duplicate IDs found!")
        from collections import Counter
        duplicates = [id for id, count in Counter(ids).items() if count > 1]
        print(f"Duplicate IDs: {duplicates}")


