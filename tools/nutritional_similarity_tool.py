"""
Nutritional Similarity Scoring Tool - Compares nutritional values using LLM + web search
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
import httpx
from tools.usda_api_tool import get_usda_food_details
from tools.nutrition_extractor_tool import extract_nutrition_data


# Priority weights for nutritional attributes (based on general importance)
NUTRIENT_WEIGHTS = {
    "calories": 0.15,
    "calories_from_fat": 0.05,
    "total_fat_g": 0.10,
    "saturated_fat_g": 0.08,
    "trans_fat_g": 0.05,
    "polyunsaturated_fat_g": 0.05,
    "monounsaturated_fat_g": 0.05,
    "cholesterol_mg": 0.05,
    "sodium_mg": 0.08,
    "total_carbs_g": 0.10,
    "dietary_fiber_g": 0.08,
    "total_sugars_g": 0.05,
    "added_sugars_g": 0.03,
    "sugar_alcohols_g": 0.02,
    "protein_g": 0.12,
    "vitamin_a_mcg": 0.03,
    "vitamin_c_mg": 0.03,
    "vitamin_d_mcg": 0.02,
    "calcium_mg": 0.05,
    "iron_mg": 0.05,
    "potassium_mg": 0.05,
}


def _extract_basic_nutrients(nutrition_data: Dict) -> Dict:
    """Extract basic nutritional values from nutrition data"""
    standardized = nutrition_data.get("standardized_nutrients", {})
    common = nutrition_data.get("common_nutrients", {})
    
    # Map standardized nutrients to basic format
    nutrients = {}
    
    # Calories
    cal_data = standardized.get("nutrient-calories-energy")
    if cal_data and cal_data.get("amount"):
        # Convert kJ to kcal if needed
        amount = cal_data["amount"]
        unit = cal_data.get("unit", "").lower()
        if "kj" in unit:
            nutrients["calories"] = amount / 4.184  # Convert kJ to kcal
        else:
            nutrients["calories"] = amount
    
    # Protein
    protein_data = standardized.get("nutrient-protein")
    if protein_data and protein_data.get("amount"):
        nutrients["protein_g"] = protein_data["amount"]
    
    # Total Fat
    fat_data = standardized.get("nutrient-total-fat")
    if fat_data and fat_data.get("amount"):
        nutrients["total_fat_g"] = fat_data["amount"]
    
    # Saturated Fat
    sat_fat_data = standardized.get("nutrient-saturated-fat")
    if sat_fat_data and sat_fat_data.get("amount"):
        nutrients["saturated_fat_g"] = sat_fat_data["amount"]
    
    # Trans Fat
    trans_fat_data = standardized.get("nutrient-trans-fat")
    if trans_fat_data and trans_fat_data.get("amount"):
        nutrients["trans_fat_g"] = trans_fat_data["amount"]
    
    # Polyunsaturated Fat
    pufa_data = standardized.get("nutrient-polyunsaturated-fat")
    if pufa_data and pufa_data.get("amount"):
        nutrients["polyunsaturated_fat_g"] = pufa_data["amount"]
    
    # Monounsaturated Fat
    mufa_data = standardized.get("nutrient-monounsaturated-fat")
    if mufa_data and mufa_data.get("amount"):
        nutrients["monounsaturated_fat_g"] = mufa_data["amount"]
    
    # Cholesterol
    chol_data = standardized.get("nutrient-cholesterol")
    if chol_data and chol_data.get("amount"):
        nutrients["cholesterol_mg"] = chol_data["amount"]
    
    # Sodium
    sodium_data = standardized.get("nutrient-sodium")
    if sodium_data and sodium_data.get("amount"):
        nutrients["sodium_mg"] = sodium_data["amount"]
    
    # Total Carbs
    carbs_data = standardized.get("nutrient-total-carbohydrates")
    if carbs_data and carbs_data.get("amount"):
        nutrients["total_carbs_g"] = carbs_data["amount"]
    
    # Dietary Fiber
    fiber_data = standardized.get("nutrient-dietary-fiber")
    if fiber_data and fiber_data.get("amount"):
        nutrients["dietary_fiber_g"] = fiber_data["amount"]
    
    # Total Sugars
    sugar_data = standardized.get("nutrient-total-sugars")
    if sugar_data and sugar_data.get("amount"):
        nutrients["total_sugars_g"] = sugar_data["amount"]
    
    # Added Sugars (may not be available)
    # Total Carbs - Fiber - Sugar Alcohols - Natural Sugars ≈ Added Sugars (approximation)
    
    # Vitamin A
    vit_a_data = standardized.get("nutrient-vitamin-a-rae")
    if vit_a_data and vit_a_data.get("amount"):
        nutrients["vitamin_a_mcg"] = vit_a_data["amount"]
    
    # Vitamin C
    vit_c_data = standardized.get("nutrient-vitamin-c-ascorbic-acid")
    if vit_c_data and vit_c_data.get("amount"):
        nutrients["vitamin_c_mg"] = vit_c_data["amount"]
    
    # Vitamin D
    vit_d_data = standardized.get("nutrient-vitamin-d")
    if vit_d_data and vit_d_data.get("amount"):
        nutrients["vitamin_d_mcg"] = vit_d_data["amount"]
    
    # Calcium
    calcium_data = standardized.get("nutrient-calcium")
    if calcium_data and calcium_data.get("amount"):
        nutrients["calcium_mg"] = calcium_data["amount"]
    
    # Iron
    iron_data = standardized.get("nutrient-iron")
    if iron_data and iron_data.get("amount"):
        nutrients["iron_mg"] = iron_data["amount"]
    
    # Potassium
    potassium_data = standardized.get("nutrient-potassium")
    if potassium_data and potassium_data.get("amount"):
        nutrients["potassium_mg"] = potassium_data["amount"]
    
    # Calculate calories_from_fat (approximation)
    if nutrients.get("total_fat_g"):
        nutrients["calories_from_fat"] = nutrients["total_fat_g"] * 9
    
    return nutrients


def _calculate_nutritional_similarity(ingredient_nutrients: Dict, usda_nutrients: Dict) -> Tuple[float, str]:
    """
    Calculate nutritional similarity score between ingredient and USDA result.
    
    Returns:
        Tuple of (similarity_score 0-100, reasoning)
    """
    if not ingredient_nutrients or not usda_nutrients:
        return 0.0, "Missing nutritional data for comparison"
    
    total_weight = 0.0
    weighted_score = 0.0
    differences = []
    
    for nutrient, weight in NUTRIENT_WEIGHTS.items():
        ing_value = ingredient_nutrients.get(nutrient)
        usda_value = usda_nutrients.get(nutrient)
        
        # Skip if both are missing
        if ing_value is None and usda_value is None:
            continue
        
        # If one is missing, penalize
        if ing_value is None or usda_value is None:
            # Use lower weight for missing values
            weighted_score += weight * 0.3  # 30% score for missing
            total_weight += weight
            differences.append(f"{nutrient}: missing in one")
            continue
        
        # Calculate percentage difference
        if ing_value == 0 and usda_value == 0:
            # Both zero = perfect match
            similarity = 1.0
        elif ing_value == 0 or usda_value == 0:
            # One is zero, other is not = poor match
            similarity = 0.2
        else:
            # Calculate relative difference
            diff = abs(ing_value - usda_value)
            avg = (ing_value + usda_value) / 2
            relative_diff = diff / avg if avg > 0 else 1.0
            
            # Convert to similarity (0-1)
            # 0% diff = 100% similar, 100% diff = 0% similar
            similarity = max(0, 1 - min(relative_diff, 2.0))  # Cap at 200% difference
        
        weighted_score += weight * similarity
        total_weight += weight
        
        if relative_diff > 0.3:  # >30% difference
            differences.append(f"{nutrient}: {relative_diff*100:.1f}% diff")
    
    if total_weight == 0:
        return 0.0, "No comparable nutrients found"
    
    final_score = (weighted_score / total_weight) * 100
    
    reasoning = f"Similarity: {final_score:.1f}%"
    if differences:
        reasoning += f". Notable differences: {', '.join(differences[:3])}"
    
    return final_score, reasoning


def get_expected_ingredient_nutrition(ingredient: str) -> Optional[Dict]:
    """
    Get expected nutritional values for an ingredient using LLM + web knowledge.
    This represents typical values for the ingredient.
    """
    client = _get_llm_client()
    if not client:
        return None
    
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    
    prompt = f"""You are a nutrition expert. Research and provide typical nutritional values for "{ingredient}" per 100g.

