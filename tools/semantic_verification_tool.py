"""
Semantic Verification Tool - Uses LLM to verify if USDA results match ingredient semantically
Enhanced with caching and improved prompt for form variations
"""

import os
import json
from typing import Dict, List, Optional
from openai import OpenAI
import httpx
from tools.cache_tool import get_cached_search_intent, save_search_intent_cache


def _get_llm_client() -> Optional[OpenAI]:
    """Get or create OpenAI client instance"""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    
    if not api_key:
        return None
    
    try:
        if base_url:
            base_url = base_url.rstrip('/')
        
        http_client = None
        if httpx:
            http_client = httpx.Client(
                timeout=httpx.Timeout(60.0, connect=15.0),
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
        print(f"  Warning: Could not initialize LLM client: {e}")
        return None


# Cache for semantic scores to ensure consistency
_semantic_score_cache = {}

def _get_cached_semantic_score(ingredient: str, fdc_id: str) -> Optional[float]:
    """Get cached semantic score for ingredient+FDC ID pair"""
    cache_key = f"{ingredient.lower()}|{fdc_id}"
    return _semantic_score_cache.get(cache_key)

def _cache_semantic_score(ingredient: str, fdc_id: str, score: float):
    """Cache semantic score for ingredient+FDC ID pair"""
    cache_key = f"{ingredient.lower()}|{fdc_id}"
    _semantic_score_cache[cache_key] = score


def verify_semantic_match(ingredient: str, usda_results: List[Dict], top_n: int = 3) -> List[Dict]:
    """
    Use LLM to verify semantic meaning of ingredient vs USDA results.
    Returns top N results that semantically match the ingredient.
    Enhanced with caching and improved prompt for form variations.
    
    Args:
        ingredient: Original ingredient name
        usda_results: List of USDA search results
        top_n: Number of top results to return
    
    Returns:
        List of verified results with semantic_match_score (0-100)
    """
    client = _get_llm_client()
    if not client:
        # Fallback: return top results without verification
        return usda_results[:top_n]
    
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    
    # Prepare results for LLM analysis (analyze top 80 for comprehensive coverage)
    # Comprehensive 4-tier search returns up to 80 results (30+20+20+10)
    results_text = []
    fdc_id_list = []
    for i, result in enumerate(usda_results[:80], 1):  # Analyze top 80 (comprehensive 4-tier search)
        desc = result.get("description", "")
        fdc_id = result.get("fdcId", "")
        fdc_id_list.append(fdc_id)
        
        # Check cache first
        cached_score = _get_cached_semantic_score(ingredient, str(fdc_id))
        if cached_score is not None:
            # Use cached score, but still include in results
            result["semantic_match_score"] = cached_score
            result["semantic_reasoning"] = "Cached score"
            results_text.append(f"{i}. FDC ID {fdc_id}: {desc} [CACHED: {cached_score:.1f}%]")
        else:
            results_text.append(f"{i}. FDC ID {fdc_id}: {desc}")
    
    results_str = "\n".join(results_text)
    
    prompt = f"""You are a nutrition database expert. Analyze if the USDA food descriptions semantically match the ingredient.

INGREDIENT: "{ingredient}"

USDA SEARCH RESULTS:
{results_str}

CRITICAL RULES:
1. Check SEMANTIC MEANING, not just word similarity
   - "jasmine rice" should match "Rice, jasmine" or "Rice, white, jasmine" but NOT "Rice, black"
   - "green lentils" should match "Lentils, green" but NOT "Green onion" or "Green beans"
   - "vanilla bean" should match vanilla-related items, NOT "Beans, cannellini"

2. **FORM VARIATIONS ARE ACCEPTABLE** - Same ingredient in different forms should score HIGH:
   - "cinnamon sticks" vs "Spices, cinnamon, ground" → Score 85-95% (same ingredient, different form)
   - "kosher salt" vs "Salt, table" → Score 80-90% (same ingredient, different form)
   - "smoked paprika" vs "Spices, paprika" → Score 80-90% (same ingredient, flavor variation)
   - "whole cloves" vs "Spices, cloves, ground" → Score 85-95% (same ingredient, different form)
   - "tzatziki" vs "Tzatziki dip" → Score 90-100% (same item, different naming - Survey (FNDDS) data type)
   - "guacamole" vs "Guacamole, NFS" → Score 90-100% (same item, NFS = Not Further Specified - Survey (FNDDS))
   - "chutney" vs "Chutney" → Score 90-100% (exact match - Survey (FNDDS))
   - "brandy" vs "Brandy" → Score 90-100% (exact match - Survey (FNDDS))

3. **SURVEY (FNDDS) DATA TYPE**: Many prepared foods, dips, sauces are in Survey (FNDDS) data type.
   - These are valid generic foods (not branded products)
   - Items like "Tzatziki dip", "Guacamole, NFS", "Chutney" are in Survey (FNDDS)
   - DO NOT penalize Survey (FNDDS) items - they are legitimate matches

3. Consider ingredient context:
   - Spices: "black pepper" = spice, not bell pepper
   - Varieties: "basmati rice" = specific rice variety, not just any rice
   - Forms: "cocoa powder" = processed cocoa, not raw cacao beans
   - Compound foods: "chickpea pasta" should match pasta made from chickpeas, not just "Chickpea flour"

4. Reject clearly wrong matches:
   - Different food categories (e.g., "green lentils" vs "green onion")
   - Different varieties (e.g., "jasmine rice" vs "black rice")
   - Different base ingredients (e.g., "vanilla bean" vs "cannellini beans")

5. **SCORING GUIDELINES:**
   - 90-100%: Exact match or same item with minor naming/form differences
   - 80-89%: Same ingredient, different form (ground vs whole, kosher vs table salt)
   - 65-79%: Related ingredient, acceptable match (e.g., "smoked paprika" vs "paprika")
   - 50-64%: Related but different (e.g., "fresh oregano" vs "dried oregano")
   - <50%: Different ingredient, reject

Return JSON array with top {top_n} matches, each with:
{{
    "rank": 1-{top_n},
    "fdc_id": <FDC ID>,
    "description": "<USDA description>",
    "semantic_match_score": 0-100 (100 = perfect semantic match, 0 = completely wrong),
    "reasoning": "<brief explanation of why this matches or doesn't match semantically>"
}}

**IMPORTANT:** Include results where semantic_match_score >= 40 (lowered from 50). Be more lenient with form variations. If ingredient exists in results (even with different form), include it with appropriate score."""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            timeout=90.0
        )
        
        content = response.choices[0].message.content
        verified_results = json.loads(content)
        
        if not isinstance(verified_results, list):
            verified_results = [verified_results] if verified_results else []
        
        # Map back to original results
        fdc_id_map = {str(r.get("fdcId", "")): r for r in usda_results}
        verified_with_data = []
        
        for v_result in verified_results:
            fdc_id = str(v_result.get("fdc_id", ""))
            if fdc_id in fdc_id_map:
                original = fdc_id_map[fdc_id]
                score = v_result.get("semantic_match_score", 0)
                original["semantic_match_score"] = score
                original["semantic_reasoning"] = v_result.get("reasoning", "")
                # Cache the score for consistency
                _cache_semantic_score(ingredient, fdc_id, score)
                verified_with_data.append(original)
        
        # Also check if we have any cached scores for results not in LLM response
        for result in usda_results[:80]:
            fdc_id = str(result.get("fdcId", ""))
            cached_score = _get_cached_semantic_score(ingredient, fdc_id)
            if cached_score is not None and cached_score >= 40:
                # Check if already in verified_with_data
                if not any(str(r.get("fdcId", "")) == fdc_id for r in verified_with_data):
                    result["semantic_match_score"] = cached_score
                    result["semantic_reasoning"] = "Cached score from previous attempt"
                    verified_with_data.append(result)
        
        # Sort by semantic match score (descending)
        verified_with_data.sort(key=lambda x: x.get("semantic_match_score", 0), reverse=True)
        
        return verified_with_data[:top_n]
    
    except Exception as e:
        print(f"  LLM semantic verification error: {e}")
        # Fallback: return top results
        return usda_results[:top_n]


