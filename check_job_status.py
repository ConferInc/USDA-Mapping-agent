"""Check current job status"""
import os
import csv
import glob
from datetime import datetime

# Find latest temp file
temp_files = glob.glob("failed_ingredients_enhanced_results*_temp.csv")
if not temp_files:
    print("No temp files found. Job may not have started or may have completed.")
    exit(0)

latest_file = max(temp_files, key=os.path.getmtime)

# Get file stats
file_size = os.path.getsize(latest_file)
file_mtime = datetime.fromtimestamp(os.path.getmtime(latest_file))

print(f"Monitoring: {latest_file}")
print(f"File size: {file_size:,} bytes")
print(f"Last modified: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}\n")

# Count rows
try:
    with open(latest_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        total = 154  # Total ingredients in failed_ingredients.csv
        processed = len(rows)
        remaining = total - processed
        progress_pct = (processed / total) * 100
        
        print(f"Progress: {processed}/{total} ingredients ({progress_pct:.1f}%)")
        print(f"Remaining: {remaining} ingredients\n")
        
        # Count by flag
        flags = {}
        for row in rows:
            flag = row.get('flag', 'UNKNOWN')
            flags[flag] = flags.get(flag, 0) + 1
        
        print("Results by flag:")
        for flag, count in sorted(flags.items(), key=lambda x: x[1], reverse=True):
            pct = (count / processed) * 100 if processed > 0 else 0
            print(f"  {flag}: {count} ({pct:.1f}%)")
        
        # Show latest processed
        if rows:
            latest = rows[-1]
            print(f"\nLatest processed:")
            print(f"  Ingredient: {latest.get('ingredient', 'N/A')}")
            print(f"  Flag: {latest.get('flag', 'N/A')}")
            print(f"  Semantic Score: {latest.get('semantic_match_score', 'N/A')}")
            print(f"  Nutrition Score: {latest.get('nutritional_similarity_score', 'N/A')}")
            print(f"  Retry Attempts: {latest.get('retry_attempts', 'N/A')}")
            
            # Estimate time remaining
            if processed > 0:
                elapsed_minutes = (datetime.now() - file_mtime).total_seconds() / 60
                avg_time_per = elapsed_minutes / processed
                estimated_remaining = avg_time_per * remaining
                print(f"\nTime Estimates:")
                print(f"  Average time per ingredient: {avg_time_per:.1f} minutes")
                print(f"  Estimated time remaining: {estimated_remaining:.1f} minutes ({estimated_remaining/60:.1f} hours)")
        
except Exception as e:
    print(f"Error reading file: {e}")

