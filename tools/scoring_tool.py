"""
Scoring Tools for Match Quality Assessment
Enhanced with advanced relevance scoring from usda_api_new_tool.py
"""

from typing import Dict, List, Tuple, Optional, Any


def score_match_quality(food_item: Dict, ingredient: str, search_intent: Optional[Dict] = None) -> Tuple[int, int, str]:
    """
    Score a food item match quality for an ingredient.
    
    Args:
        food_item: Food item from USDA API search results
        ingredient: Original ingredient name
        search_intent: Optional search intent from LLM (contains avoid words, preferred form, etc.)
    
    Returns:
        Tuple of (base_score, type_score, description):
        - base_score: Lower is better (0 = perfect match, higher = worse match)
        - type_score: Data type priority (0 = Foundation, 1 = SR Legacy, 2 = Branded)
        - description: Food description
    
    Scoring Strategy:
    1. Ingredient should be PRIMARY subject (first word or first word before comma)
    2. Prefer simpler descriptions (fewer words = more likely pure ingredient)
    3. Penalize compound foods (multiple primary ingredients)
    4. Prefer Foundation foods (more standardized)
    5. Apply penalties based on LLM intent (avoid words, etc.)
    """
    description = food_item.get("description", "").strip()
    description_lower = description.lower()
    ingredient_lower = ingredient.lower()
    ingredient_words = set(ingredient_lower.split())
    data_type = food_item.get("dataType", "")
    
    # Data type priority: Foundation > SR Legacy > Branded
    type_score = 0 if data_type == "Foundation" else (1 if data_type == "SR Legacy" else 2)
    
    # Parse description into words
    desc_words = [w.rstrip(',') for w in description_lower.split()]
    desc_words_set = set(desc_words)
    word_count = len(desc_words)
    
    # Base score starts at 0 (best), increases with penalties
    base_score = 0
    
    # Get first word
    first_word = desc_words[0] if desc_words else ""
    second_word = desc_words[1] if len(desc_words) > 1 else ""
    
    # Check if ingredient is at the start
    if first_word in ingredient_words:
        # Good match - ingredient is first word
        base_score += 0
    elif first_word not in ingredient_words:
        # Check if first word is plural/singular form
        first_word_is_plural_form = False
        for ing_word in ingredient_words:
            if first_word == ing_word + 's' or first_word == ing_word + 'es':
                first_word_is_plural_form = True
                break
            if ing_word.endswith('y') and first_word == ing_word[:-1] + 'ies':
                first_word_is_plural_form = True
                break
            if ing_word.endswith('s') and first_word == ing_word[:-1]:
                first_word_is_plural_form = True
                break
        
        if first_word_is_plural_form:
            base_score += 0  # No penalty for plural/singular variations
        else:
            base_score += 50  # Penalty for ingredient not at start
    
    # Apply LLM intent penalties if available
    if search_intent:
        avoid_words = search_intent.get("avoid", [])
        for avoid_word in avoid_words:
            if isinstance(avoid_word, str) and len(avoid_word) >= 3:
                avoid_word_lower = avoid_word.lower()
                if avoid_word_lower in description_lower:
                    # Check if avoid word appears in first 3 words
                    words_in_desc = description_lower.split()
                    first_3_words = [w.rstrip(',') for w in words_in_desc[:3]]
                    if avoid_word_lower in first_3_words:
                        # Check if ingredient appears before avoid word
                        ingredient_in_first_3 = any(word in first_3_words for word in ingredient_words)
                        avoid_pos = first_3_words.index(avoid_word_lower) if avoid_word_lower in first_3_words else -1
                        
                        if avoid_pos >= 0:
                            ingredient_positions = [i for i, w in enumerate(first_3_words) 
                                                   if any(word in w for word in ingredient_words)]
                            if ingredient_positions and min(ingredient_positions) < avoid_pos:
                                continue  # Ingredient before avoid word = OK (modifier)
                            elif avoid_pos == 0 and not ingredient_in_first_3:
                                base_score += 200  # Very heavy penalty - wrong match
                            elif not ingredient_in_first_3:
                                base_score += 200  # Very heavy penalty - wrong match
    
    # Penalty for compound foods (indicated by "and", "with", "&")
    conjunction_words = ["and", "with", "&", "+"]
    has_conjunction = any(conj in desc_words for conj in conjunction_words)
    if has_conjunction:
        early_words = desc_words[:3]
        if any(conj in early_words for conj in conjunction_words):
            # Check if it's nutritional context (OK) or compound food (bad)
            nutritional_context = any(word in description_lower for word in 
                                    ["vitamin", "added", "%", "milkfat", "fat", "protein", "calcium"])
            if not ("with" in early_words and nutritional_context):
                base_score += 150  # Very heavy penalty - compound food
    
    # Penalty for long descriptions (likely processed/composite foods)
    if "," in description_lower:
        parts = description_lower.split(",", 1)
        modifier_part = parts[1].strip()
        modifier_words = modifier_part.split()
        modifier_word_count = len(modifier_words)
        
        if modifier_word_count > 6:
            nutritional_indicators = {"vitamin", "added", "%", "milkfat", "fat", "fluid", "with", "and"}
            has_nutritional_info = any(ind in modifier_part for ind in nutritional_indicators)
            if not has_nutritional_info:
                base_score += 50  # Penalty for very long modifiers
    
    return (base_score, type_score, description)


