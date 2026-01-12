# Output Quality Improvements - Plan of Attack

## Overview

This document outlines a plan to fix issues identified in the recommendation output format, specifically from `data/sample-out.txt`. The goal is to improve clarity, accuracy, and usefulness of the generated reports.

## Issues Identified

### Critical Bugs

1. **Duplicate benefit names in reasoning** (Lines 24, 48, 72, 96)
   - **Issue**: "Restrictive limits found on: Hearing Aids, Hearing Aids"
   - **Root Cause**: `ReasoningBuilder._analyze_limits()` adds benefit names to `restrictive_limits` list twice if a benefit has both quantity and time limits (lines 238-239 and 248-249)
   - **Impact**: Confusing output, inaccurate count

2. **Weaknesses count mismatch** (Lines 19, 43, 67, 91)
   - **Issue**: Weaknesses say "Restrictive limits on 2 benefit(s)" but reasoning shows only one unique benefit (duplicated)
   - **Root Cause**: Count uses `len(restrictive_limits)` but list contains duplicates
   - **Impact**: Misleading information

3. **Identical plans with identical scores** (Rank #1 vs Rank #2)
   - **Issue**: Two different plans (47501TX0030008-02 and 47501TX0030009-02) have identical scores, strengths, weaknesses, and reasoning
   - **Root Cause**: Need to investigate ranking/tie-breaking logic
   - **Impact**: Unclear differentiation, user confusion

### Usability Issues

4. **No plan names/descriptions**
   - **Issue**: Only cryptic plan IDs like "47501TX0030008-02" are shown
   - **Root Cause**: Plan model doesn't include human-readable names
   - **Impact**: Difficult to reference plans in conversations

5. **Missing user context in output**
   - **Issue**: No summary of user needs/preferences shown
   - **Root Cause**: `format_recommendations_text()` doesn't include user_profile in output
   - **Impact**: Hard to understand why scores matter

6. **No differentiation between similar-scoring plans**
   - **Issue**: Plans with very similar scores (94.75% vs 94.42%) look nearly identical
   - **Root Cause**: Missing comparison/differentiation logic
   - **Impact**: Unclear why one plan ranks higher

7. **"Generous" without context**
   - **Issue**: "$50,000 annual maximum" labeled as "Generous" with no baseline
   - **Root Cause**: Hard-coded threshold in `_identify_strengths()` (line 375: `>= 3000`)
   - **Impact**: Meaningless without comparison or user context

8. **Formulaic/repetitive reasoning**
   - **Issue**: Very similar text across all plans
   - **Root Cause**: Template-based explanations lack plan-specific insights
   - **Impact**: Generic, not helpful for decision-making

9. **Missing actionable information**
   - **Issue**: No next steps, cost estimates, or comparison tools
   - **Root Cause**: Output format focused only on scoring
   - **Impact**: Users don't know what to do next

10. **Unclear percentage explanations**
    - **Issue**: "78% of total benefits" - 78% of what total? How many benefits total?
    - **Root Cause**: Missing context in `format_coverage_explanation()` (line 53)
    - **Impact**: Confusing statistics

11. **Weaknesses section lacks detail**
    - **Issue**: Says "Restrictive limits on 2 benefit(s)" but doesn't specify which benefits in the weaknesses section
    - **Root Cause**: Weaknesses list doesn't include specific benefit names (line 427 in builder.py)
    - **Impact**: Users must read reasoning section to find details

12. **Extra blank lines at end of file**
    - **Issue**: Two empty lines at end (lines 100-101)
    - **Root Cause**: Formatter adds separator after last item
    - **Impact**: Minor formatting issue

## Implementation Plan

### Phase 1: Fix Critical Bugs (High Priority)

**Goal**: Fix data accuracy and duplicate issues

#### Task 1.1: Fix duplicate benefit names in restrictive_limits
- **File**: `src/scratchi/reasoning/builder.py`
- **Location**: `_analyze_limits()` method (lines 215-256)
- **Fix**: Use a set to track restrictive_limits, convert to list at end
- **Changes**:
  ```python
  restrictive_limits: set[str] = set()  # Use set instead of list
  # ... add benefits to set ...
  restrictive_limits.add(benefit.benefit_name)  # Won't add duplicates
  # Convert to sorted list at end for deterministic output
  return LimitAnalysis(
      ...
      restrictive_limits=sorted(list(restrictive_limits)),
  )
  ```
- **Testing**: Add test case with benefit having both quantity and time limits
- **Estimated Effort**: 1 hour

#### Task 1.2: Fix weaknesses count accuracy
- **File**: `src/scratchi/reasoning/builder.py`
- **Location**: `_identify_weaknesses()` method (line 427)
- **Fix**: Count will automatically be correct after Task 1.1, but verify logic
- **Testing**: Verify count matches actual number of unique benefits
- **Estimated Effort**: 30 minutes (mostly verification)

#### Task 1.3: Investigate identical plan scores
- **Files**: `src/scratchi/recommend/engine.py`, `src/scratchi/scoring/orchestrator.py`
- **Goal**: Understand why two different plans have identical scores
- **Actions**:
  - Add logging to compare plan characteristics
  - Check if plans are truly identical or if scoring is too coarse
  - Implement tie-breaking logic if needed
- **Testing**: Test with plans that should have identical scores vs. similar scores
- **Estimated Effort**: 2-3 hours

### Phase 2: Improve Output Clarity (Medium Priority)

**Goal**: Make output more readable and informative

#### Task 2.1: Add specific benefit names to weaknesses
- **File**: `src/scratchi/reasoning/builder.py`
- **Location**: `_identify_weaknesses()` method (lines 425-428)
- **Fix**: Include specific benefit names in weakness text
- **Changes**:
  ```python
  if limit_analysis.restrictive_limits:
      if len(limit_analysis.restrictive_limits) == 1:
          weaknesses.append(f"Restrictive limits on: {limit_analysis.restrictive_limits[0]}")
      elif len(limit_analysis.restrictive_limits) <= 3:
          weaknesses.append(f"Restrictive limits on: {', '.join(limit_analysis.restrictive_limits)}")
      else:
          weaknesses.append(
              f"Restrictive limits on {len(limit_analysis.restrictive_limits)} benefits: "
              f"{', '.join(limit_analysis.restrictive_limits[:2])}, and {len(limit_analysis.restrictive_limits) - 2} more"
          )
  ```
- **Testing**: Test with 1, 2, 3, and many restrictive limits
- **Estimated Effort**: 1 hour

#### Task 2.2: Improve percentage clarity in explanations
- **File**: `src/scratchi/reasoning/templates.py`
- **Location**: `format_coverage_explanation()` method (line 53)
- **Fix**: Include total benefit count in explanation
- **Changes**:
  ```python
  parts.append(
      f"Plan includes {analysis.ehb_benefits_count} Essential Health Benefits "
      f"({ehb_ratio:.0%} of {analysis.total_benefits_count} total benefits).",
  )
  ```
- **Testing**: Verify explanation is clearer
- **Estimated Effort**: 30 minutes

#### Task 2.3: Add user context to text output
- **File**: `src/scratchi/recommend/formatter.py`
- **Location**: `format_recommendations_text()` method (lines 78-139)
- **Fix**: Add user profile summary at top if provided
- **Changes**:
  ```python
  if user_profile:
      lines.append("User Profile:")
      lines.append(f"  Family Size: {user_profile.get('family_size', 'N/A')}")
      lines.append(f"  Expected Usage: {user_profile.get('expected_usage', 'N/A')}")
      # Add more relevant context
      lines.append("")
  ```
- **Testing**: Test with and without user_profile
- **Estimated Effort**: 1 hour

#### Task 2.4: Remove extra blank lines at end
- **File**: `src/scratchi/recommend/formatter.py`
- **Location**: `format_recommendations_text()` method (lines 136-139)
- **Fix**: Don't add separator after last recommendation
- **Changes**: Only add separator if not last item
- **Testing**: Verify no extra blank lines
- **Estimated Effort**: 15 minutes

### Phase 3: Enhance Differentiation (Medium Priority)

**Goal**: Help users understand differences between similar plans

#### Task 3.1: Add plan comparison/differentiation
- **Files**: `src/scratchi/recommend/formatter.py`, `src/scratchi/recommend/engine.py`
- **Goal**: Highlight key differences between consecutive plans
- **Approach**:
  - Compare adjacent plans in ranking
  - Identify key differentiators (coverage gaps, cost differences, etc.)
  - Add "Key Differences" section to output
- **Implementation**:
  - Create `_compare_plans()` function in formatter
  - Add comparison logic to identify top 2-3 differences
  - Include in text output between plans
- **Testing**: Test with plans that have similar scores
- **Estimated Effort**: 3-4 hours

#### Task 3.2: Improve "Generous" threshold with context
- **File**: `src/scratchi/reasoning/builder.py`
- **Location**: `_identify_strengths()` method (line 375)
- **Fix**: Either:
  - Remove subjective terms, use objective descriptions ("$50,000 annual maximum")
  - OR compare against dataset average/percentile
- **Approach**: Prefer removing subjective terms, keep objective facts
- **Changes**:
  ```python
  if cost_analysis.annual_maximum is not None:
      strengths.append(f"Annual maximum: ${cost_analysis.annual_maximum:,.0f}")
  ```
- **Testing**: Verify output is more objective
- **Estimated Effort**: 30 minutes

#### Task 3.3: Add tie-breaking logic for ranking
- **File**: `src/scratchi/recommend/engine.py`
- **Goal**: Break ties using secondary criteria
- **Approach**: If scores are identical (within epsilon), use:
  1. Higher coverage score
  2. Lower cost (if applicable)
  3. Fewer restrictive limits
  4. Alphabetical by plan_id (last resort)
- **Testing**: Test with plans that have identical scores
- **Estimated Effort**: 2 hours

### Phase 4: Future Enhancements (Low Priority)

**Goal**: Additional improvements for better UX

#### Task 4.1: Add plan names/descriptions
- **Files**: `src/scratchi/models/plan.py`, data loading code
- **Goal**: Include human-readable plan names if available in data
- **Approach**:
  - Check if CSV has plan name/description columns
  - Add to Plan model if available
  - Include in output
- **Note**: May require data source changes
- **Estimated Effort**: 2-3 hours (if data available)

#### Task 4.2: Make reasoning more plan-specific
- **Files**: `src/scratchi/reasoning/templates.py`, `src/scratchi/reasoning/builder.py`
- **Goal**: Generate more unique, insightful reasoning per plan
- **Approach**:
  - Identify unique aspects of each plan
  - Highlight specific benefits/features that stand out
  - Reduce generic template language
- **Estimated Effort**: 4-6 hours

#### Task 4.3: Add actionable next steps
- **File**: `src/scratchi/recommend/formatter.py`
- **Goal**: Include guidance on next steps
- **Approach**:
  - Add summary section with recommended actions
  - Include comparison table suggestions
  - Add links/contact info if applicable
- **Estimated Effort**: 2-3 hours

#### Task 4.4: Add cost estimate context
- **Files**: Multiple (cost agent, formatter)
- **Goal**: Include estimated costs or cost ranges
- **Approach**: This may require additional data or calculations
- **Note**: Depends on available data
- **Estimated Effort**: 4-6 hours (if data available)

## Implementation Order

### Sprint 1 (Critical Fixes)
1. Task 1.1: Fix duplicate benefit names
2. Task 1.2: Fix weaknesses count
3. Task 1.3: Investigate identical plan scores
4. Task 2.1: Add specific benefit names to weaknesses
5. Task 2.4: Remove extra blank lines

### Sprint 2 (Clarity Improvements)
1. Task 2.2: Improve percentage clarity
2. Task 2.3: Add user context to output
3. Task 3.2: Improve "Generous" threshold
4. Task 3.3: Add tie-breaking logic

### Sprint 3 (Enhancements)
1. Task 3.1: Add plan comparison/differentiation
2. Task 4.1: Add plan names (if data available)
3. Task 4.2: Make reasoning more plan-specific

### Future Sprints
- Task 4.3: Add actionable next steps
- Task 4.4: Add cost estimate context

## Testing Strategy

### Unit Tests
- Test `_analyze_limits()` with benefits having both quantity and time limits
- Test weaknesses generation with various limit scenarios
- Test tie-breaking logic with identical scores
- Test formatting functions with edge cases

### Integration Tests
- Test end-to-end pipeline with sample data
- Verify output matches expected format
- Test with plans that have identical scores
- Test with various user profiles

### Manual Testing
- Review sample output after each phase
- Verify output is clearer and more useful
- Check for any regressions

## Success Criteria

1. ✅ No duplicate benefit names in output
2. ✅ Weaknesses count matches actual number of unique benefits
3. ✅ Plans with identical scores are differentiated or clearly explained
4. ✅ Weaknesses include specific benefit names
5. ✅ Percentages include context (e.g., "78% of 67 total benefits")
6. ✅ User context included in output when available
7. ✅ No extra blank lines at end of file
8. ✅ Plans with similar scores show key differences
9. ✅ Output uses objective language instead of subjective terms
10. ✅ Tie-breaking works correctly for identical scores

## Files to Modify

### Core Changes
- `src/scratchi/reasoning/builder.py` - Fix duplicates, improve strengths/weaknesses
- `src/scratchi/reasoning/templates.py` - Improve explanation clarity
- `src/scratchi/recommend/formatter.py` - Add user context, improve formatting
- `src/scratchi/recommend/engine.py` - Add tie-breaking logic

### Testing
- `tests/test_reasoning/test_builder.py` - Add tests for duplicate fixes
- `tests/test_recommend/test_formatter.py` - Test formatting improvements
- `tests/test_recommend/test_engine.py` - Test tie-breaking

## Notes

- All changes should maintain backward compatibility with existing code
- Follow project coding standards (type hints, docstrings, etc.)
- Update existing tests and add new ones as needed
- Consider performance impact of comparison logic
- Some enhancements (plan names, cost estimates) may depend on data availability
