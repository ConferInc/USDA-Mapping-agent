# USDA Nutrition Fetcher - CrewAI Enhanced Version

A modular, scalable agentic workflow for fetching nutrition profiles from the USDA FoodData Central API using CrewAI framework with advanced semantic verification and nutritional similarity scoring.

## Overview

This is a CrewAI-based implementation of the USDA nutrition fetcher, designed with modularity, scalability, and maintainability in mind. The system uses multiple specialized agents working together to efficiently fetch and process nutrition data with comprehensive verification and quality scoring.

## Key Features

✅ **Complete Nutrient Extraction**: Extracts all 117 nutritional attributes from `nutrition_definitions_117.csv`  
✅ **Fast Path Lookup**: Uses curated mappings for instant results  
✅ **Comprehensive 4-Tier Search**: Searches Foundation, SR Legacy, Survey (FNDDS), Branded, and All types  
✅ **Semantic Verification**: LLM-powered semantic matching to ensure accurate ingredient mapping  
✅ **Nutritional Similarity Scoring**: Validates nutritional profiles match expected values  
✅ **Advanced Relevance Scoring**: Rule-based scoring with position, exact match, and data type prioritization  
✅ **Universal Input Support**: Accepts CSV, TXT, and JSON input formats with auto-detection  
✅ **Multiple Output Formats**: CSV (standard/debug), JSON (clean/debug/batch)  
✅ **Detailed Metrics**: Step-by-step timing, tier distribution, API/LLM call tracking  
✅ **Batch Processing**: Process multiple ingredients efficiently with progress tracking  
✅ **Error Handling**: Comprehensive error recovery and retry logic (2 attempts)  

## Architecture

The system consists of 5 specialized agents:

1. **MappingLookupAgent** - Fast path lookup in curated mappings
2. **SearchStrategyAgent** - LLM-powered semantic search intent generation
3. **USDASearchAgent** - USDA API interaction with comprehensive 4-tier search
4. **MatchScoringAgent** - Quality scoring and ranking with advanced relevance scoring
5. **NutritionExtractorAgent** - Data extraction and normalization (all 117 nutrients)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required environment variables:
- `USDA_API_KEY` (required)
- `OPENAI_API_KEY` (required for LLM features)
- `OPENAI_BASE_URL` (optional)
- `OPENAI_MODEL_NAME` (optional, default: gpt-4o-mini)

## Usage

### Command Line

#### Basic Usage
```bash
# Process ingredients from CSV
python main_enhanced.py --input ingredients.csv --output nutrition_data.csv

# Process with limit
python main_enhanced.py --input ingredients.csv --output results.csv --limit 10

# Resume from specific index
python main_enhanced.py --input ingredients.csv --output results.csv --start-from 50
```

#### Input Formats
```bash
# CSV (auto-detected)
python main_enhanced.py --input ingredients.csv --output results.csv

# TXT file (one ingredient per line)
python main_enhanced.py --input ingredients.txt --input-format txt --output results.csv

# JSON file
python main_enhanced.py --input ingredients.json --input-format json --output results.json
```

#### Output Formats
```bash
# Standard CSV (default)
python main_enhanced.py --input ingredients.csv --format csv --output results.csv

# Debug CSV (with detailed metrics)
python main_enhanced.py --input ingredients.csv --format csv-debug --output results_debug.csv

# Clean JSON (API-ready, minimal payload)
python main_enhanced.py --input ingredients.csv --format json-clean --output results_clean.json

# Debug JSON (full information)
python main_enhanced.py --input ingredients.csv --format json-debug --output results_debug.json

# Batch JSON (with summary statistics)
python main_enhanced.py --input ingredients.csv --format json-batch --output results_batch.json
```

### Python API

```python
from orchestrator_enhanced import EnhancedNutritionFetchOrchestrator

orchestrator = EnhancedNutritionFetchOrchestrator()

# Process single ingredient
result = orchestrator.fetch_nutrition_for_ingredient("tzatziki")

# Process multiple ingredients
results = orchestrator.process_ingredients(
    ingredients=["tzatziki", "guacamole", "chutney"],
    output_file="nutrition_data.csv",
    format="csv",
    output_mode="standard"
)
```