def _score_relevance_advanced(food: Dict[str, Any], query: str, position: int) -> float:
    """
    Advanced relevance scoring (higher is better).
    Enhanced version with position-based scoring, exact match bonuses,
    compound food detection, and processed form penalties.
    
    Args:
        food: Food item from USDA API
        query: Original search query
        position: Position in the API results (0 = first, most relevant)
    
    Returns:
        Relevance score (higher is better, typically 200-2000 range)
    """
    description = food.get("description", "").lower()
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    score = 1000.0  # Base score
    
    # Position penalty (API orders by relevance, so earlier is better)
    score -= position * 10
    
    # Exact match bonus (huge boost)
    if description == query_lower:
        score += 500
    # Starts with query (very good match)
    elif description.startswith(query_lower):
        score += 300
    # Starts with main ingredient word (good match for "Milk, whole" when query is "whole milk")
    # For multi-word queries, the last word is often the main ingredient
    query_word_list = query_lower.split()
    main_ingredient = query_word_list[-1] if query_word_list else ""
    if main_ingredient and description.startswith(main_ingredient):
        score += 250
        # If it also contains the full query phrase, give additional bonus
        if query_lower in description:
            score += 100
    # Exact phrase match (only if didn't already match above)
    elif query_lower in description:
        score += 200
    
    # Word-level matching
    desc_words = set(description.replace(",", " ").split())
    matching_words = query_words.intersection(desc_words)
    if matching_words:
        # All query words present (excellent)
        if matching_words == query_words:
            score += 150
        else:
            # Partial word match
            score += len(matching_words) * 30
    
    # Penalize compound foods when searching for base ingredients
    # If query is simple (1-2 words) but description is complex (3+ words), penalize
    query_word_count = len(query_words)
    desc_words_list = description.replace(",", " ").split()
    desc_word_count = len(desc_words_list)
    
    # Common compound food indicators to penalize (especially when they start the description)
    compound_indicators = ["cheese", "crackers", "bread", "cookies", "cake", 
                          "soup", "sauce", "dressing", "cereal", "bar", "drink",
                          "juice", "spread", "butter", "yogurt"]
    
    # Processed/preserved forms to penalize when searching for fresh/liquid
    processed_forms = ["dry", "powdered", "powder", "dehydrated", "canned", "frozen", 
                       "concentrated", "evaporated", "condensed"]
    
    if query_word_count <= 2:  # Simple query (e.g., "whole milk", "apple")
        # Strongly penalize if description STARTS with compound indicators
        # This indicates a processed food MADE WITH the ingredient, not the ingredient itself
        first_word = desc_words_list[0] if desc_words_list else ""
        if first_word in compound_indicators:
            score -= 800  # Heavy penalty for starting with compound food
        
        # Also penalize if compound indicator appears anywhere
        elif any(indicator in description for indicator in compound_indicators):
            score -= 500  # Increased penalty
        
        # Penalize processed/preserved forms when searching for fresh/liquid (unless query specifies it)
        # For "whole milk", prefer liquid over "dry milk" or "powdered milk"
        if not any(form in query_lower for form in processed_forms):
            if any(form in description for form in processed_forms):
                score -= 300  # Penalize processed forms when searching for fresh
        
        # Penalize if description is much longer than query (likely a compound food)
        if desc_word_count > query_word_count + 1:
            score -= 150  # Increased penalty
    
    # Data type priority (Foundation > SR Legacy > Survey > Branded > others)
    # Comprehensive 4-tier search: Tier 1 (Foundation,SR Legacy) > Tier 2 (Survey) > Tier 3 (Branded) > Tier 4 (All types)
    data_type = food.get("dataType", "")
    if data_type == "Foundation":
        score += 100
    elif data_type == "SR Legacy":
        score += 50
    elif data_type == "Survey (FNDDS)":
        score += 25
    elif data_type == "Branded":
        score -= 50  # Penalty for Branded products (Tier 3) - available but deprioritized
    
    # Food category relevance (e.g., searching "milk" should prefer "Dairy" category)
    food_category_obj = food.get("foodCategory", {})
    if isinstance(food_category_obj, dict):
        food_category = food_category_obj.get("description", "").lower()
    elif isinstance(food_category_obj, str):
        food_category = food_category_obj.lower()
    else:
        food_category = ""
    
    if "milk" in query_lower and "dairy" in food_category:
        score += 50
    if "fruit" in query_lower and "fruit" in food_category:
        score += 50
    
    return score


