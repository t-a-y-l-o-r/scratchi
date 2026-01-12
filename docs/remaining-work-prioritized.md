# Remaining Work - Prioritized

This document prioritizes the remaining recommendations from `recommendations-accuracy-robustness.md` based on:
- **Impact**: How much it improves accuracy/robustness
- **Risk**: What happens if we don't implement it
- **Effort**: How complex it is to implement
- **Dependencies**: What needs to be done first

## Tier 1: Quick Wins (High Impact, Low Effort) ⚡

These are easy to implement and provide immediate value for robustness.

### 1. Top-N Selection Edge Cases (4.2) - **HIGH PRIORITY**
- **Status**: ⚠️ Edge cases not tested
- **Effort**: ~30 minutes
- **Impact**: Prevents crashes with edge case inputs
- **Tasks**:
  - Test `top_n = 0` (should return empty list)
  - Test `top_n > total_plans` (should return all plans)
  - Test `top_n = None` (should return all plans)
  - Add validation/logging for edge cases
- **File**: `tests/test_recommend/test_engine.py` or new test file
- **Code Location**: `src/scratchi/recommend/engine.py:109-110`

### 2. Ranking Stability Explicit Test (4.1) - **HIGH PRIORITY**
- **Status**: ⚠️ Needs explicit determinism test
- **Effort**: ~30 minutes
- **Impact**: Ensures consistent results
- **Tasks**:
  - Add explicit test that identical inputs produce identical rankings
  - Test tie-breaking logic (when scores are equal)
  - Verify ranking is consistent across multiple runs
- **File**: `tests/test_recommend/test_engine.py`
- **Note**: We have determinism tests for scoring, but not for ranking

### 3. User Profile Validation Enhancements (5.2) - **MEDIUM PRIORITY**
- **Status**: ⚠️ Minor enhancements needed
- **Effort**: ~1 hour
- **Impact**: Prevents invalid user profiles
- **Tasks**:
  - Validate `required_benefits` list doesn't contain duplicates
  - Validate `excluded_benefits_ok` doesn't overlap with `required_benefits`
  - Add tests for these validations
- **File**: `src/scratchi/models/user.py` (add to `__post_init__`)
- **Test File**: `tests/test_models/test_user.py`

### 4. Empty Data Edge Cases (6.1) - **MEDIUM PRIORITY**
- **Status**: ⚠️ Minor additions possible
- **Effort**: ~1 hour
- **Impact**: Better edge case coverage
- **Tasks**:
  - Test CSV containing only header row
  - Test plans with no benefits (should this be allowed?)
  - Add appropriate error handling/logging
- **File**: `tests/test_data/test_loader.py`

## Tier 2: Medium Complexity (Important for Production) 🏗️

These require more effort but are important for production readiness.

### 5. Plan Data Validation (5.3) - **HIGH PRIORITY**
- **Status**: ❌ Not implemented
- **Effort**: ~2-3 hours
- **Impact**: Catches data quality issues early
- **Risk**: Invalid plans could cause scoring errors or crashes
- **Tasks**:
  - Validate plans have at least one benefit (in `Plan.from_benefits()`)
  - Validate `plan_id` is unique within a dataset
  - Validate `standard_component_id` matches `plan_id` prefix
  - Check for plans with all benefits marked "Not Covered" (may indicate data issue)
  - Validate cost-sharing consistency (copay OR coinsurance, not both for same tier)
  - Add validation function and tests
- **Files**:
  - `src/scratchi/models/plan.py` (add validation method)
  - `src/scratchi/data_loader/loader.py` (call validation after aggregation)
  - `tests/test_models/test_plan_validation.py` (new test file)