## Workflow

The enhanced workflow follows these steps:

1. **Fast Path (Curated Mappings)**: Check if ingredient exists in curated mappings
2. **Search Strategy Generation**: LLM generates optimal search query (cached for performance)
3. **Comprehensive 4-Tier Search**: 
   - Tier 1: Foundation,SR Legacy (30 results)
   - Tier 2: Survey (FNDDS) (20 results)
   - Tier 3: Branded (20 results)
   - Tier 4: All types (10 results)
   - Total: Up to 80 results, merged and scored
4. **Semantic Verification**: LLM verifies semantic match (0-100% score)
5. **Nutritional Similarity Scoring** (conditional): Validates nutritional profile matches
6. **Nutrition Extraction**: Extracts all 117 nutrients from USDA data

### Decision Logic

| Semantic Score | Action | Nutritional Threshold | Flag |
|---------------|--------|----------------------|------|
| >= 90% | Direct mapping, skip nutritional scoring | N/A | HIGH_CONFIDENCE |
| 80-89% | Proceed with nutritional scoring | >= 80% | HIGH_CONFIDENCE or MID_CONFIDENCE |
| 65-79% | Proceed with nutritional scoring | >= 90% | MID_CONFIDENCE |
| < 65% | Skip, don't map | N/A | NO_MAPPING_FOUND |

## Output Formats

### CSV Standard
- Basic metadata (ingredient, fdc_id, description, data_type, flag, etc.)
- Processing time
- All 116 nutrients
- **Total**: ~131 columns

### CSV Debug
- All standard columns
- Step-by-step timing breakdown
- Tier distribution (counts per tier)
- Top 3 semantic results (scores + descriptions)
- Top 3 nutritional results (scores + descriptions)
- API/LLM call counts
- Attempt details
- All 116 nutrients
- **Total**: ~160+ columns

### JSON Clean
Minimal payload for API integration:
```json
{
  "ingredient": "tzatziki",
  "fdc_id": 2705448,
  "description": "Tzatziki dip",
  "data_type": "Survey (FNDDS)",
  "flag": "HIGH_CONFIDENCE",
  "nutrients": {
    "nutrient-calories-energy": {"amount": 91.0, "unit": "kcal"},
    ...
  },
  "timestamp": "2026-01-14T00:26:22.497773"
}
```

### JSON Debug
Full information with nested debug section containing timing, metrics, and detailed results.

### JSON Batch
Array format with summary statistics:
```json
{
  "summary": {
    "total": 39,
    "successful": 12,
    "failed": 27,
    "processing_time_seconds": 1234.5
  },
  "results": [...],
  "failed_ingredients": [...]
}
```

## Project Structure

```
nutrition_usda_crewai/
├── agents/              # CrewAI agents
│   ├── mapping_lookup_agent.py
│   ├── search_strategy_agent.py
│   ├── usda_search_agent.py
│   ├── match_scoring_agent.py
│   └── nutrition_extractor_agent.py
├── tasks/               # Task definitions
├── tools/               # Reusable tools
│   ├── usda_api_tool.py
│   ├── mapping_tool.py
│   ├── cache_tool.py
│   ├── scoring_tool.py
│   ├── llm_tool.py
│   ├── semantic_verification_tool.py
│   ├── nutritional_similarity_tool.py
│   └── search_retry_tool.py
├── utils/               # Utility modules
│   ├── data_loader.py      # Universal input loader
│   ├── data_saver_enhanced.py  # Enhanced output formats
│   └── nutrient_mapper.py
├── orchestrator_enhanced.py  # Main workflow orchestrator
├── main_enhanced.py      # Command-line entry point
└── requirements.txt      # Dependencies
```

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

## Documentation

- **CURRENT_RULES_SUMMARY.md**: Current workflow rules and decision logic
- **IMPLEMENTATION_SUMMARY.md**: Latest implementation details and features

## License

[Your License Here]
