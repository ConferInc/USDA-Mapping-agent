"""
Workflow Orchestrator - Coordinates the entire nutrition fetching process
"""

import os
import sys
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.mapping_tool import search_mappings
from tools.llm_tool import generate_search_intent
from tools.cache_tool import get_cached_search_intent, save_search_intent_cache
from tools.usda_api_tool import search_usda_food, get_usda_food_details
from tools.scoring_tool import filter_search_results
from tools.nutrition_extractor_tool import extract_nutrition_data
from utils.data_loader import load_ingredients
from utils.data_saver import save_results


class NutritionFetchOrchestrator:
    """Orchestrates the nutrition fetching workflow"""
    
    def __init__(self):
        """Initialize the orchestrator"""
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "from_mappings": 0,
            "from_search": 0
        }
    
    def fetch_nutrition_for_ingredient(self, ingredient: str) -> Optional[Dict]:
        """
        Fetch nutrition data for a single ingredient using the full workflow.
        
        Args:
            ingredient: Ingredient name
        
        Returns:
            Nutrition data dictionary or None if failed
        """
        print(f"\n{'='*80}")
        print(f"Processing: {ingredient}")
        print(f"{'='*80}")
        
        # Step 1: Check curated mappings (fast path)
        print(f"\n[Step 1] Checking curated mappings...")
        mapping = search_mappings(ingredient)
        
        if mapping:
            print(f"[OK] Found in mappings! FDC ID: {mapping.get('fdc_id')}")
            fdc_id = mapping.get('fdc_id')
            
            # Step 5: Extract nutrition data directly
            print(f"\n[Step 5] Extracting nutrition data...")
            food_data = get_usda_food_details(fdc_id)
            if food_data:
                nutrition_data = extract_nutrition_data(food_data)
                if nutrition_data:
                    nutrition_data["ingredient"] = ingredient
                    nutrition_data["source"] = "curated_mapping"
                    self.stats["from_mappings"] += 1
                    print(f"[SUCCESS] Extracted nutrition data for '{ingredient}'")
                    return nutrition_data
        
        # Step 2: Generate search strategy (if not in mappings)
        print(f"\n[Step 2] Generating search strategy...")
        # Check cache first
        intent = get_cached_search_intent(ingredient)
        if not intent:
            intent = generate_search_intent(ingredient)
            if intent:
                save_search_intent_cache(ingredient, intent)
        
        if not intent:
            # Fallback to simple intent
            intent = {
                "search_query": ingredient,
                "is_phrase": " " in ingredient.lower(),
                "preferred_form": "",
                "avoid": [],
                "expected_pattern": ""
            }
        
        print(f"[OK] Search query: {intent.get('search_query')}")
        
        # Step 3: Search USDA API
        print(f"\n[Step 3] Searching USDA API...")
        search_query = intent.get('search_query', ingredient)
        search_results = search_usda_food(search_query, page_size=50, data_type="Foundation,SR Legacy")
        
        if not search_results:
            # Try without data type filter
            print(f"  No results with filter, trying without filter...")
            search_results = search_usda_food(search_query, page_size=50)
        
        if not search_results:
            print(f"[ERROR] No search results found for '{ingredient}'")
            return None
        
        print(f"[OK] Found {len(search_results)} search results")
        
        # Step 4: Score and rank
        print(f"\n[Step 4] Scoring and ranking results...")
        scored_results = filter_search_results(search_results, ingredient, max_score=50)
        
        if not scored_results:
            print(f"[WARNING] No good matches found, trying with higher threshold...")
            scored_results = filter_search_results(search_results, ingredient, max_score=200)
        
        if not scored_results:
            print(f"[ERROR] No acceptable matches found for '{ingredient}'")
            return None
        
        best_match = scored_results[0][1]  # Get the food item from the best match
        fdc_id = best_match.get('fdcId')
        score_info = scored_results[0][0]
        print(f"[OK] Best match: {best_match.get('description')} (FDC ID: {fdc_id}, score: {score_info[0]})")
        
        # Step 5: Extract nutrition data
        print(f"\n[Step 5] Extracting nutrition data...")
        food_data = get_usda_food_details(fdc_id)
        if food_data:
            nutrition_data = extract_nutrition_data(food_data)
            if nutrition_data:
                nutrition_data["ingredient"] = ingredient
                nutrition_data["source"] = "search"
                self.stats["from_search"] += 1
                print(f"[SUCCESS] Extracted nutrition data for '{ingredient}'")
                return nutrition_data
        
        print(f"[ERROR] Failed to extract nutrition data for '{ingredient}'")
        return None
    
    def process_ingredients(self, ingredients: List[str], output_file: str = "nutrition_data.csv", 
                          format: str = "csv", limit: Optional[int] = None, 
                          start_from: int = 0) -> Dict:
        """
        Process a list of ingredients and save results.
        
        Args:
            ingredients: List of ingredient names
            output_file: Output file path
            format: Output format ("json" or "csv")
            limit: Optional limit on number of ingredients to process
            start_from: Start from this index
        
        Returns:
            Dictionary with processing statistics
        """
        # Apply limits
        if start_from > 0:
            ingredients = ingredients[start_from:]
            print(f"Starting from index {start_from}")
        
        if limit:
            ingredients = ingredients[:limit]
            print(f"Processing {len(ingredients)} ingredients (limited)")
        
        self.stats["total"] = len(ingredients)
        
        results = []
        failed = []
        
        print(f"\n{'='*80}")
        print(f"PROCESSING {len(ingredients)} INGREDIENTS")
        print(f"{'='*80}\n")
        
        for i, ingredient in enumerate(ingredients, 1):
            print(f"\n[{i}/{len(ingredients)}]")
            
            try:
                nutrition_data = self.fetch_nutrition_for_ingredient(ingredient)
                if nutrition_data:
                    results.append(nutrition_data)
                    self.stats["successful"] += 1
                else:
                    failed.append(ingredient)
                    self.stats["failed"] += 1
            except Exception as e:
                print(f"[ERROR] Exception processing '{ingredient}': {e}")
                failed.append(ingredient)
                self.stats["failed"] += 1
            
            # Save progress periodically
            if i % 10 == 0:
                temp_output = output_file.replace('.csv', '_temp.csv').replace('.json', '_temp.json')
                save_results(results, temp_output, format)
                print(f"\n[PROGRESS] Saved: {len(results)} successful, {len(failed)} failed")
        
        # Save final results
        if results:
            save_results(results, output_file, format)
            print(f"\n[SUCCESS] Saved {len(results)} results to {output_file}")
        
        if failed:
            failed_file = output_file.replace('.csv', '_failed.txt').replace('.json', '_failed.txt')
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(failed))
            print(f"[INFO] Saved {len(failed)} failed ingredients to {failed_file}")
        
        # Print summary
        self._print_summary()
        
        return {
            "total": self.stats["total"],
            "successful": self.stats["successful"],
            "failed": self.stats["failed"],
            "from_mappings": self.stats["from_mappings"],
            "from_search": self.stats["from_search"],
            "results": results,
            "failed_ingredients": failed
        }
    
    def _print_summary(self):
        """Print processing summary"""
        print(f"\n{'='*80}")
        print("PROCESSING SUMMARY")
        print(f"{'='*80}")
        print(f"Total processed: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']} ({self.stats['successful']/self.stats['total']*100:.1f}%)")
        print(f"Failed: {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        print(f"From mappings (fast path): {self.stats['from_mappings']}")
        print(f"From search: {self.stats['from_search']}")
        print(f"{'='*80}")


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fetch nutrition profiles from USDA API for ingredients using CrewAI workflow"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input CSV file with ingredients"
    )
    parser.add_argument(
        "--output",
        default="nutrition_data.csv",
        help="Output file path (default: nutrition_data.csv)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="csv",
        help="Output format: json or csv (default: csv)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of ingredients to process (for testing)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start from this ingredient index (for resuming)"
    )
    
    args = parser.parse_args()
    
    # Validate API key
    if not os.getenv("USDA_API_KEY"):
        print("[ERROR] USDA_API_KEY not found in environment!")
        print("Please add it to your .env file")
        sys.exit(1)
    
    # Load ingredients
    print(f"Loading ingredients from {args.input}...")
    ingredients = load_ingredients(args.input)
    print(f"Loaded {len(ingredients)} ingredients")
    
    # Create orchestrator
    orchestrator = NutritionFetchOrchestrator()
    
    # Process ingredients
    results = orchestrator.process_ingredients(
        ingredients,
        output_file=args.output,
        format=args.format,
        limit=args.limit,
        start_from=args.start_from
    )
    
    print(f"\n[COMPLETE] Processing finished!")
    return results


if __name__ == "__main__":
    main()