### 6. Boundary Value Testing (6.3) - **HIGH PRIORITY**
- **Status**: ❌ Not tested
- **Effort**: ~2-3 hours
- **Impact**: Ensures system handles extreme inputs
- **Risk**: System might fail with unexpected inputs
- **Tasks**:
  - Test very large family sizes (e.g., 20+)
  - Test `family_size = 1` (single person)
  - Test very large numbers of required benefits (100+)
  - Test plans with very large numbers of benefits (1000+)
  - Test extreme priority weights (e.g., `coverage_weight = 0.99`, others = 0.01)
  - Test very high/low coinsurance rates (0%, 100%)
  - Use property-based testing (Hypothesis) for some cases
- **File**: `tests/test_scoring/test_boundary_values.py` (new test file)

### 7. Invalid Data Handling (6.4) - **MEDIUM PRIORITY**
- **Status**: ⚠️ Partially tested
- **Effort**: ~2-3 hours
- **Impact**: Better error handling and security
- **Tasks**:
  - Test invalid enum values in CSV (e.g., "Maybe" for Yes/No field)
  - Test non-numeric values in numeric fields
  - Test extremely long strings in text fields
  - Test special characters, SQL injection attempts, XSS attempts in text fields
  - Ensure all validation errors are logged with context
- **Files**:
  - `tests/test_data/test_invalid_data.py` (new test file)
  - `src/scratchi/data_loader/loader.py` (enhance error handling)

### 8. CSV File Validation Edge Cases (5.1) - **MEDIUM PRIORITY**
- **Status**: ⚠️ Partially implemented
- **Effort**: ~2-3 hours
- **Impact**: Better handling of malformed CSV files
- **Tasks**:
  - Test CSV files with wrong encoding (UTF-8 vs Latin-1)
  - Test very large CSV files (memory efficiency)
  - Test CSV files with special characters, quotes, newlines in fields
  - Add progress logging for large file processing
  - Test CSV files with missing required columns (enhance existing tests)
- **File**: `tests/test_data/test_loader.py` (enhance existing tests)

## Tier 3: Complex but Valuable (Long-term Maintenance) 🔧

These require significant effort but provide long-term value.

### 9. Data Quality Checks (10.1, 10.2) - **MEDIUM PRIORITY**
- **Status**: ❌ Not implemented
- **Effort**: ~4-6 hours
- **Impact**: Helps identify data issues proactively
- **Tasks**:
  - Add checks for duplicate `plan_ids` in CSV
  - Check for plans with inconsistent metadata (same `plan_id`, different `state_code`)
  - Verify benefit names are consistent across plans
  - Check for plans with cost-sharing that doesn't make sense (e.g., 0% coinsurance AND $0 copay)
  - Report percentage of plans with missing cost information
  - Report percentage of plans with missing limit information
  - Identify benefits that are rarely covered (may indicate data issue)
  - Generate data quality report after CSV loading
- **Files**:
  - `src/scratchi/data_loader/quality.py` (new module)
  - `tests/test_data/test_quality.py` (new test file)

### 10. Regression Testing (9.2) - **MEDIUM PRIORITY**
- **Status**: ❌ Not implemented
- **Effort**: ~4-6 hours
- **Impact**: Prevents regressions in scoring logic
- **Tasks**:
  - Create golden test files: known inputs → expected outputs
  - Store expected scores for a set of test plans
  - Verify scores don't change unexpectedly
  - Add integration tests that verify end-to-end pipeline produces expected results
  - Version control test data and expected outputs
- **Files**:
  - `tests/test_regression/` (new test directory)
  - `tests/test_regression/golden_tests.py`
  - `tests/test_regression/fixtures/` (test data)

### 11. Real-World Data Testing (9.1) - **MEDIUM PRIORITY**
- **Status**: ❌ Not implemented
- **Effort**: ~3-4 hours
- **Impact**: Validates system with actual data
- **Tasks**:
  - Create test fixtures from real CSV data (anonymized if needed)
  - Test with full dataset (`benefits-and-cost-sharing-puf.csv`)
  - Verify that all plans in real dataset can be loaded and scored
  - Test with diverse user profiles (different family sizes, priorities, requirements)
- **Files**:
  - `tests/test_integration/test_real_world_data.py` (new test file)
  - `tests/fixtures/real_data/` (test data directory)

