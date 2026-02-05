"""
Data Saving Utilities
"""

import csv
import json
import os
from typing import List, Dict
from pathlib import Path


def save_results(results: List[Dict], output_path: str, format: str = "json") -> bool:
    """
    Save results to file.
    
    Args:
        results: List of result dictionaries
        output_path: Output file path
        format: Output format ("json" or "csv")
    
    Returns:
        True if saved successfully
    """
    if format == "json":
        return save_json(results, output_path)
    elif format == "csv":
        return save_csv(results, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}")


def save_json(results: List[Dict], output_path: str) -> bool:
    """
    Save results to JSON file.
    
    Args:
        results: List of result dictionaries
        output_path: Output file path
    
    Returns:
        True if saved successfully
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Saved {len(results)} results to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving JSON to {output_path}: {e}")
        return False


def save_csv(results: List[Dict], output_path: str) -> bool:
    """
    Save results to CSV file.
    
    Args:
        results: List of result dictionaries
        output_path: Output file path
    
    Returns:
        True if saved successfully
    """
    if not results:
        print("Warning: No results to save")
        return False
    
    try:
        # Use standardized_nutrients if available, otherwise fall back to nutrients
        # Collect all unique nutrient IDs from standardized_nutrients
        all_nutrient_ids = set()
        for result in results:
            standardized = result.get("standardized_nutrients", {})
            if standardized:
                all_nutrient_ids.update(standardized.keys())
            else:
                # Fallback to raw nutrients
                nutrients = result.get("nutrients", {})
                all_nutrient_ids.update(nutrients.keys())
        
        # Sort nutrient IDs for consistent column order
        all_nutrient_ids = sorted(list(all_nutrient_ids))
        
        # Flatten results for CSV
        rows = []
        for result in results:
            row = {
                "ingredient": result.get("ingredient", ""),
                "fdc_id": result.get("fdc_id", ""),
                "description": result.get("description", ""),
                "data_type": result.get("data_type", ""),
                "brand_owner": result.get("brand_owner", ""),
                "source": result.get("source", ""),
            }
            
            # Use standardized_nutrients if available
            standardized = result.get("standardized_nutrients", {})
            if standardized:
                # Add all standardized nutrients
                for nutrient_id in all_nutrient_ids:
                    nutrient_data = standardized.get(nutrient_id)
                    if nutrient_data and nutrient_data is not None:
                        amount = nutrient_data.get("amount", "")
                        unit = nutrient_data.get("unit", "")
                        row[nutrient_id] = f"{amount} {unit}".strip() if amount else ""
                    else:
                        row[nutrient_id] = ""  # NULL value
            else:
                # Fallback to raw nutrients
                nutrients = result.get("nutrients", {})
                for nutrient_id in all_nutrient_ids:
                    nutrient_data = nutrients.get(nutrient_id)
                    if nutrient_data:
                        amount = nutrient_data.get("amount", "")
                        unit = nutrient_data.get("unit", "")
                        row[nutrient_id] = f"{amount} {unit}".strip() if amount else ""
                    else:
                        row[nutrient_id] = ""
            
            rows.append(row)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Define fieldnames with nutrients in sorted order
        fieldnames = ["ingredient", "fdc_id", "description", "data_type", "brand_owner", "source"] + all_nutrient_ids
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"[OK] Saved {len(results)} results to {output_path}")
        return True
    except Exception as e:
        print(f"Error saving CSV to {output_path}: {e}")
        return False

