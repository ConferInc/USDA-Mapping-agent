"""
Enhanced Workflow Orchestrator - With semantic verification, nutritional similarity, and retry logic
"""

import os
import sys
import datetime
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
from io import StringIO
import contextlib

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.mapping_tool import search_mappings
from tools.llm_tool import generate_search_intent
from tools.cache_tool import get_cached_search_intent, save_search_intent_cache
from tools.usda_api_tool import search_usda_food, search_usda_food_multi_tier, search_usda_food_multi_tier_comprehensive, get_usda_food_details
from tools.scoring_tool import filter_search_results
from tools.nutrition_extractor_tool import extract_nutrition_data
from tools.semantic_verification_tool import verify_semantic_match
from tools.nutritional_similarity_tool import calculate_nutritional_similarity_score
from tools.search_retry_tool import generate_retry_search_strategy
from utils.data_loader import load_ingredients
from utils.data_saver_enhanced import save_results_enhanced


class EnhancedNutritionFetchOrchestrator:
    """
    Enhanced orchestrator with semantic verification and nutritional similarity scoring.
    
    Features:
    - Advanced relevance scoring with compound food detection and processed form penalties
    - Semantic verification (LLM-based)
    - Nutritional similarity scoring (LLM + web research)
    - Retry logic with varied search strategies
    - Optional fast-path using get_ingredient_nutrition_profile_fast() for simple cases
    """
    
    def __init__(self, log_file: Optional[str] = None, use_enhanced_scoring: bool = True):
        """
        Initialize the orchestrator
        
        Args:
            log_file: Optional path to log file for output
            use_enhanced_scoring: If True, use enhanced relevance scoring with advanced logic (default: True)
        """
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "from_mappings": 0,
            "from_search": 0,
            "no_mapping_found": 0
        }
        self.log_file = log_file
        self.log_buffer = StringIO()
        self.use_enhanced_scoring = use_enhanced_scoring
    
    def _log(self, message: str):
        """Log message to both console and log file"""
        print(message)
        self.log_buffer.write(message + "\n")
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(message + "\n")
            except:
                pass
    
    def fetch_nutrition_for_ingredient(self, ingredient: str) -> Optional[Dict]:
        """
        Fetch nutrition data with enhanced verification and retry logic.
        
        Returns:
            Nutrition data dictionary with enhanced metadata, or None if failed
        """
        start_time = time.time()
        self._log(f"\n{'='*80}")
        self._log(f"Processing: {ingredient}")
        self._log(f"{'='*80}")
        
        result_metadata = {
            "ingredient": ingredient,
            "timestamp": datetime.datetime.now().isoformat(),
            "flag": "SUCCESS",
            "mapping_status": "",
            "semantic_match_score": None,
            "nutritional_similarity_score": None,
            "reasoning": "",
            "retry_attempts": 0,
            "search_queries_used": [],
            # Debug information
            "timing": {
                "curated_mapping_time_seconds": None,
                "search_time_seconds": None,
                "semantic_verification_time_seconds": None,
                "nutritional_scoring_time_seconds": None,
                "extraction_time_seconds": None
            },
            "tier_distribution": {
                "tier_1_count": 0,
                "tier_2_count": 0,
                "tier_3_count": 0,
                "tier_4_count": 0
            },
            "search_metrics": {
                "total_search_results": 0,
                "semantic_verified_count": 0,
                "top_semantic_results": [],
                "top_nutritional_results": []
            },
            "api_metrics": {
                "api_calls_count": 0,
                "llm_calls_count": 0,
                "cache_hits": 0,
                "cache_misses": 0
            },
            "attempt_details": []
        }
        
        # Step 1: Check curated mappings (fast path)
        self._log(f"\n[Step 1] Checking curated mappings...")
        mapping_start = time.time()
        mapping = search_mappings(ingredient)
        mapping_time = time.time() - mapping_start
        result_metadata["timing"]["curated_mapping_time_seconds"] = round(mapping_time, 3)
        result_metadata["api_metrics"]["api_calls_count"] += 0  # Mapping lookup doesn't use API
        
        if mapping:
            self._log(f"[OK] Found in mappings! FDC ID: {mapping.get('fdc_id')}")
            fdc_id = mapping.get('fdc_id')
            
            # Extract nutrition data directly
            self._log(f"\n[Step 5] Extracting nutrition data...")
            extraction_start = time.time()
            food_data = get_usda_food_details(fdc_id)
            result_metadata["api_metrics"]["api_calls_count"] += 1
            if food_data:
                nutrition_data = extract_nutrition_data(food_data)
                extraction_time = time.time() - extraction_start
                result_metadata["timing"]["extraction_time_seconds"] = round(extraction_time, 3)
                
                if nutrition_data:
                    nutrition_data["ingredient"] = ingredient
                    nutrition_data["source"] = "curated_mapping"
                    nutrition_data["flag"] = "HIGH_CONFIDENCE"
                    nutrition_data["mapping_status"] = "curated_mapping"
                    nutrition_data["semantic_match_score"] = 100.0  # Trusted mapping
                    nutrition_data["nutritional_similarity_score"] = 100.0  # Trusted mapping
                    nutrition_data["reasoning"] = "Found in curated mappings (verified)"
                    nutrition_data["retry_attempts"] = 0
                    # Add debug metadata
                    nutrition_data["debug"] = result_metadata
                    self.stats["from_mappings"] += 1
                    elapsed_time = time.time() - start_time
                    self._log(f"[SUCCESS] Extracted nutrition data for '{ingredient}'")
                    self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (fast path - curated mapping)")
                    nutrition_data["processing_time_seconds"] = round(elapsed_time, 2)
                    return nutrition_data
        
        # Step 2-5: Search with retry logic (up to 2 attempts)
        # Attempt 1: Comprehensive 4-tier search with original query
        # Attempt 2: Comprehensive 4-tier search with query variations
        max_retries = 2
        previous_queries = []
        
        for attempt in range(1, max_retries + 1):
            result_metadata["retry_attempts"] = attempt
            attempt_info = {"attempt": attempt, "query": "", "success": False}
            
            self._log(f"\n[Attempt {attempt}/{max_retries}]")
            
            # Step 2: Generate search strategy
            self._log(f"[Step 2] Generating search strategy...")
            if attempt == 1:
                # First attempt: use cached or generate new intent
                intent = get_cached_search_intent(ingredient)
                if not intent:
                    intent = generate_search_intent(ingredient)
                    if intent:
                        save_search_intent_cache(ingredient, intent)
            else:
                # Retry: generate alternative strategy
                intent = generate_retry_search_strategy(ingredient, attempt, previous_queries)
            
            if not intent:
                intent = {
                    "search_query": ingredient,
                    "is_phrase": " " in ingredient.lower(),
                    "preferred_form": "",
                    "avoid": [],
                    "expected_pattern": ""
                }
            
            search_query = intent.get('search_query', ingredient)
            result_metadata["search_queries_used"].append(search_query)
            attempt_info["query"] = search_query
            self._log(f"[OK] Search query: {search_query}")
            if attempt > 1:
                self._log(f"  Retry reason: {intent.get('retry_reason', 'Alternative strategy')}")
            
            # Step 3: Search USDA API (Comprehensive 4-tier search strategy)
            self._log(f"\n[Step 3] Searching USDA API (comprehensive 4-tier search)...")
            # Use comprehensive 4-tier search: Foundation,SR Legacy (30) + Survey FNDDS (20) + Branded (20) + All types (10)
            # Always searches all tiers for maximum coverage
            search_start = time.time()
            search_results = search_usda_food_multi_tier_comprehensive(search_query, ingredient=ingredient)
            search_time = time.time() - search_start
            result_metadata["timing"]["search_time_seconds"] = round(search_time, 3)
            result_metadata["api_metrics"]["api_calls_count"] += 4  # 4 tiers = 4 API calls
            
            if not search_results:
                self._log(f"[WARNING] No search results found")
                attempt_info["success"] = False
                result_metadata["attempt_details"].append(attempt_info)
                if attempt < max_retries:
                    continue  # Try next retry
                else:
                    result_metadata["flag"] = "NO_MAPPING_FOUND"
                    result_metadata["mapping_status"] = "no_search_results"
                    result_metadata["reasoning"] = f"No search results found after {max_retries} attempts with different queries"
                    elapsed_time = time.time() - start_time
                    result_metadata["processing_time_seconds"] = round(elapsed_time, 2)
                    self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (no search results)")
                    self.stats["no_mapping_found"] += 1
                    return self._create_failed_result(result_metadata)
            
            # Count results by tier for logging and metadata
            tier_counts = {}
            for result in search_results:
                tier = result.get("_search_tier", "unknown")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            # Store tier distribution in metadata
            result_metadata["tier_distribution"]["tier_1_count"] = tier_counts.get(1, 0)
            result_metadata["tier_distribution"]["tier_2_count"] = tier_counts.get(2, 0)
            result_metadata["tier_distribution"]["tier_3_count"] = tier_counts.get(3, 0)
            result_metadata["tier_distribution"]["tier_4_count"] = tier_counts.get(4, 0)
            result_metadata["search_metrics"]["total_search_results"] = len(search_results)
            
            tier_info = ", ".join([f"Tier {k}: {v}" for k, v in sorted(tier_counts.items())])
            tier_names = {1: "Foundation,SR Legacy", 2: "Survey (FNDDS)", 3: "Branded", 4: "All types"}
            tier_details = ", ".join([f"Tier {k} ({tier_names.get(k, 'unknown')}): {v}" for k, v in sorted(tier_counts.items())])
            self._log(f"[OK] Found {len(search_results)} search results ({tier_details})")
            
            # Optional: Pre-filter using enhanced scoring before semantic verification
            # This can improve efficiency by reducing the number of results sent to LLM
            # Currently disabled to maintain full semantic verification, but can be enabled if needed
            # if self.use_enhanced_scoring and len(search_results) > 10:
            #     from tools.scoring_tool import filter_search_results
            #     prefiltered = filter_search_results(search_results, ingredient, max_score=100, use_enhanced=True)
            #     if prefiltered:
            #         search_results = [item[1] for item in prefiltered[:10]]  # Top 10 for semantic verification
            #         self._log(f"[INFO] Pre-filtered to {len(search_results)} results using enhanced scoring")
            
            # Step 3.5: Semantic Verification (LLM-based)
            self._log(f"\n[Step 3.5] Semantic verification (LLM)...")
            semantic_start = time.time()
            verified_results = verify_semantic_match(ingredient, search_results, top_n=3)
            semantic_time = time.time() - semantic_start
            result_metadata["timing"]["semantic_verification_time_seconds"] = round(semantic_time, 3)
            result_metadata["api_metrics"]["llm_calls_count"] += 1  # Semantic verification uses LLM
            
            if not verified_results:
                self._log(f"[WARNING] No semantically verified matches")
                attempt_info["success"] = False
                result_metadata["attempt_details"].append(attempt_info)
                if attempt < max_retries:
                    continue  # Try next retry
                else:
                    result_metadata["flag"] = "NO_MAPPING_FOUND"
                    result_metadata["mapping_status"] = "semantic_mismatch"
                    result_metadata["reasoning"] = f"No semantically valid matches found after {max_retries} attempts"
                    elapsed_time = time.time() - start_time
                    result_metadata["processing_time_seconds"] = round(elapsed_time, 2)
                    self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (no semantic matches)")
                    self.stats["no_mapping_found"] += 1
                    return self._create_failed_result(result_metadata)
            
            self._log(f"[OK] {len(verified_results)} semantically verified results")
            result_metadata["search_metrics"]["semantic_verified_count"] = len(verified_results)
            
            # Store top 3 semantic results for debug
            top_semantic = []
            for v_result in verified_results[:3]:
                top_semantic.append({
                    "fdc_id": v_result.get("fdcId") or v_result.get("fdc_id"),
                    "description": v_result.get("description", ""),
                    "score": v_result.get("semantic_match_score", 0)
                })
            result_metadata["search_metrics"]["top_semantic_results"] = top_semantic
            
            best_semantic_result = verified_results[0]  # Already sorted by semantic score
            best_semantic_score = best_semantic_result.get("semantic_match_score", 0)
            
            for i, v_result in enumerate(verified_results, 1):
                score = v_result.get("semantic_match_score", 0)
                desc = v_result.get("description", "")
                self._log(f"  {i}. {desc} (semantic score: {score:.1f}%)")
            
            # Decision logic based on semantic score:
            # - >= 90%: Direct mapping (HIGH_CONFIDENCE), skip step 4 & 5
            # - 80-89%: Proceed to step 4 & 5 (can map if nutritional >= 80%)
            # - 65-79%: Proceed to step 4 & 5 (can map if nutritional >= 90%)
            # - < 65%: DON'T proceed with next steps, skip step 4 & 5
            
            proceed_to_step4 = False
            allow_mapping = False
            nutritional_threshold = 80.0  # Default threshold for mapping
            
            if best_semantic_score >= 90.0:
                # Semantic score >= 90%: Direct mapping, skip step 4 & 5
                self._log(f"\n[INFO] Semantic score ({best_semantic_score:.1f}%) >= 90% - Direct mapping, skipping step 4 & 5")
                proceed_to_step4 = False
                allow_mapping = True
                flag = "HIGH_CONFIDENCE"
                mapping_status = "search_verified_semantic_high"
                fdc_id = best_semantic_result.get("fdcId") or best_semantic_result.get("fdc_id")
                
            elif best_semantic_score >= 80.0:
                # Semantic score 80-89%: Need nutritional verification (can map if nutritional >= 80%)
                self._log(f"\n[INFO] Semantic score ({best_semantic_score:.1f}%) between 80-89% - Proceeding to step 4 & 5 for nutritional verification (threshold: >= 80%)")
                proceed_to_step4 = True
                allow_mapping = True  # Can map if nutritional score >= 80%
                nutritional_threshold = 80.0
                
            elif best_semantic_score >= 65.0:
                # Semantic score 65-79%: Need nutritional verification (can map if nutritional >= 90%)
                self._log(f"\n[INFO] Semantic score ({best_semantic_score:.1f}%) between 65-79% - Proceeding to step 4 & 5 for nutritional verification (threshold: >= 90%)")
                proceed_to_step4 = True
                allow_mapping = True  # Can map if nutritional score >= 90%
                nutritional_threshold = 90.0
                
            else:
                # Semantic score < 65%: DON'T proceed with next steps, skip step 4 & 5
                self._log(f"\n[INFO] Semantic score ({best_semantic_score:.1f}%) < 65% - Skipping step 4 & 5, will NOT map")
                proceed_to_step4 = False
                allow_mapping = False
                result_metadata["flag"] = "NO_MAPPING_FOUND"
                result_metadata["mapping_status"] = "semantic_score_too_low"
                result_metadata["semantic_match_score"] = best_semantic_score
                result_metadata["reasoning"] = f"Semantic score ({best_semantic_score:.1f}%) below 65% threshold. Skipping nutritional verification."
                attempt_info["success"] = False
                result_metadata["attempt_details"].append(attempt_info)
                
                if attempt < max_retries:
                    self._log(f"[WARNING] Semantic score too low (<65%), retrying...")
                    previous_queries.append(search_query)
                    continue
                else:
                    elapsed_time = time.time() - start_time
                    result_metadata["processing_time_seconds"] = round(elapsed_time, 2)
                    self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (semantic score too low)")
                    self.stats["no_mapping_found"] += 1
                    return self._create_failed_result(result_metadata)
            
            # Step 4 & 5: Nutritional Similarity Scoring (only if flag is set)
            if proceed_to_step4:
                self._log(f"\n[Step 4] Nutritional similarity scoring (LLM + web research)...")
                nutritional_start = time.time()
                similarity_results = calculate_nutritional_similarity_score(ingredient, verified_results, top_n=3)
                nutritional_time = time.time() - nutritional_start
                result_metadata["timing"]["nutritional_scoring_time_seconds"] = round(nutritional_time, 3)
                result_metadata["api_metrics"]["llm_calls_count"] += 2  # Expected nutrition + similarity comparison
                result_metadata["api_metrics"]["api_calls_count"] += len(similarity_results)  # One API call per result for nutrition data
                
                if not similarity_results:
                    self._log(f"[WARNING] No nutritionally similar matches")
                    attempt_info["success"] = False
                    result_metadata["attempt_details"].append(attempt_info)
                    if attempt < max_retries:
                        continue  # Try next retry
                    else:
                        result_metadata["flag"] = "NO_MAPPING_FOUND"
                        result_metadata["mapping_status"] = "nutritional_mismatch"
                        result_metadata["semantic_match_score"] = best_semantic_score
                        result_metadata["reasoning"] = f"No nutritionally similar matches found after {max_retries} attempts. Semantic score: {best_semantic_score:.1f}%"
                        self.stats["no_mapping_found"] += 1
                        return self._create_failed_result(result_metadata)
                
                # Find best match with nutritional similarity
                best_match = similarity_results[0]  # Already sorted by nutritional similarity score
                best_nutrition_score = best_match.get("nutritional_similarity_score", 0)
                
                # Store top 3 nutritional results for debug
                top_nutritional = []
                for sim_result in similarity_results[:3]:
                    top_nutritional.append({
                        "fdc_id": sim_result.get("fdc_id"),
                        "description": sim_result.get("description", ""),
                        "score": sim_result.get("nutritional_similarity_score", 0)
                    })
                result_metadata["search_metrics"]["top_nutritional_results"] = top_nutritional
                
                self._log(f"[OK] Best nutritional match: {best_match.get('description')} (nutritional similarity: {best_nutrition_score:.1f}%)")
                
                # Decision based on allow_mapping flag and nutritional score
                # Note: If semantic score < 65%, we already skipped step 4 & 5, so this code won't execute
                # This section only executes for semantic scores >= 65%
                
                if allow_mapping:
                    # Check nutritional score against the threshold (80% for 80-89% semantic, 90% for 65-79% semantic)
                    if best_nutrition_score >= nutritional_threshold:
                        # Determine confidence level based on nutritional score
                        if best_nutrition_score >= 90.0:
                            if best_semantic_score >= 80.0:
                                flag = "HIGH_CONFIDENCE"
                                mapping_status = "search_verified_high"
                            else:
                                # High nutritional but lower semantic (65-79%)
                                flag = "MID_CONFIDENCE"
                                mapping_status = "search_verified_mid_semantic_low"
                        elif best_nutrition_score >= 80.0:
                            flag = "MID_CONFIDENCE"
                            mapping_status = "search_verified_mid"
                        else:
                            flag = "LOW_CONFIDENCE"
                            mapping_status = "search_low_confidence"
                        
                        # Nutritional score passed threshold - proceed with extraction
                        self._log(f"[OK] Combined verification passed - Semantic: {best_semantic_score:.1f}%, Nutritional: {best_nutrition_score:.1f}% (threshold: {nutritional_threshold:.1f}%), Flag: {flag}")
                        
                        # Step 5: Extract nutrition data
                        self._log(f"\n[Step 5] Extracting nutrition data...")
                        fdc_id = best_match.get("fdc_id")
                        food_data = get_usda_food_details(fdc_id)
                        
                        if food_data:
                            nutrition_data = extract_nutrition_data(food_data)
                            extraction_time = time.time() - extraction_start
                            result_metadata["timing"]["extraction_time_seconds"] = round(extraction_time, 3)
                            
                            if nutrition_data:
                                # Add enhanced metadata
                                nutrition_data["ingredient"] = ingredient
                                nutrition_data["source"] = "search"
                                nutrition_data["flag"] = flag
                                nutrition_data["mapping_status"] = mapping_status
                                nutrition_data["semantic_match_score"] = best_semantic_score
                                nutrition_data["nutritional_similarity_score"] = best_nutrition_score
                                nutrition_data["reasoning"] = best_match.get("nutritional_reasoning", "")
                                nutrition_data["retry_attempts"] = attempt
                                nutrition_data["search_queries_used"] = ", ".join(result_metadata["search_queries_used"])
                                nutrition_data["timestamp"] = result_metadata["timestamp"]
                                # Add debug metadata
                                nutrition_data["debug"] = result_metadata
                                
                                self.stats["from_search"] += 1
                                elapsed_time = time.time() - start_time
                                self._log(f"[SUCCESS] Extracted nutrition data for '{ingredient}' ({flag})")
                                self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds")
                                nutrition_data["processing_time_seconds"] = round(elapsed_time, 2)
                                attempt_info["success"] = True
                                result_metadata["attempt_details"].append(attempt_info)
                                return nutrition_data
                            else:
                                result_metadata["flag"] = "NO_MAPPING_FOUND"
                                result_metadata["mapping_status"] = "nutrition_extraction_failed"
                                result_metadata["semantic_match_score"] = best_semantic_score
                                result_metadata["nutritional_similarity_score"] = best_nutrition_score
                                result_metadata["reasoning"] = f"Could not extract nutrition data for FDC ID {fdc_id}"
                                if attempt < max_retries:
                                    self._log(f"[WARNING] Nutrition extraction failed, retrying...")
                                    previous_queries.append(search_query)
                                    continue
                                else:
                                    elapsed_time = time.time() - start_time
                                    result_metadata["processing_time_seconds"] = round(elapsed_time, 2)
                                    self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (extraction failed)")
                                    self.stats["no_mapping_found"] += 1
                                    return self._create_failed_result(result_metadata)
                        else:
                            result_metadata["flag"] = "NO_MAPPING_FOUND"
                            result_metadata["mapping_status"] = "food_data_not_found"
                            result_metadata["semantic_match_score"] = best_semantic_score
                            result_metadata["nutritional_similarity_score"] = best_nutrition_score
                            result_metadata["reasoning"] = f"Could not fetch food data for FDC ID {fdc_id}"
                            if attempt < max_retries:
                                self._log(f"[WARNING] Could not fetch food data for FDC ID {fdc_id}, retrying...")
                                previous_queries.append(search_query)
                                continue
                            else:
                                elapsed_time = time.time() - start_time
                                result_metadata["processing_time_seconds"] = round(elapsed_time, 2)
                                self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (food data not found)")
                                self.stats["no_mapping_found"] += 1
                                return self._create_failed_result(result_metadata)
            
            else:
                # Semantic score >= 90%, direct mapping without step 4 & 5
                self._log(f"\n[Step 5] Extracting nutrition data (skipped step 4 - direct mapping)...")
                extraction_start = time.time()
                fdc_id = best_semantic_result.get("fdcId") or best_semantic_result.get("fdc_id")
                
                if not fdc_id:
                    # Try other FDC IDs from semantic results
                    self._log(f"[WARNING] Could not get FDC ID from best match, trying other semantic matches...")
                    for alt_result in verified_results[1:]:  # Try other verified results
                        alt_fdc_id = alt_result.get("fdcId") or alt_result.get("fdc_id")
                        if alt_fdc_id:
                            fdc_id = alt_fdc_id
                            self._log(f"[OK] Using FDC ID {fdc_id} from alternative semantic match")
                            break
                    
                    if not fdc_id:
                        # No FDC ID found in any semantic result
                        if attempt < max_retries:
                            self._log(f"[WARNING] Could not get FDC ID from any semantic match, retrying...")
                            previous_queries.append(search_query)
                            continue
                        else:
                            result_metadata["flag"] = "NO_MAPPING_FOUND"
                            result_metadata["mapping_status"] = "fdc_id_not_found"
                            result_metadata["semantic_match_score"] = best_semantic_score
                            result_metadata["reasoning"] = f"Semantic score ({best_semantic_score:.1f}%) was high but could not get FDC ID from any semantic match"
                            elapsed_time = time.time() - start_time
                            result_metadata["processing_time_seconds"] = round(elapsed_time, 2)
                            self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (fdc_id not found)")
                            self.stats["no_mapping_found"] += 1
                            return self._create_failed_result(result_metadata)
                
                # Try to fetch food data, with fallback to other FDC IDs
                extraction_start = time.time()
                food_data = get_usda_food_details(fdc_id)
                result_metadata["api_metrics"]["api_calls_count"] += 1
                
                if not food_data:
                    # Try other FDC IDs from semantic results if first one fails
                    self._log(f"[WARNING] Could not fetch food data for FDC ID {fdc_id}, trying other semantic matches...")
                    for alt_result in verified_results[1:]:  # Try other verified results
                        alt_fdc_id = alt_result.get("fdcId") or alt_result.get("fdc_id")
                        if alt_fdc_id and alt_fdc_id != fdc_id:
                            self._log(f"  Trying FDC ID {alt_fdc_id}...")
                            food_data = get_usda_food_details(alt_fdc_id)
                            if food_data:
                                fdc_id = alt_fdc_id
                                self._log(f"[OK] Successfully fetched data from FDC ID {alt_fdc_id}")
                                break
                    
                    if not food_data:
                        # All FDC IDs from semantic results failed - retry search (not just retry same query)
                        if attempt < max_retries:
                            self._log(f"[WARNING] Could not fetch food data for any FDC ID from semantic results, retrying with different search...")
                            previous_queries.append(search_query)
                            continue
                        else:
                            result_metadata["flag"] = "NO_MAPPING_FOUND"
                            result_metadata["mapping_status"] = "food_data_not_found"
                            result_metadata["semantic_match_score"] = best_semantic_score
                            result_metadata["reasoning"] = f"Semantic score ({best_semantic_score:.1f}%) was high but could not fetch food data for any FDC ID from semantic results"
                            elapsed_time = time.time() - start_time
                            result_metadata["processing_time_seconds"] = round(elapsed_time, 2)
                            self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (food data not found)")
                            self.stats["no_mapping_found"] += 1
                            return self._create_failed_result(result_metadata)
                
                # Extract nutrition data
                extraction_start = time.time()
                nutrition_data = extract_nutrition_data(food_data)
                extraction_time = time.time() - extraction_start
                result_metadata["timing"]["extraction_time_seconds"] = round(extraction_time, 3)
                
                if nutrition_data:
                    # Add enhanced metadata
                    nutrition_data["ingredient"] = ingredient
                    nutrition_data["source"] = "search"
                    nutrition_data["flag"] = flag
                    nutrition_data["mapping_status"] = mapping_status
                    nutrition_data["semantic_match_score"] = best_semantic_score
                    nutrition_data["nutritional_similarity_score"] = None  # Not calculated (skipped step 4)
                    nutrition_data["reasoning"] = f"Direct mapping based on high semantic match score ({best_semantic_score:.1f}%). Step 4 (nutritional similarity) was skipped."
                    nutrition_data["retry_attempts"] = attempt
                    nutrition_data["search_queries_used"] = ", ".join(result_metadata["search_queries_used"])
                    nutrition_data["timestamp"] = result_metadata["timestamp"]
                    # Add debug metadata
                    nutrition_data["debug"] = result_metadata
                    attempt_info["success"] = True
                    result_metadata["attempt_details"].append(attempt_info)
                    
                    self.stats["from_search"] += 1
                    elapsed_time = time.time() - start_time
                    self._log(f"[SUCCESS] Extracted nutrition data for '{ingredient}' ({flag}) - Direct mapping based on semantic score")
                    self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (skipped nutritional verification)")
                    nutrition_data["processing_time_seconds"] = round(elapsed_time, 2)
                    return nutrition_data
        
        # All retries exhausted
        elapsed_time = time.time() - start_time
        result_metadata["flag"] = "NO_MAPPING_FOUND"
        result_metadata["mapping_status"] = "all_retries_exhausted"
        result_metadata["reasoning"] = f"Could not find suitable match after {max_retries} attempts with different search strategies"
        # Store all attempt details
        if "attempt_details" not in result_metadata or len(result_metadata["attempt_details"]) < max_retries:
            # Add final attempt if not already added
            if len(result_metadata.get("attempt_details", [])) < max_retries:
                result_metadata["attempt_details"].append(attempt_info)
        self._log(f"[TIME] Processing time: {elapsed_time:.2f} seconds (all retries exhausted)")
        self.stats["no_mapping_found"] += 1
        failed_result = self._create_failed_result(result_metadata)
        failed_result["processing_time_seconds"] = round(elapsed_time, 2)
        return failed_result
    
    def _create_failed_result(self, metadata: Dict) -> Dict:
        """Create a result dictionary for failed mappings"""
        result = {
            "ingredient": metadata["ingredient"],
            "fdc_id": None,
            "description": None,
            "data_type": None,
            "brand_owner": None,
            "source": None,
            "flag": metadata["flag"],
            "mapping_status": metadata["mapping_status"],
            "semantic_match_score": metadata.get("semantic_match_score"),
            "nutritional_similarity_score": metadata.get("nutritional_similarity_score"),
            "reasoning": metadata["reasoning"],
            "retry_attempts": metadata["retry_attempts"],
            "search_queries_used": ", ".join(metadata["search_queries_used"]),
            "timestamp": metadata["timestamp"],
            "standardized_nutrients": {},
            "processing_time_seconds": metadata.get("processing_time_seconds")
        }
        # Add debug metadata if available
        if "timing" in metadata or "tier_distribution" in metadata or "search_metrics" in metadata:
            result["debug"] = metadata
        return result
    
    def process_ingredients(self, ingredients: List[str], output_file: str = "nutrition_data.csv", 
                          format: str = "csv", limit: Optional[int] = None, 
                          start_from: int = 0, output_mode: str = "standard") -> Dict:
        """Process ingredients with enhanced logging and output"""
        # Add timestamp to output filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(output_file)[0]
        ext = os.path.splitext(output_file)[1]
        timestamped_output = f"{base_name}_{timestamp}{ext}"
        
        # Create log file name
        log_file = f"{base_name}_{timestamp}.log"
        self.log_file = log_file
        
        # Apply limits
        if start_from > 0:
            ingredients = ingredients[start_from:]
            self._log(f"Starting from index {start_from}")
        
        if limit:
            ingredients = ingredients[:limit]
            self._log(f"Processing {len(ingredients)} ingredients (limited)")
        
        self.stats["total"] = len(ingredients)
        
        results = []
        failed = []
        processing_times = []
        total_start_time = time.time()
        
        self._log(f"\n{'='*80}")
        self._log(f"PROCESSING {len(ingredients)} INGREDIENTS")
        self._log(f"Output file: {timestamped_output}")
        self._log(f"Log file: {log_file}")
        self._log(f"Start time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"{'='*80}\n")
        
        for i, ingredient in enumerate(ingredients, 1):
            self._log(f"\n[{i}/{len(ingredients)}]")
            
            try:
                nutrition_data = self.fetch_nutrition_for_ingredient(ingredient)
                processing_time = nutrition_data.get("processing_time_seconds", 0) if nutrition_data else 0
                processing_times.append(processing_time)
                
                if nutrition_data:
                    flag = nutrition_data.get("flag", "HIGH_CONFIDENCE")
                    if flag in ["HIGH_CONFIDENCE", "MID_CONFIDENCE"]:
                        results.append(nutrition_data)
                        self.stats["successful"] += 1
                    elif flag == "LOW_CONFIDENCE":
                        # LOW_CONFIDENCE means below 80% - don't allow mapping
                        results.append(nutrition_data)  # Include for record but mark as failed
                        failed.append(ingredient)
                        self.stats["failed"] += 1
                    else:
                        results.append(nutrition_data)  # Include failed with flag
                        failed.append(ingredient)
                        self.stats["failed"] += 1
                else:
                    failed.append(ingredient)
                    self.stats["failed"] += 1
            except Exception as e:
                self._log(f"[ERROR] Exception processing '{ingredient}': {e}")
                failed.append(ingredient)
                self.stats["failed"] += 1
            
            # Save progress periodically
            if i % 10 == 0:
                temp_output = timestamped_output.replace('.csv', '_temp.csv').replace('.json', '_temp.json')
                save_results_enhanced(results, temp_output, format, mode=output_mode)
                self._log(f"\n[PROGRESS] Saved: {len(results)} results, {len(failed)} failed")
        
        # Save final results
        if results:
            save_results_enhanced(results, timestamped_output, format, mode=output_mode)
            self._log(f"\n[SUCCESS] Saved {len(results)} results to {timestamped_output}")
        
        if failed:
            failed_file = timestamped_output.replace('.csv', '_failed.txt').replace('.json', '_failed.txt')
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(failed))
            self._log(f"[INFO] Saved {len(failed)} failed ingredients to {failed_file}")
        
        # Calculate total time
        total_time = time.time() - total_start_time
        self._log(f"\nEnd time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Print summary
        self._print_summary(total_time, processing_times)
        
        return {
            "total": self.stats["total"],
            "successful": self.stats["successful"],
            "failed": self.stats["failed"],
            "from_mappings": self.stats["from_mappings"],
            "from_search": self.stats["from_search"],
            "no_mapping_found": self.stats["no_mapping_found"],
            "results": results,
            "failed_ingredients": failed,
            "output_file": timestamped_output,
            "log_file": log_file
        }
    
    def _print_summary(self, total_time: float, processing_times: List[float]):
        """Print processing summary with timing information"""
        self._log(f"\n{'='*80}")
        self._log("PROCESSING SUMMARY")
        self._log(f"{'='*80}")
        self._log(f"Total processed: {self.stats['total']}")
        self._log(f"Successful: {self.stats['successful']} ({self.stats['successful']/self.stats['total']*100:.1f}%)")
        self._log(f"Failed/No Mapping: {self.stats['failed']} ({self.stats['failed']/self.stats['total']*100:.1f}%)")
        self._log(f"From mappings (fast path): {self.stats['from_mappings']}")
        self._log(f"From search: {self.stats['from_search']}")
        self._log(f"No mapping found: {self.stats['no_mapping_found']}")
        self._log(f"\n{'='*80}")
        self._log("TIMING INFORMATION")
        self._log(f"{'='*80}")
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            min_time = min(processing_times)
            max_time = max(processing_times)
            self._log(f"Total time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
            self._log(f"Average time per ingredient: {avg_time:.2f} seconds")
            self._log(f"Fastest ingredient: {min_time:.2f} seconds")
            self._log(f"Slowest ingredient: {max_time:.2f} seconds")
            self._log(f"Throughput: {self.stats['total']/total_time*60:.2f} ingredients/minute")
        self._log(f"{'='*80}")


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhanced USDA Nutrition Fetcher with semantic verification and nutritional similarity scoring"
    )
    parser.add_argument("--input", required=True, help="Input file with ingredients (CSV, TXT, or JSON)")
    parser.add_argument("--input-format", choices=["auto", "csv", "txt", "json"], default="auto", help="Input file format (auto-detect if not specified)")
    parser.add_argument("--output", default="nutrition_data.csv", help="Output file path (timestamp will be added)")
    parser.add_argument("--format", choices=["csv", "csv-standard", "csv-debug", "json", "json-clean", "json-debug", "json-batch"], default="csv", help="Output format")
    parser.add_argument("--output-mode", choices=["standard", "debug"], default="standard", help="Output mode (standard or debug) - for backward compatibility")
    parser.add_argument("--limit", type=int, help="Limit number of ingredients to process")
    parser.add_argument("--start-from", type=int, default=0, help="Start from this ingredient index")
    
    args = parser.parse_args()
    
    if not os.getenv("USDA_API_KEY"):
        print("[ERROR] USDA_API_KEY not found in environment!")
        sys.exit(1)
    
    print(f"Loading ingredients from {args.input}...")
    from utils.data_loader import load_ingredients_universal
    ingredients = load_ingredients_universal(args.input, format=args.input_format)
    print(f"Loaded {len(ingredients)} ingredients from {args.input_format if args.input_format != 'auto' else 'auto-detected'} format")
    
    orchestrator = EnhancedNutritionFetchOrchestrator()
    results = orchestrator.process_ingredients(
        ingredients,
        output_file=args.output,
        format=args.format,
        limit=args.limit,
        start_from=args.start_from,
        output_mode=args.output_mode
    )
    
    print(f"\n[COMPLETE] Processing finished!")
    print(f"Output: {results['output_file']}")
    print(f"Log: {results['log_file']}")
    return results


if __name__ == "__main__":
    main()

