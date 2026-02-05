"""
LLM Tools for Search Intent Generation
"""

import os
import json
from typing import Dict, Optional
from openai import OpenAI
import httpx

# Try to import OpenAI
try:
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("Warning: OpenAI library not installed. LLM features disabled.")


def _get_llm_client() -> Optional[OpenAI]:
    """Get or create OpenAI client instance"""
    if not LLM_AVAILABLE:
        return None
    
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
                timeout=httpx.Timeout(30.0, connect=10.0),
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
        print(f"Warning: Could not initialize LLM client: {e}")
        return None


def generate_search_intent(ingredient: str) -> Optional[Dict]:
    """
    Generate search intent for an ingredient using LLM.
    
    Args:
        ingredient: Ingredient name to analyze
    
    Returns:
        Search intent dictionary:
        {
            "search_query": str,
            "is_phrase": bool,
            "preferred_form": str,
            "avoid": List[str],
            "expected_pattern": str
        }
    """
    client = _get_llm_client()
    if not client:
        return None
    
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    
    prompt = f"""You are a nutrition database expert. Analyze this ingredient and generate search intent for USDA FoodData Central API keyword search.

Ingredient: "{ingredient}"

SEMANTIC UNDERSTANDING:
- "black pepper" = spice (pepper that is black), belongs to spices category. USDA format: "Spices, pepper, black" or "Pepper, black"
- "onion" = vegetable, can be yellow/red/white onion (VALID color types). USDA format: "Onions, raw" or "Onions, yellow"
- "vegetable oil" = generic cooking oil. USDA format: "Oil, vegetable" or "Vegetable oil"
- Color/type AFTER ingredient = VALID modifier (e.g., "Onions, yellow" for "onion")
- Color/type BEFORE ingredient = DIFFERENT variety (e.g., "Green onion" is different from "onion")

USDA API uses keyword search - generate search_query that will return the ingredient itself, not unrelated items.

Return JSON with 5 fields:

1. search_query: Best search terms for USDA keyword search. Be strategic:
   - For "black pepper": use "pepper black" or "spices pepper" (helps find spice category)
   - For "onion": use "onions raw" (plural + form narrows results)
   - For "vegetable oil": use "vegetable oil" (keep as phrase)
   - Goal: Terms that return the actual ingredient, not items containing the word

2. is_phrase: true if multi-word is a compound name (oils, spices). false for single words.

3. preferred_form: Standard form (dairy→"whole", produce→"raw"). Empty if no preference.

4. avoid: Words indicating WRONG matches. Key distinctions:
   - For "onion": Avoid "green", "scallion", "shallot" (different varieties) BUT allow "yellow", "red", "white" (valid color types)
   - For "black pepper": Avoid "beans", "bell pepper" (different items)
   - For animal products: Avoid plant-based alternatives
   - Avoid processed forms when raw expected
   - Avoid compound foods containing ingredient
   - CRITICAL: Color/type words AFTER ingredient are VALID (e.g., "yellow" in "Onions, yellow")
   - Color/type words BEFORE ingredient are NOT OK (e.g., "green" in "Green onion")

5. expected_pattern: Expected USDA description format:
   - "black pepper" → "Spices, pepper, black" or "Pepper, black"
   - "onion" → "Onions, raw" or "Onions, yellow"
   - "vegetable oil" → "Oil, vegetable"

Return ONLY valid JSON."""

    try:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that returns only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                timeout=60.0,
                response_format={"type": "json_object"}
            )
        except Exception as format_error:
            if "response_format" in str(format_error).lower() or "400" in str(format_error):
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that returns only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    timeout=60.0
                )
            else:
                raise format_error
        
        content = response.choices[0].message.content
        intent = json.loads(content)
        
        # Validate and normalize intent
        search_query = intent.get("search_query", ingredient)
        if isinstance(search_query, list):
            search_query = search_query[0] if search_query else ingredient
        if not isinstance(search_query, str):
            search_query = str(search_query)
        search_query = search_query.strip().strip('"').strip("'")
        
        return {
            "search_query": search_query if search_query else ingredient,
            "is_phrase": intent.get("is_phrase", False),
            "preferred_form": intent.get("preferred_form", ""),
            "avoid": intent.get("avoid", []),
            "expected_pattern": intent.get("expected_pattern", "")
        }
    except Exception as e:
        print(f"  LLM error: {e}")
        return None

