"""
Enhanced Data Saving Utilities - With reasoning, flag, nutrition_score columns
"""

import csv
import json
import os
from typing import List, Dict
from pathlib import Path


def save_results_enhanced(results: List[Dict], output_path: str, format: str = "json", mode: str = "standard") -> bool:
    """
    Save results to file with enhanced metadata columns.
    
    Args:
        results: List of result dictionaries
        output_path: Output file path
        format: Output format ("json", "json-clean", "json-debug", "json-batch", "csv", "csv-debug")
        mode: Output mode ("standard" or "debug") - for backward compatibility
    
    Returns:
        True if saved successfully
    """
    # Handle format aliases
    if format == "json":
        if mode == "debug":
            format = "json-debug"
        else:
            format = "json"  # Default JSON includes debug info
    elif format == "csv":
        if mode == "debug":
            format = "csv-debug"
        else:
            format = "csv-standard"
    
    # Route to appropriate saver
    if format == "csv-standard" or format == "csv":
        return save_csv_enhanced(results, output_path)
    elif format == "csv-debug":
        return save_csv_debug(results, output_path)
    elif format == "json" or format == "json-debug":
        return save_json_debug(results, output_path)
    elif format == "json-clean":
        return save_json_clean(results, output_path)
    elif format == "json-batch":
        return save_json_batch(results, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'csv', 'csv-debug', 'json', 'json-clean', 'json-debug', or 'json-batch'")


def save_json_enhanced(results: List[Dict], output_path: str) -> bool:
    """Save results to JSON file with enhanced metadata (alias for json-debug)"""
    return save_json_debug(results, output_path)


def save_json_debug(results: List[Dict], output_path: str) -> bool:
    """Save results to JSON file with full debugging information"""
    try:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Saved {len(results)} results to {output_path} (debug mode)")
        return True
    except Exception as e:
        print(f"Error saving JSON to {output_path}: {e}")
        return False


def save_json_clean(results: List[Dict], output_path: str) -> bool:
    """
    Save results to JSON file with clean format (minimal payload for API use).
    Only includes essential fields: ingredient, fdc_id, description, data_type, flag, nutrients, timestamp
    """
    if not results:
        print("Warning: No results to save")
        return False
    
    try:
        clean_results = []
        for result in results:
            clean_result = {
                "ingredient": result.get("ingredient", ""),
                "fdc_id": result.get("fdc_id"),
                "description": result.get("description", ""),
                "data_type": result.get("data_type", ""),
                "flag": result.get("flag", ""),
                "mapping_status": result.get("mapping_status", ""),
                "nutrients": {},
                "timestamp": result.get("timestamp", "")
            }
            
            # Add all nutrients in clean format
            standardized = result.get("standardized_nutrients", {})
            for nutrient_id, nutrient_data in standardized.items():
                if nutrient_data and nutrient_data is not None:
                    clean_result["nutrients"][nutrient_id] = {
                        "amount": nutrient_data.get("amount"),
                        "unit": nutrient_data.get("unit", "")
                    }
            
            clean_results.append(clean_result)
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Saved {len(results)} results to {output_path} (clean mode)")
        return True
    except Exception as e:
        print(f"Error saving clean JSON to {output_path}: {e}")
        return False


def save_json_batch(results: List[Dict], output_path: str) -> bool:
    """
    Save results to JSON file in batch format with summary statistics.
    Structure: {summary: {...}, results: [...], failed_ingredients: [...]}
    """
    if not results:
        print("Warning: No results to save")
        return False
    
    try:
        # Calculate summary
        successful = sum(1 for r in results if r.get("flag") in ["HIGH_CONFIDENCE", "MID_CONFIDENCE"])
        failed = len(results) - successful
        total_time = sum(r.get("processing_time_seconds", 0) or 0 for r in results)
        
        # Extract clean results
        clean_results = []
        for result in results:
            clean_result = {
                "ingredient": result.get("ingredient", ""),
                "fdc_id": result.get("fdc_id"),
                "description": result.get("description", ""),
                "data_type": result.get("data_type", ""),
                "flag": result.get("flag", ""),
                "mapping_status": result.get("mapping_status", ""),
                "nutrients": {},
                "timestamp": result.get("timestamp", "")
            }
            
            # Add all nutrients
            standardized = result.get("standardized_nutrients", {})
            for nutrient_id, nutrient_data in standardized.items():
                if nutrient_data and nutrient_data is not None:
                    clean_result["nutrients"][nutrient_id] = {
                        "amount": nutrient_data.get("amount"),
                        "unit": nutrient_data.get("unit", "")
                    }
            
            clean_results.append(clean_result)
        
        # Extract failed ingredients
        failed_ingredients = [r.get("ingredient", "") for r in results if r.get("flag") not in ["HIGH_CONFIDENCE", "MID_CONFIDENCE"]]
        
        batch_output = {
            "summary": {
                "total": len(results),
                "successful": successful,
                "failed": failed,
                "processing_time_seconds": round(total_time, 2)
            },
            "results": clean_results,
            "failed_ingredients": failed_ingredients,
            "timestamp": results[0].get("timestamp", "") if results else ""
        }
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(batch_output, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Saved {len(results)} results to {output_path} (batch mode)")
        return True
    except Exception as e:
        print(f"Error saving batch JSON to {output_path}: {e}")
        return False


def save_csv_enhanced(results: List[Dict], output_path: str) -> bool:
    """
    Save results to CSV file with standard columns (enhanced):
    - ingredient, fdc_id, description, data_type, brand_owner, source
    - flag, mapping_status, semantic_match_score, nutritional_similarity_score
    - reasoning, retry_attempts, search_queries_used, timestamp
    - processing_time_seconds
    - All 116 standardized nutrients
    """
    if not results:
        print("Warning: No results to save")
        return False
    
    try:
        # Collect all unique nutrient IDs
        all_nutrient_ids = set()
        for result in results:
            standardized = result.get("standardized_nutrients", {})
            if standardized:
                all_nutrient_ids.update(standardized.keys())
        
        all_nutrient_ids = sorted(list(all_nutrient_ids))
        
        # Flatten results for CSV
        rows = []
        for result in results:
            row = {
                # Basic metadata
                "ingredient": result.get("ingredient", ""),
                "fdc_id": result.get("fdc_id", ""),
                "description": result.get("description", ""),
                "data_type": result.get("data_type", ""),
                "brand_owner": result.get("brand_owner", ""),
                "source": result.get("source", ""),
                
                # Enhanced metadata
                "flag": result.get("flag", ""),
                "mapping_status": result.get("mapping_status", ""),
                "semantic_match_score": result.get("semantic_match_score", ""),
                "nutritional_similarity_score": result.get("nutritional_similarity_score", ""),
                "reasoning": str(result.get("reasoning", "")).replace('"', "'"),  # Replace double quotes with single quotes to avoid CSV issues
                "retry_attempts": str(result.get("retry_attempts", "")),
                "search_queries_used": str(result.get("search_queries_used", "")).replace('"', "'"),  # Replace double quotes with single quotes to avoid CSV issues
                "timestamp": str(result.get("timestamp", "")),
                "processing_time_seconds": result.get("processing_time_seconds", ""),
            }
            
            # Add all standardized nutrients
            standardized = result.get("standardized_nutrients", {})
            for nutrient_id in all_nutrient_ids:
                nutrient_data = standardized.get(nutrient_id)
                if nutrient_data and nutrient_data is not None:
                    amount = nutrient_data.get("amount", "")
                    unit = nutrient_data.get("unit", "")
                    row[nutrient_id] = f"{amount} {unit}".strip() if amount else ""
                else:
                    row[nutrient_id] = ""  # NULL value
            
            rows.append(row)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Define fieldnames
        metadata_fields = [
            "ingredient", "fdc_id", "description", "data_type", "brand_owner", "source",
            "flag", "mapping_status", "semantic_match_score", "nutritional_similarity_score",
            "reasoning", "retry_attempts", "search_queries_used", "timestamp", "processing_time_seconds"
        ]
        fieldnames = metadata_fields + all_nutrient_ids
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, escapechar='\\')
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"[OK] Saved {len(results)} results to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving CSV to {output_path}: {e}")
        return False


