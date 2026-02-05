# CrewAI Nutrition Workflow - Complete Documentation

## Overview

This document provides comprehensive documentation of the CrewAI-based USDA nutrition fetching workflow, including architecture, workflow steps, decision logic, and implementation details.

## Architecture

### Agents

1. **MappingLookupAgent**
   - **Role**: Mapping Lookup Specialist
   - **Goal**: Quickly find ingredients in curated mappings database
   - **Tools**: `load_curated_mappings`, `search_mappings`
   - **Output**: FDC ID if found in mappings

2. **SearchStrategyAgent**
   - **Role**: Search Strategy Expert
   - **Goal**: Generate optimal search strategies for USDA API queries
   - **Tools**: `generate_search_intent`, `get_cached_search_intent`, `save_search_intent_cache`
   - **Output**: Search query with intent (preferred form, avoid words, expected pattern)

3. **USDASearchAgent**
   - **Role**: USDA API Specialist
   - **Goal**: Search USDA FoodData Central API efficiently
   - **Tools**: `search_usda_food_multi_tier_comprehensive`
   - **Output**: Up to 80 search results from 4 tiers

4. **MatchScoringAgent**
   - **Role**: Quality Scoring Expert
   - **Goal**: Score and rank search results
   - **Tools**: `score_match_quality_enhanced`, `filter_search_results`
   - **Output**: Ranked search results

5. **NutritionExtractorAgent**
   - **Role**: Nutrition Data Extractor
   - **Goal**: Extract and normalize nutrition data
   - **Tools**: `extract_nutrition_data`, `get_usda_food_details`
   - **Output**: Standardized nutrition data (all 117 nutrients)

## Workflow Steps

### Step 1: Fast Path - Curated Mappings

**Purpose**: Instant lookup for known ingredients

**Process**:
1. Search curated mappings using fuzzy matching
2. If found, directly fetch nutrition data using FDC ID
3. Return with `HIGH_CONFIDENCE` flag

**Output**: Nutrition data with `source: "curated_mapping"`

### Step 2: Search Strategy Generation

**Purpose**: Generate optimal search query using LLM

**Process**:
1. Check cache for existing search intent
2. If not cached, use LLM to generate search intent:
   - Search query
   - Preferred form
   - Avoid words
   - Expected pattern
3. Cache the intent for future use

**Output**: Search query optimized for USDA API

### Step 3: Comprehensive 4-Tier Search

**Purpose**: Search USDA API across all relevant data types

**Strategy**:
- **Tier 1**: Foundation,SR Legacy - 30 results (preferred generic foods)
- **Tier 2**: Survey (FNDDS) - 20 results (prepared foods, dips, sauces)
- **Tier 3**: Branded - 20 results (branded products)
- **Tier 4**: All types - 10 results (catch-all)

**Process**:
1. Execute all 4 tiers in parallel (always, no conditional logic)
2. Merge results and deduplicate by FDC ID
3. Score all results using enhanced relevance scoring
4. Return top 80 results

**Enhanced Scoring Factors**:
- Position in results (earlier = higher score)
- Exact match bonus
- Compound food penalty
- Processed form penalty
- Data type priority (Foundation > SR Legacy > Survey > Branded)
- Branded product penalty

### Step 3.5: Semantic Verification

**Purpose**: Verify semantic match using LLM

**Process**:
1. Analyze top 80 search results
2. LLM scores each result for semantic match (0-100%)
3. Cache semantic scores for consistency
4. Return top 3 results with `semantic_match_score >= 40`

**Scoring Guidelines**:
- **90-100%**: Exact match or same item with minor naming/form differences
- **80-89%**: Same ingredient, different form
- **65-79%**: Related ingredient, acceptable match
- **50-64%**: Related but different
- **<50%**: Different ingredient, reject

**Decision Logic**:

| Semantic Score | Action | Nutritional Threshold | Flag | Mapping Status |
|---------------|--------|----------------------|------|----------------|
| >= 90% | Direct mapping, skip Step 4 & 5 | N/A (skipped) | HIGH_CONFIDENCE | search_verified_semantic_high |
| 80-89% | Proceed to Step 4 & 5 | >= 80% | HIGH_CONFIDENCE or MID_CONFIDENCE | search_verified_high or search_verified_mid |
| 65-79% | Proceed to Step 4 & 5 | >= 90% | MID_CONFIDENCE | search_verified_mid_semantic_low |
| < 65% | Skip Step 4 & 5, don't map | N/A (skipped) | NO_MAPPING_FOUND | semantic_score_too_low |

### Step 4: Nutritional Similarity Scoring (Conditional)

**Purpose**: Validate nutritional profile matches expected values

