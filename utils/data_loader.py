"""
Data Loading Utilities - Universal input format support
"""

import csv
import json
import os
from typing import List, Optional
from pathlib import Path


def load_ingredients(csv_path: str) -> List[str]:
    """
    Load ingredients from CSV file (legacy function for backward compatibility).
    
    Args:
        csv_path: Path to CSV file with 'ingredient' column
    
    Returns:
        List of ingredient names
    """
    return load_ingredients_universal(csv_path, format="csv")


def load_ingredients_universal(file_path: str, format: str = "auto") -> List[str]:
    """
    Universal ingredient loader supporting CSV, TXT, and JSON formats.
    Auto-detects format if not specified.
    
    Args:
        file_path: Path to input file (CSV, TXT, or JSON)
        format: Input format ("auto", "csv", "txt", "json")
    
    Returns:
        List of ingredient names
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If format detection fails or parsing fails
    """
    # Try multiple possible paths
    possible_paths = [
        file_path,
        f"../nutrition_usda/{file_path}",
        os.path.join(os.path.dirname(__file__), "..", "..", "nutrition_usda", file_path)
    ]
    
    file_path_resolved = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path_resolved = path
            break
    
    if not file_path_resolved:
        raise FileNotFoundError(f"Could not find input file: {file_path}")
    
    # Auto-detect format if needed
    if format == "auto":
        format = _detect_file_format(file_path_resolved)
    
    # Parse based on format
    if format == "csv":
        return _parse_csv(file_path_resolved)
    elif format == "txt":
        return _parse_txt(file_path_resolved)
    elif format == "json":
        return _parse_json(file_path_resolved)
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'csv', 'txt', or 'json'")


def _detect_file_format(file_path: str) -> str:
    """
    Auto-detect file format by extension and content.
    
    Args:
        file_path: Path to file
    
    Returns:
        Detected format ("csv", "txt", or "json")
    """
    # Check by extension first
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return "csv"
    elif ext == ".txt" or ext == ".text":
        return "txt"
    elif ext == ".json":
        return "json"
    
    # Try to detect by content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            
            # Check if it's JSON
            if first_line.startswith('[') or first_line.startswith('{'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f2:
                        json.load(f2)
                    return "json"
                except:
                    pass
            
            # Check if it's CSV (has comma and looks like header)
            if ',' in first_line:
                return "csv"
            
            # Default to text
            return "txt"
    except Exception:
        # Default to text if detection fails
        return "txt"


def _parse_csv(file_path: str) -> List[str]:
    """
    Parse CSV file and extract ingredients.
    Looks for 'ingredient', 'name', 'food', or 'item' column.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        List of ingredient names
    """
    ingredients = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Find ingredient column (case-insensitive)
        fieldnames = reader.fieldnames or []
        ingredient_column = None
        
        for col in ['ingredient', 'name', 'food', 'item', 'ingredients']:
            for field in fieldnames:
                if field.lower() == col.lower():
                    ingredient_column = field
                    break
            if ingredient_column:
                break
        
        # If no ingredient column found, use first text column
        if not ingredient_column and fieldnames:
            ingredient_column = fieldnames[0]
        
        if not ingredient_column:
            raise ValueError("Could not find ingredient column in CSV file")
        
        for row in reader:
            ingredient = row.get(ingredient_column, '').strip()
            if ingredient:
                ingredients.append(ingredient)
    
    return ingredients


def _parse_txt(file_path: str) -> List[str]:
    """
    Parse text file (one ingredient per line).
    Skips empty lines and comment lines (starting with # or //).
    
    Args:
        file_path: Path to text file
    
    Returns:
        List of ingredient names
    """
    ingredients = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        # Skip header if first line looks like a header
        start_idx = 0
        if lines and (lines[0].lower().strip() in ['ingredient', 'ingredients', 'name', 'food', 'item']):
            start_idx = 1
        
        for line in lines[start_idx:]:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Skip comment lines
            if line.startswith('#') or line.startswith('//'):
                continue
            
            # Remove inline comments
            if '#' in line:
                line = line.split('#')[0].strip()
            if '//' in line:
                line = line.split('//')[0].strip()
            
            if line:
                ingredients.append(line)
    
    return ingredients


def _parse_json(file_path: str) -> List[str]:
    """
    Parse JSON file and extract ingredients.
    Supports multiple JSON structures:
    - Simple array: ["ingredient1", "ingredient2"]
    - Array of objects: [{"ingredient": "..."}, {"name": "..."}]
    - Object with ingredients key: {"ingredients": [...]}
    - Object with data key: {"data": [{"name": "..."}]}
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        List of ingredient names
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    ingredients = []
    
    # Case 1: Simple array of strings
    if isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], str):
            # ["ingredient1", "ingredient2"]
            ingredients = [item.strip() for item in data if item and isinstance(item, str)]
        elif isinstance(data[0], dict):
            # [{"ingredient": "..."}, {"name": "..."}]
            for item in data:
                ingredient = _extract_ingredient_from_object(item)
                if ingredient:
                    ingredients.append(ingredient)
    
    # Case 2: Object with ingredients/data key
    elif isinstance(data, dict):
        # Try "ingredients" key
        if "ingredients" in data:
            items = data["ingredients"]
            if isinstance(items, list):
                if items and isinstance(items[0], str):
                    ingredients = [item.strip() for item in items if item]
                elif items and isinstance(items[0], dict):
                    for item in items:
                        ingredient = _extract_ingredient_from_object(item)
                        if ingredient:
                            ingredients.append(ingredient)
        
        # Try "data" key
        elif "data" in data:
            items = data["data"]
            if isinstance(items, list):
                for item in items:
                    ingredient = _extract_ingredient_from_object(item)
                    if ingredient:
                        ingredients.append(ingredient)
        
        # Try root-level array keys
        else:
            for key in ["items", "foods", "names", "list"]:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    if items and isinstance(items[0], str):
                        ingredients = [item.strip() for item in items if item]
                        break
                    elif items and isinstance(items[0], dict):
                        for item in items:
                            ingredient = _extract_ingredient_from_object(item)
                            if ingredient:
                                ingredients.append(ingredient)
                        break
    
    return ingredients


def _extract_ingredient_from_object(obj: dict) -> Optional[str]:
    """
    Extract ingredient name from object.
    Looks for 'ingredient', 'name', 'food', or 'item' field.
    
    Args:
        obj: Dictionary object
    
    Returns:
        Ingredient name or None
    """
    if not isinstance(obj, dict):
        return None
    
    # Try common field names (case-insensitive)
    for field in ['ingredient', 'name', 'food', 'item', 'ingredients']:
        for key in obj.keys():
            if key.lower() == field.lower():
                value = obj[key]
                if value and isinstance(value, str):
                    return value.strip()
    
    return None


def load_json(file_path: str) -> dict:
    """
    Load JSON file.
    
    Args:
        file_path: Path to JSON file
    
    Returns:
        Dictionary from JSON file
    """
    import json
    
    # Try multiple possible paths
    possible_paths = [
        file_path,
        f"../nutrition_usda/{file_path}",
        os.path.join(os.path.dirname(__file__), "..", "..", "nutrition_usda", file_path)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    raise FileNotFoundError(f"Could not find JSON file: {file_path}")