Consider:
- Common form (raw, cooked, etc.)
- Typical variety/type
- Standard preparation

Return JSON with nutritional values (use null if not applicable):
{{
    "calories": <kcal>,
    "protein_g": <g>,
    "total_fat_g": <g>,
    "saturated_fat_g": <g>,
    "total_carbs_g": <g>,
    "dietary_fiber_g": <g>,
    "total_sugars_g": <g>,
    "sodium_mg": <mg>,
    "calcium_mg": <mg>,
    "iron_mg": <mg>,
    "vitamin_a_mcg": <mcg>,
    "vitamin_c_mg": <mg>,
    "vitamin_d_mcg": <mcg>,
    "potassium_mg": <mg>
}}

Use web knowledge and typical values. Return only valid JSON."""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            timeout=90.0
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"  Error getting expected nutrition: {e}")
        return None


def calculate_nutritional_similarity_score(ingredient: str, usda_results: List[Dict], 
                                           top_n: int = 3) -> List[Dict]:
    """
    Calculate nutritional similarity scores for top USDA results.
    Uses LLM for heavy reasoning on nutritional comparisons.
    
    Args:
        ingredient: Original ingredient name
        usda_results: List of USDA search results (already semantically verified)
        top_n: Number of top results to analyze
    
    Returns:
        List of results with nutritional_similarity_score and detailed reasoning
    """
    client = _get_llm_client()
    if not client:
        # Fallback: calculate basic similarity without LLM reasoning
        return _calculate_basic_similarity(ingredient, usda_results, top_n)
    
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    
    # Get expected nutrition values for ingredient
    expected_nutrition = get_expected_ingredient_nutrition(ingredient)
    
    # Fetch nutrition data for top results
    results_with_nutrition = []
    for result in usda_results[:top_n]:
        fdc_id = result.get("fdcId")
        if not fdc_id:
            continue
        
        food_data = get_usda_food_details(fdc_id)
        if food_data:
            nutrition_data = extract_nutrition_data(food_data)
            if nutrition_data:
                nutrients = _extract_basic_nutrients(nutrition_data)
                results_with_nutrition.append({
                    "fdc_id": fdc_id,
                    "description": result.get("description", ""),
                    "nutrients": nutrients,
                    "nutrition_data": nutrition_data
                })
    
    if not results_with_nutrition:
        return []
    
    # Prepare prompt for LLM reasoning
    expected_text = ""
    if expected_nutrition:
        expected_str = ", ".join([f"{k}: {v}" for k, v in expected_nutrition.items() if v is not None])
        expected_text = f"\nEXPECTED VALUES for '{ingredient}' (per 100g): {expected_str}\n"
    
    nutrients_text = []
    for i, r in enumerate(results_with_nutrition, 1):
        nutrients_str = ", ".join([f"{k}: {v:.2f}" for k, v in r["nutrients"].items() if v is not None])
        nutrients_text.append(f"{i}. {r['description']} (FDC {r['fdc_id']}): {nutrients_str}")
    
    prompt = f"""You are a nutrition expert. Analyze nutritional similarity between an ingredient and USDA food results.