**Process** (only if semantic score 65-89%):
1. LLM generates expected nutritional values for ingredient (using web knowledge)
2. Fetch actual nutrition data for top 3 semantic matches
3. Compare expected vs actual using weighted attributes
4. Calculate nutritional similarity score (0-100%)

**Weighted Attributes**:
- Calories (high weight)
- Protein (high weight)
- Fat (medium weight)
- Carbohydrates (medium weight)
- Key micronutrients (low weight)

**Output**: Top 3 results with nutritional similarity scores

### Step 5: Nutrition Extraction

**Purpose**: Extract all 117 nutrients from USDA data

**Process**:
1. Fetch detailed food data using FDC ID
2. Extract all 117 standardized nutrients
3. Map to standardized nutrient IDs
4. Set missing values to `NULL`

**Output**: Complete nutrition profile with all 117 nutrients

## Retry Logic

**Max Retries**: 2 attempts

**Attempt 1**: Comprehensive 4-tier search with original query  
**Attempt 2**: Comprehensive 4-tier search with query variations

**Query Variations**:
- Add/remove modifiers
- Category-based search
- Alternative naming
- Simplified form

## Input Formats

### CSV
- Detects column names: `ingredient`, `name`, `food`, `item`
- Skips empty rows

### TXT
- One ingredient per line
- Skips comments (lines starting with `#` or `//`)
- Skips headers

### JSON
Supports multiple structures:
- Simple array: `["ingredient1", "ingredient2"]`
- Array of objects: `[{"ingredient": "..."}]`
- Object with ingredients key: `{"ingredients": [...]}`
- Object with data key: `{"data": [{"name": "..."}]}`

**Auto-detection**: By file extension and content analysis

## Output Formats

### CSV Standard
- Basic metadata (14 columns)
- Processing time (1 column)
- All 116 nutrients
- **Total**: ~131 columns

### CSV Debug
- All standard columns
- Step-by-step timing (5 columns)
- Tier distribution (4 columns)
- Search metrics (2 columns)
- Top 3 semantic results (6 columns)
- Top 3 nutritional results (6 columns)
- API/LLM metrics (4 columns)
- Attempt details (4 columns)
- All 116 nutrients
- **Total**: ~160+ columns

### JSON Clean
Minimal payload for API use:
- Essential fields only
- No debug information

### JSON Debug
Full information with nested debug section:
- Result data
- Debug information (timing, metrics, top results)

### JSON Batch
Array format with summary:
- Summary statistics
- Results array
- Failed ingredients list

## Metrics Tracking

The orchestrator tracks detailed metrics for each ingredient:

- **Timing**: Curated mapping, search, semantic verification, nutritional scoring, extraction
- **Tier Distribution**: Counts for each search tier (1-4)
- **Search Metrics**: Total results, semantic verified count, top 3 results
- **API/LLM Metrics**: Call counts, cache hits/misses
- **Attempt Details**: Query and success status for each retry

## Error Handling

- **API Errors**: Retry with exponential backoff
- **LLM Errors**: Fallback to default search query
- **No Results**: Retry with alternative query
- **Low Scores**: Skip mapping, mark as failed
- **Extraction Errors**: Retry with alternative FDC ID

## Performance Optimizations

- **Caching**: Search intents and semantic scores are cached
- **Fast Path**: Curated mappings bypass all search steps
- **Parallel Processing**: 4-tier search executes in parallel
- **Early Exit**: High semantic scores (>=90%) skip nutritional verification

## Configuration

### Environment Variables
- `USDA_API_KEY`: Required for USDA API access
- `OPENAI_API_KEY`: Required for LLM features
- `OPENAI_BASE_URL`: Optional, for custom OpenAI-compatible API
- `OPENAI_MODEL_NAME`: Optional, default: `gpt-4o-mini`

### Thresholds
- Semantic score >= 90%: Direct mapping
- Semantic score 80-89%: Nutritional threshold >= 80%
- Semantic score 65-79%: Nutritional threshold >= 90%
- Semantic score < 65%: No mapping

## Testing

```bash
# Test individual agents
python test_agents.py

# Test nutrient extraction
python test_nutrient_extraction.py

# Test orchestrator
python test_orchestrator.py

# Verify output format
python verify_enhanced_output.py
```

## Troubleshooting

### Common Issues

1. **No semantic matches found**
   - Check if ingredient exists in USDA database
   - Verify search query is appropriate
   - Check semantic verification logs

2. **Low semantic scores**
   - Ingredient may not exist in USDA
   - Try alternative naming
   - Check if ingredient is too specific

3. **Nutritional similarity fails**
   - Expected values may not match USDA data
   - Check if ingredient form is different
   - Verify nutritional profile is reasonable

4. **API rate limiting**
   - System includes automatic retry with backoff
   - Check API key limits
   - Reduce batch size if needed
