"""Monitor progress of running job"""
import os
import glob
import csv
from datetime import datetime

# Find latest output file
csv_files = glob.glob("failed_ingredients_enhanced_results*.csv")
if not csv_files:
    print("No output files found yet. Job may still be starting...")
    exit(0)

latest_file = max(csv_files, key=os.path.getmtime)
print(f"Monitoring: {latest_file}\n")

# Count rows in CSV
try:
    with open(latest_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        print(f"Progress: {len(rows)} ingredients processed")
        
        # Count by flag
        flags = {}
        for row in rows:
            flag = row.get('flag', 'UNKNOWN')
            flags[flag] = flags.get(flag, 0) + 1
        
        print(f"\nResults by flag:")
        for flag, count in sorted(flags.items()):
            print(f"  {flag}: {count}")
        
        # Show latest processed
        if rows:
            latest = rows[-1]
            print(f"\nLatest processed:")
            print(f"  Ingredient: {latest.get('ingredient')}")
            print(f"  Flag: {latest.get('flag')}")
            print(f"  Semantic Score: {latest.get('semantic_match_score')}")
            print(f"  Nutrition Score: {latest.get('nutritional_similarity_score')}")
            print(f"  Processing Time: {latest.get('processing_time_seconds')}s")
            
            # Check if temp file exists (means job is still running)
            temp_file = latest_file.replace('.csv', '_temp.csv')
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8') as tf:
                    temp_reader = csv.DictReader(tf)
                    temp_rows = list(temp_reader)
                    print(f"\n  Temp file shows: {len(temp_rows)} results (job still running)")
        
except Exception as e:
    print(f"Error reading file: {e}")


