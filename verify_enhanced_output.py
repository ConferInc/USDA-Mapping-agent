"""Verify enhanced output CSV"""
import csv
import os

import glob
csv_files = glob.glob("test_enhanced_results_*.csv")
csv_file = csv_files[-1] if csv_files else "test_enhanced_results_20260109_002656.csv"
print(f"Checking file: {csv_file}")
if not os.path.exists(csv_file):
    print(f"File not found: {csv_file}")
    exit(1)

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    rows = list(reader)
    
    print(f"Total columns: {len(cols)}")
    print(f"Total rows: {len(rows)}")
    
    # Check enhanced columns
    enhanced_cols = ['flag', 'mapping_status', 'semantic_match_score', 
                     'nutritional_similarity_score', 'reasoning', 'retry_attempts', 
                     'search_queries_used', 'timestamp']
    
    print(f"\nEnhanced columns present:")
    for col in enhanced_cols:
        present = "[OK]" if col in cols else "[MISSING]"
        print(f"  {present} {col}")
    
    # Show sample data
    if rows:
        print(f"\nSample Row 1:")
        r = rows[0]
        print(f"  Ingredient: {r.get('ingredient')}")
        print(f"  Flag: {r.get('flag')}")
        print(f"  Mapping Status: {r.get('mapping_status')}")
        print(f"  Semantic Match Score: {r.get('semantic_match_score')}")
        print(f"  Nutritional Similarity Score: {r.get('nutritional_similarity_score')}")
        print(f"  Retry Attempts: {r.get('retry_attempts')}")
        print(f"  Search Queries: {r.get('search_queries_used')[:80]}...")
        print(f"  Timestamp: {r.get('timestamp')}")
        
        # Check reasoning length
        reasoning = r.get('reasoning', '')
        print(f"  Reasoning length: {len(reasoning)} chars")