INGREDIENT: "{ingredient}"
{expected_text}
USDA FOOD RESULTS WITH NUTRITIONAL VALUES (per 100g):
{chr(10).join(nutrients_text)}

TASK:
1. Compare each USDA result's nutritional profile with expected values for "{ingredient}"
2. Calculate similarity scores (0-100) based on:
   - Core macronutrients (calories, protein, carbs, fat) - HIGH WEIGHT (40%)
   - Key vitamins/minerals (vitamin A, C, D, calcium, iron, potassium) - MEDIUM WEIGHT (30%)
   - Other nutrients - LOWER WEIGHT (30%)
3. Consider acceptable variations (e.g., raw vs cooked, different varieties)
4. Use heavy reasoning: analyze each nutrient difference and its significance

Return JSON array with:
{{
    "rank": 1-{top_n},
    "fdc_id": <FDC ID>,
    "nutritional_similarity_score": 0-100,
    "reasoning": "<detailed explanation of nutritional comparison with heavy reasoning on each nutrient difference>",
    "key_differences": ["<nutrient1>: <difference>", "<nutrient2>: <difference>"]
}}

Only include results where nutritional_similarity_score >= 50. 
Thresholds:
- 90-100%: HIGH_CONFIDENCE (excellent match)
- 80-89%: MID_CONFIDENCE (good match)
- Below 80%: LOW_CONFIDENCE (poor match, will be rejected)"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns only valid JSON arrays. Use web search knowledge for typical nutritional values."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Slight temperature for reasoning
            timeout=120.0
        )
        
        content = response.choices[0].message.content
        similarity_results = json.loads(content)
        
        if not isinstance(similarity_results, list):
            similarity_results = [similarity_results] if similarity_results else []
        
        # Merge with original results (preserve semantic_match_score from verified_results)
        fdc_id_map = {str(r["fdc_id"]): r for r in results_with_nutrition}
        # Also need to preserve semantic scores from verified_results
        verified_fdc_map = {}
        for v_result in usda_results:
            fdc_id = str(v_result.get("fdcId", ""))
            if fdc_id:
                verified_fdc_map[fdc_id] = v_result.get("semantic_match_score", 0)
        
        final_results = []
        
        for sim_result in similarity_results:
            fdc_id = str(sim_result.get("fdc_id", ""))
            if fdc_id in fdc_id_map:
                original = fdc_id_map[fdc_id]
                original["nutritional_similarity_score"] = sim_result.get("nutritional_similarity_score", 0)
                original["nutritional_reasoning"] = sim_result.get("reasoning", "")
                original["key_differences"] = sim_result.get("key_differences", [])
                # Preserve semantic_match_score from verified results
                if fdc_id in verified_fdc_map:
                    original["semantic_match_score"] = verified_fdc_map[fdc_id]
                final_results.append(original)
        
        # Sort by nutritional similarity score
        final_results.sort(key=lambda x: x.get("nutritional_similarity_score", 0), reverse=True)
        
        return final_results
    
    except Exception as e:
        print(f"  LLM nutritional similarity error: {e}")
        # Fallback to basic calculation
        return _calculate_basic_similarity(ingredient, usda_results, top_n)