def score_match_quality_enhanced(food_item: Dict, ingredient: str, position: int = 0, 
                                 search_intent: Optional[Dict] = None) -> Tuple[int, int, str]:
    """
    Enhanced scoring that combines advanced relevance scoring with existing logic.
    Uses the advanced _score_relevance_advanced() function and converts to lower-is-better format.
    
    Args:
        food_item: Food item from USDA API search results
        ingredient: Original ingredient name
        position: Position in search results (0 = first)
        search_intent: Optional search intent from LLM (contains avoid words, preferred form, etc.)
    
    Returns:
        Tuple of (base_score, type_score, description):
        - base_score: Lower is better (converted from higher-is-better relevance score)
        - type_score: Data type priority (0 = Foundation, 1 = SR Legacy, 2 = Branded)
        - description: Food description
    """
    # Get advanced relevance score (higher is better)
    relevance_score = _score_relevance_advanced(food_item, ingredient, position)
    
    # Convert to lower-is-better format (invert: higher relevance = lower penalty)
    # Normalize: 2000 (excellent) -> 0, 0 (poor) -> 2000
    # Typical range: 200-2000, so we'll use 2000 as max
    max_possible_score = 2000.0
    base_score = int(max_possible_score - relevance_score)
    
    # Apply LLM intent penalties if available
    if search_intent:
        avoid_words = search_intent.get("avoid", [])
        description_lower = food_item.get("description", "").lower()
        ingredient_lower = ingredient.lower()
        ingredient_words = set(ingredient_lower.split())
        
        for avoid_word in avoid_words:
            if isinstance(avoid_word, str) and len(avoid_word) >= 3:
                avoid_word_lower = avoid_word.lower()
                if avoid_word_lower in description_lower:
                    # Check if avoid word appears in first 3 words
                    words_in_desc = description_lower.split()
                    first_3_words = [w.rstrip(',') for w in words_in_desc[:3]]
                    if avoid_word_lower in first_3_words:
                        # Check if ingredient appears before avoid word
                        ingredient_in_first_3 = any(word in first_3_words for word in ingredient_words)
                        avoid_pos = first_3_words.index(avoid_word_lower) if avoid_word_lower in first_3_words else -1
                        
                        if avoid_pos >= 0:
                            ingredient_positions = [i for i, w in enumerate(first_3_words) 
                                                   if any(word in w for word in ingredient_words)]
                            if not (ingredient_positions and min(ingredient_positions) < avoid_pos):
                                if avoid_pos == 0 and not ingredient_in_first_3:
                                    base_score += 200  # Very heavy penalty - wrong match
                                elif not ingredient_in_first_3:
                                    base_score += 200  # Very heavy penalty - wrong match
    
    # Data type priority: Foundation > SR Legacy > Branded
    data_type = food_item.get("dataType", "")
    type_score = 0 if data_type == "Foundation" else (1 if data_type == "SR Legacy" else 2)
    
    description = food_item.get("description", "").strip()
    
    return (base_score, type_score, description)


def filter_search_results(search_results: List[Dict], ingredient: str, 
                          max_score: int = 50, use_enhanced: bool = True) -> List[Tuple[Tuple[int, int, str], Dict]]:
    """
    Filter and score search results, returning ranked list.
    
    Args:
        search_results: List of food items from USDA API
        ingredient: Original ingredient name
        max_score: Maximum acceptable base score (default 50)
        use_enhanced: If True, use enhanced scoring with advanced relevance logic (default: True)
    
    Returns:
        List of tuples: ((base_score, type_score, description), food_item)
        Sorted by score (lower is better)
    """
    scored_results = []
    
    for idx, result in enumerate(search_results):
        if use_enhanced:
            score = score_match_quality_enhanced(result, ingredient, position=idx)
        else:
            score = score_match_quality(result, ingredient)
        
        base_score, type_score, description = score
        
        # Filter out very poor matches
        # For enhanced scoring, max_score needs to be adjusted (higher threshold since scores are inverted)
        if use_enhanced:
            # Enhanced scores are inverted (lower = better), so we need a higher threshold
            # Typical good scores: 0-500, poor scores: 1500-2000
            threshold = max(1500, 2000 - max_score * 20)  # Convert max_score to enhanced scale
            if base_score < threshold:
                scored_results.append((score, result))
        else:
            if base_score < max_score or base_score == 0:
                scored_results.append((score, result))
    
    # Sort by score (base_score first, then type_score)
    scored_results.sort(key=lambda x: (x[0][0], x[0][1]))
    
    return scored_results

