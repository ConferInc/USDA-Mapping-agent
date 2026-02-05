"""Verify threshold logic"""
import csv
import glob

csv_files = glob.glob("test_thresholds_*.csv")
csv_file = csv_files[-1] if csv_files else None

if not csv_file:
    print("No test file found")
    exit(1)

print(f"Checking: {csv_file}\n")

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
    print("Threshold Test Results:")
    print("="*60)
    
    for i, r in enumerate(rows, 1):
        ingredient = r.get("ingredient", "")
        flag = r.get("flag", "")
        score = r.get("nutritional_similarity_score", "")
        status = r.get("mapping_status", "")
        
        print(f"\n{i}. {ingredient}")
        print(f"   Flag: {flag}")
        print(f"   Nutrition Score: {score}%")
        print(f"   Mapping Status: {status}")
        
        # Verify threshold logic
        try:
            score_val = float(score) if score else 0
            if score_val >= 90:
                expected = "HIGH_CONFIDENCE"
            elif score_val >= 80:
                expected = "MID_CONFIDENCE"
            else:
                expected = "LOW_CONFIDENCE"
            
            if flag == expected:
                print(f"   [OK] Flag matches threshold logic")
            else:
                print(f"   [ERROR] Expected {expected}, got {flag}")
        except:
            pass