def _calculate_basic_similarity(ingredient: str, usda_results: List[Dict], top_n: int) -> List[Dict]:
    """Fallback: Calculate basic similarity without LLM"""
    results_with_scores = []
    
    for result in usda_results[:top_n]:
        fdc_id = result.get("fdcId")
        if not fdc_id:
            continue
        
        food_data = get_usda_food_details(fdc_id)
        if food_data:
            nutrition_data = extract_nutrition_data(food_data)
            if nutrition_data:
                nutrients = _extract_basic_nutrients(nutrition_data)
                # Basic score: assume 70% similarity (fallback)
                results_with_scores.append({
                    "fdc_id": fdc_id,
                    "description": result.get("description", ""),
                    "nutritional_similarity_score": 70.0,
                    "nutritional_reasoning": "Basic similarity calculation (LLM unavailable)",
                    "nutrients": nutrients,
                    "nutrition_data": nutrition_data
                })
    
    return results_with_scores


def _get_llm_client() -> Optional[OpenAI]:
    """Get or create OpenAI client instance"""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    
    if not api_key:
        return None
    
    try:
        if base_url:
            base_url = base_url.rstrip('/')
        
        http_client = None
        if httpx:
            http_client = httpx.Client(
                timeout=httpx.Timeout(120.0, connect=15.0),
                verify=True
            )
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None,
            http_client=http_client,
            max_retries=2
        )
        return client
    except Exception as e:
        return None

