# Current Workflow Rules and Decision Logic

**Last Updated**: January 2026

This document describes the current rules, thresholds, and decision logic used in the CrewAI nutrition workflow.

## Step 3: USDA API Search

### Comprehensive 4-Tier Search Strategy

**Always executes all 4 tiers** (no conditional logic):

1. **Tier 1**: Foundation,SR Legacy - 30 results (preferred generic foods)
2. **Tier 2**: Survey (FNDDS) - 20 results (prepared foods like "Tzatziki dip", "Guacamole, NFS")
3. **Tier 3**: Branded - 20 results (branded products)
4. **Tier 4**: All types - 10 results (catch-all)

**Total**: Up to 80 results, merged, deduplicated, and scored

### Why Comprehensive 4-Tier?
- **Problem**: Items like "Tzatziki dip" (FDC: 2705448) are in `Survey (FNDDS)` data type, NOT `Foundation,SR Legacy`
- **Solution**: Always search all relevant data types to ensure maximum coverage
- **Result**: Better coverage for prepared foods, dips, sauces, condiments, and branded products
- **Enhanced Scoring**: Prioritizes Foundation/SR Legacy but allows Survey/Branded to rank higher if better match

## Step 3.5: Semantic Verification (LLM)

### Purpose
Use LLM to verify if USDA search results semantically match the ingredient (beyond keyword matching).

### Current Behavior
- **Analyzes**: Top 80 search results (matches comprehensive 4-tier search output)
- **Method**: LLM scores each result for semantic match (0-100%)
- **Returns**: Top 3 results with `semantic_match_score >= 40`
- **Caching**: Semantic scores are cached for consistency across retries
- **Temperature**: Set to 0 for more consistent results

### Scoring Guidelines
- **90-100%**: Exact match or same item with minor naming/form differences
  - Example: "tzatziki" → "Tzatziki dip" (90-100%)
  - Example: "guacamole" → "Guacamole, NFS" (90-100%)
  - Example: "chutney" → "Chutney" (90-100%)
- **80-89%**: Same ingredient, different form
  - Example: "cinnamon sticks" → "Spices, cinnamon, ground" (85-95%)
  - Example: "kosher salt" → "Salt, table" (80-90%)
- **65-79%**: Related ingredient, acceptable match
  - Example: "smoked paprika" → "Spices, paprika" (80-90%)
- **50-64%**: Related but different
  - Example: "fresh oregano" → "dried oregano" (50-64%)
- **<50%**: Different ingredient, reject

### Decision Logic Based on Semantic Score

| Semantic Score | Action | Nutritional Threshold | Flag | Mapping Status |
|---------------|--------|----------------------|------|----------------|
| >= 90% | Direct mapping, skip Step 4 & 5 | N/A (skipped) | HIGH_CONFIDENCE | search_verified_semantic_high |
| 80-89% | Proceed to Step 4 & 5 | >= 80% | HIGH_CONFIDENCE or MID_CONFIDENCE | search_verified_high or search_verified_mid |
| 65-79% | Proceed to Step 4 & 5 | >= 90% | MID_CONFIDENCE | search_verified_mid_semantic_low |
| < 65% | **Skip Step 4 & 5**, don't map | N/A (skipped) | NO_MAPPING_FOUND | semantic_score_too_low |

### Changes from Previous Version
- **< 65%**: Now **skips** Step 4 & 5 entirely (previously proceeded but didn't map)
- **65-79%**: New threshold range requiring nutritional >= 90% (previously was 65-89% with >= 80%)
- **80-89%**: Remains the same (nutritional >= 80%)

## Step 4: Nutritional Similarity Scoring (LLM + Web Research)

### Purpose
Compare nutritional profiles to ensure selected USDA items are nutritionally comparable to the input ingredient.

### Current Behavior
1. **Get Expected Values**: LLM + web research to get typical nutritional values for ingredient (per 100g)
2. **Fetch USDA Data**: Get actual nutrition data for top 3 semantically verified results
3. **Compare**: LLM analyzes nutritional similarity with weighted attributes
4. **Score**: Returns `nutritional_similarity_score` (0-100%) with detailed reasoning

### Weighted Attributes
- **Core Macronutrients** (40% weight): calories, protein, carbs, fat
- **Key Vitamins/Minerals** (30% weight): vitamin A, C, D, calcium, iron, potassium
- **Other Nutrients** (30% weight): fiber, sugars, sodium, etc.

### Scoring Thresholds

| Nutritional Score | Confidence Level | Action |
|------------------|------------------|--------|
| >= 90% | HIGH_CONFIDENCE | Excellent match, allow mapping |
| 80-89% | MID_CONFIDENCE | Good match, allow mapping |
| < 80% | LOW_CONFIDENCE | Poor match, reject (unless special case) |

### Special Case
- If semantic score < 65% but nutritional score >= 95%, allow mapping with `LOW_CONFIDENCE` and `mapping_status = "nutritionally_identical_low_semantic"`

## Step 5: Extract Nutrition Data

### Purpose
Extract all 117 standardized nutrients from USDA food data.

### Current Behavior
- Extracts all nutrients from `nutrition_definitions_117.csv`
- Sets missing values to `None` (NULL)
- Standardizes units and formats

## Retry Logic

### Maximum Attempts
- **2 attempts** per ingredient

### Retry Strategies
1. **Attempt 1**: Comprehensive 4-tier search with original LLM-generated query
2. **Attempt 2**: Comprehensive 4-tier search with query variations (alternative strategy)

### Retry Triggers
- No search results found
- No semantically verified matches
- Semantic score too low (< 65%) and nutritional score also low
- Nutritional score below threshold (< 80%) when semantic score is 65-89%

## Output Format

### CSV Columns
- `ingredient`: Original ingredient name
- `flag`: HIGH_CONFIDENCE, MID_CONFIDENCE, LOW_CONFIDENCE, or NO_MAPPING_FOUND
- `mapping_status`: Detailed status (e.g., "search_verified_semantic_high", "search_verified_mid")
- `semantic_match_score`: 0-100% (or None if skipped)
- `nutritional_similarity_score`: 0-100% (or None if skipped)
- `reasoning`: Detailed explanation of mapping decision
- `retry_attempts`: Number of retry attempts (1-3)
- `search_queries_used`: List of search queries tried
- `timestamp`: Processing timestamp
- `processing_time_seconds`: Time taken to process ingredient
- All 117 standardized nutrients (with NULL for missing values)

## Expected Improvements After Multi-Tier Search

### Before (Single-Tier Search)
- "tzatziki" → Searches Foundation,SR Legacy only → No results → Tries without filter → Finds "Tzatziki dip" at position 4, but query might have changed
- **Success Rate**: ~7.7% (3/39)

### After (Multi-Tier Search)
- "tzatziki" → Searches Foundation,SR Legacy (0 results) → Searches Survey (FNDDS) → Finds "Tzatziki dip" → Enhanced scoring ranks it high → Semantic verification includes it
- **Expected Success Rate**: ~30-50% (12-20/39)

### Key Improvements
1. ✅ Captures Survey (FNDDS) items like "Tzatziki dip", "Guacamole, NFS", "Chutney", "Brandy"
2. ✅ Still prioritizes Foundation/SR Legacy when available
3. ✅ Better coverage for prepared foods, dips, sauces, condiments
4. ✅ Increased semantic verification coverage (top 50 instead of top 20)