## Tier 4: Nice to Have (Lower Priority) 📚

These are valuable but not critical for core functionality.

### 12. Comprehensive Logging Enhancements (8.1) - **LOW PRIORITY**
- **Status**: ⚠️ Basic logging exists
- **Effort**: ~2-3 hours
- **Impact**: Better observability
- **Tasks**:
  - Log data quality issues: missing fields, invalid values, parsing warnings
  - Log scoring decisions: why a plan scored high/low (at DEBUG level)
  - Log recommendation generation: number of plans evaluated, top scores
  - Add structured logging with context (plan_id, user_profile_id, etc.)
  - Log performance metrics: processing time, memory usage
- **Note**: We already have good logging, this is about enhancing it

### 13. Test Coverage Measurement (11.1) - **LOW PRIORITY**
- **Status**: ❌ Not measured
- **Effort**: ~1 hour (setup) + ongoing
- **Impact**: Identify untested code
- **Tasks**:
  - Set up `coverage.py` in CI/CD
  - Aim for >90% code coverage
  - Add coverage reports to CI/CD
  - Document coverage goals
- **File**: `pyproject.toml` (add coverage config)

### 14. Documentation Enhancements (12.1) - **LOW PRIORITY**
- **Status**: ⚠️ Partially documented
- **Effort**: ~2-3 hours
- **Impact**: Better developer experience
- **Tasks**:
  - Document edge case handling (what happens when data is missing)
  - Add examples showing how scores are calculated
  - Document known limitations
  - Document performance characteristics
- **Files**: `docs/plan-recommendation-engine.md`

### 15. Performance Testing (7.1, 7.2) - **LOW PRIORITY**
- **Status**: ❌ Not implemented
- **Effort**: ~3-4 hours
- **Impact**: Ensures system scales
- **Tasks**:
  - Add performance tests with large datasets (10K+ plans, 100K+ benefits)
  - Profile memory usage during CSV loading
  - Profile scoring time per plan
  - Add performance benchmarks to CI/CD
  - Consider parallelizing plan scoring (if thread-safe)
- **Note**: Important for production but not blocking

### 16. Mutation Testing (11.1) - **LOW PRIORITY**
- **Status**: ❌ Not implemented
- **Effort**: ~2-3 hours (setup) + ongoing
- **Impact**: Verifies test quality
- **Tasks**:
  - Set up mutation testing tool (e.g., `mutmut`)
  - Run mutation tests periodically
  - Document mutation testing strategy
- **Note**: Advanced testing technique, nice to have

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 days)
1. Top-N Selection Edge Cases (1)
2. Ranking Stability Explicit Test (2)
3. User Profile Validation Enhancements (3)
4. Empty Data Edge Cases (4)

### Phase 2: Production Readiness (1 week)
5. Plan Data Validation (5)
6. Boundary Value Testing (6)
7. Invalid Data Handling (7)
8. CSV File Validation Edge Cases (8)

### Phase 3: Long-term Maintenance (1-2 weeks)
9. Data Quality Checks (9)
10. Regression Testing (10)
11. Real-World Data Testing (11)

### Phase 4: Polish (as needed)
12-16. Nice to have items

## Summary

**Total Estimated Effort**: ~30-40 hours for all items

**Critical Path** (must-do for production):
- Tier 1 items (Quick Wins)
- Tier 2 items (Production Readiness)

**Can Defer**:
- Tier 3 items (can be done incrementally)
- Tier 4 items (nice to have)

## Notes

- **Copay Amount Parsing (2.2)**: Currently stored as strings, parsing may not be needed. Defer unless requirements change.
- **Date Parsing Additional Formats (2.3)**: Would require parser enhancement. Defer unless needed for actual data.
- **Partial Benefit Name Matching (3.1)**: Not implemented by design (exact normalized match required). Document as known limitation.
- **Duplicate Benefit Names (3.2)**: Should be validated. Can add to Plan Data Validation (5).
