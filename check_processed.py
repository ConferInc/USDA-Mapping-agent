"""Check which ingredients have been processed"""
import csv

temp_file = "failed_ingredients_enhanced_results_20260109_193246_temp.csv"

try:
    with open(temp_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        processed = [r['ingredient'] for r in rows]
        
        print(f"Processed ingredients: {len(processed)}/154")
        print(f"\nLast processed: {processed[-1] if processed else 'None'}")
        print(f"\nFirst 5: {processed[:5] if len(processed) >= 5 else processed}")
        print(f"Last 5: {processed[-5:] if len(processed) >= 5 else processed}")
        
        # Load all ingredients
        with open("../nutrition_usda/failed_ingredients.csv", 'r', encoding='utf-8') as all_f:
            all_reader = csv.DictReader(all_f)
            all_ingredients = [row['ingredient'] for row in all_reader]
        
        # Find index of last processed ingredient
        if processed:
            last_ingredient = processed[-1]
            try:
                last_index = all_ingredients.index(last_ingredient)
                next_index = last_index + 1
                print(f"\nLast processed index: {last_index}")
                print(f"Next ingredient to process: {all_ingredients[next_index] if next_index < len(all_ingredients) else 'None'}")
                print(f"To resume, use: --start-from {next_index}")
            except ValueError:
                print(f"\nCould not find '{last_ingredient}' in full list")
        else:
            print("\nNo ingredients processed yet. Start from 0.")
            
except Exception as e:
    print(f"Error: {e}")