def save_csv_debug(results: List[Dict], output_path: str) -> bool:
    """
    Save results to CSV file with full debugging columns:
    - All standard columns
    - Step-by-step timing (curated_mapping, search, semantic, nutritional, extraction)
    - Tier distribution (tier_1_count, tier_2_count, tier_3_count, tier_4_count)
    - Search metrics (total_search_results, semantic_verified_count)
    - Top 3 semantic results (score + description)
    - Top 3 nutritional results (score + description)
    - API/LLM metrics (api_calls_count, llm_calls_count, cache_hits, cache_misses)
    - Attempt details (attempt_1_query, attempt_1_success, attempt_2_query, attempt_2_success)
    - All 116 standardized nutrients
    """
    if not results:
        print("Warning: No results to save")
        return False
    
    try:
        # Collect all unique nutrient IDs
        all_nutrient_ids = set()
        for result in results:
            standardized = result.get("standardized_nutrients", {})
            if standardized:
                all_nutrient_ids.update(standardized.keys())
        
        all_nutrient_ids = sorted(list(all_nutrient_ids))
        
        # Flatten results for CSV
        rows = []
        for result in results:
            debug = result.get("debug", {})
            timing = debug.get("timing", {})
            tier_dist = debug.get("tier_distribution", {})
            search_metrics = debug.get("search_metrics", {})
            api_metrics = debug.get("api_metrics", {})
            top_semantic = search_metrics.get("top_semantic_results", [])
            top_nutritional = search_metrics.get("top_nutritional_results", [])
            attempt_details = debug.get("attempt_details", [])
            
            row = {
                # Basic metadata
                "ingredient": result.get("ingredient", ""),
                "fdc_id": result.get("fdc_id", ""),
                "description": result.get("description", ""),
                "data_type": result.get("data_type", ""),
                "brand_owner": result.get("brand_owner", ""),
                "source": result.get("source", ""),
                
                # Enhanced metadata
                "flag": result.get("flag", ""),
                "mapping_status": result.get("mapping_status", ""),
                "semantic_match_score": result.get("semantic_match_score", ""),
                "nutritional_similarity_score": result.get("nutritional_similarity_score", ""),
                "reasoning": str(result.get("reasoning", "")).replace('"', "'"),
                "retry_attempts": str(result.get("retry_attempts", "")),
                "search_queries_used": str(result.get("search_queries_used", "")).replace('"', "'"),
                "timestamp": str(result.get("timestamp", "")),
                "processing_time_seconds": result.get("processing_time_seconds", ""),
                
                # Timing breakdown
                "curated_mapping_time_seconds": timing.get("curated_mapping_time_seconds", ""),
                "search_time_seconds": timing.get("search_time_seconds", ""),
                "semantic_verification_time_seconds": timing.get("semantic_verification_time_seconds", ""),
                "nutritional_scoring_time_seconds": timing.get("nutritional_scoring_time_seconds", ""),
                "extraction_time_seconds": timing.get("extraction_time_seconds", ""),
                
                # Tier distribution
                "tier_1_count": tier_dist.get("tier_1_count", 0),
                "tier_2_count": tier_dist.get("tier_2_count", 0),
                "tier_3_count": tier_dist.get("tier_3_count", 0),
                "tier_4_count": tier_dist.get("tier_4_count", 0),
                
                # Search metrics
                "total_search_results": search_metrics.get("total_search_results", 0),
                "semantic_verified_count": search_metrics.get("semantic_verified_count", 0),
                
                # Top 3 semantic results
                "top_semantic_score_1": top_semantic[0].get("score", "") if len(top_semantic) > 0 else "",
                "top_semantic_desc_1": top_semantic[0].get("description", "") if len(top_semantic) > 0 else "",
                "top_semantic_score_2": top_semantic[1].get("score", "") if len(top_semantic) > 1 else "",
                "top_semantic_desc_2": top_semantic[1].get("description", "") if len(top_semantic) > 1 else "",
                "top_semantic_score_3": top_semantic[2].get("score", "") if len(top_semantic) > 2 else "",
                "top_semantic_desc_3": top_semantic[2].get("description", "") if len(top_semantic) > 2 else "",
                
                # Top 3 nutritional results
                "top_nutritional_score_1": top_nutritional[0].get("score", "") if len(top_nutritional) > 0 else "",
                "top_nutritional_desc_1": top_nutritional[0].get("description", "") if len(top_nutritional) > 0 else "",
                "top_nutritional_score_2": top_nutritional[1].get("score", "") if len(top_nutritional) > 1 else "",
                "top_nutritional_desc_2": top_nutritional[1].get("description", "") if len(top_nutritional) > 1 else "",
                "top_nutritional_score_3": top_nutritional[2].get("score", "") if len(top_nutritional) > 2 else "",
                "top_nutritional_desc_3": top_nutritional[2].get("description", "") if len(top_nutritional) > 2 else "",
                
                # API/LLM metrics
                "api_calls_count": api_metrics.get("api_calls_count", 0),
                "llm_calls_count": api_metrics.get("llm_calls_count", 0),
                "cache_hits": api_metrics.get("cache_hits", 0),
                "cache_misses": api_metrics.get("cache_misses", 0),
                
                # Attempt details
                "attempt_1_query": attempt_details[0].get("query", "") if len(attempt_details) > 0 else "",
                "attempt_1_success": attempt_details[0].get("success", "") if len(attempt_details) > 0 else "",
                "attempt_2_query": attempt_details[1].get("query", "") if len(attempt_details) > 1 else "",
                "attempt_2_success": attempt_details[1].get("success", "") if len(attempt_details) > 1 else "",
            }
            
            # Add all standardized nutrients
            standardized = result.get("standardized_nutrients", {})
            for nutrient_id in all_nutrient_ids:
                nutrient_data = standardized.get(nutrient_id)
                if nutrient_data and nutrient_data is not None:
                    amount = nutrient_data.get("amount", "")
                    unit = nutrient_data.get("unit", "")
                    row[nutrient_id] = f"{amount} {unit}".strip() if amount else ""
                else:
                    row[nutrient_id] = ""  # NULL value
            
            rows.append(row)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Define fieldnames
        metadata_fields = [
            "ingredient", "fdc_id", "description", "data_type", "brand_owner", "source",
            "flag", "mapping_status", "semantic_match_score", "nutritional_similarity_score",
            "reasoning", "retry_attempts", "search_queries_used", "timestamp", "processing_time_seconds",
            "curated_mapping_time_seconds", "search_time_seconds", "semantic_verification_time_seconds",
            "nutritional_scoring_time_seconds", "extraction_time_seconds",
            "tier_1_count", "tier_2_count", "tier_3_count", "tier_4_count",
            "total_search_results", "semantic_verified_count",
            "top_semantic_score_1", "top_semantic_desc_1",
            "top_semantic_score_2", "top_semantic_desc_2",
            "top_semantic_score_3", "top_semantic_desc_3",
            "top_nutritional_score_1", "top_nutritional_desc_1",
            "top_nutritional_score_2", "top_nutritional_desc_2",
            "top_nutritional_score_3", "top_nutritional_desc_3",
            "api_calls_count", "llm_calls_count", "cache_hits", "cache_misses",
            "attempt_1_query", "attempt_1_success", "attempt_2_query", "attempt_2_success"
        ]
        fieldnames = metadata_fields + all_nutrient_ids
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, escapechar='\\')
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"[OK] Saved {len(results)} results to {output_path} (debug mode)")
        return True
    except Exception as e:
        print(f"Error saving debug CSV to {output_path}: {e}")
        return False


