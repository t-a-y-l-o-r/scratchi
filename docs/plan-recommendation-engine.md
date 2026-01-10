# Plan Recommendation Engine with Reasoning - Implementation Plan

## Overview

Build an agentic system that profiles users, matches their needs to insurance plans, and provides personalized recommendations with transparent, detailed reasoning chains.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input Layer                         │
│  (Natural language queries + structured preferences)        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              User Profiling Agent                           │
│  - Extracts family demographics                             │
│  - Identifies expected usage patterns                       │
│  - Determines priority weights                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Plan Data Ingestion & Storage                    │
│  - CSV parsing with Pydantic models                         │
│  - Plan index/search structure                              │
│  - Benefit normalization                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Multi-Agent Reasoning Pipeline                   │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ Coverage Agent  │  │ Cost Agent      │  │ Limit Agent  ││
│  │ - EHB analysis  │  │ - Copay/coins   │  │ - Quantity   ││
│  │ - Exclusions    │  │ - Annual max    │  │ - Time       ││
│  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘│
│           │                    │                   │        │
│           └────────────────────┴───────────────────┘        │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │ Scoring Orchestrator│                  │
│                    │ - Weighted scoring │                   │
│                    │ - Multi-criteria   │                   │
│                    └─────────┬──────────┘                   │
└──────────────────────────────┼──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            Reasoning Chain Builder                          │
│  - Generates explanations for each score component          │
│  - Identifies trade-offs and gaps                           │
│  - Creates human-readable reasoning                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Recommendation Formatter                       │
│  - Ranks plans by weighted score                           │
│  - Produces structured output with reasoning                │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Core Dependencies
- **pydantic** - Data validation and models
- **pandas** - CSV processing and data manipulation
- **langchain** (optional) - If using LLM for natural language understanding
- **numpy** - Numerical scoring calculations

### Development Dependencies
- **pytest** - Testing framework
- **mypy** - Type checking
- **ruff** - Linting and formatting

## Data Models

### User Profile Model
```python
@dataclass
class UserProfile:
    family_size: int
    children_count: int
    adults_count: int
    expected_usage: ExpectedUsage  # Low/Medium/High
    priorities: PriorityWeights  # Coverage, Cost, Limits
    required_benefits: list[str]  # e.g., ["Orthodontia - Child"]
    excluded_benefits_ok: list[str]  # Benefits they don't need
    preferred_cost_sharing: CostSharingPreference  # Prefer copay vs coinsurance
    budget_constraints: BudgetConstraints | None
```

### Plan Model (from CSV)
```python
class PlanBenefit(BaseModel):
    plan_id: str
    standard_component_id: str
    benefit_name: str
    is_covered: bool
    is_ehb: bool | None
    copay_inn_tier1: str | None
    copay_inn_tier2: str | None
    copay_outof_net: str | None
    coins_inn_tier1: str | None
    coins_inn_tier2: str | None
    coins_outof_net: str | None
    quant_limit_on_svc: bool | None
    limit_qty: float | None
    limit_unit: str | None
    exclusions: str | None
    explanation: str | None
    ehb_var_reason: str | None
    is_excl_from_inn_moop: bool | None
    is_excl_from_oon_moop: bool | None
```

### Aggregated Plan Model
```python
class Plan:
    plan_id: str
    standard_component_id: str
    benefits: dict[str, PlanBenefit]  # Keyed by benefit_name
    state_code: str
    issuer_id: str
    business_year: int
```

### Recommendation Output Model
```python
class Recommendation:
    plan: Plan
    overall_score: float
    rank: int
    reasoning_chain: ReasoningChain
    strengths: list[str]
    weaknesses: list[str]
    trade_offs: list[TradeOff]
    user_fit_score: dict[str, float]  # Coverage: 0.8, Cost: 0.6, etc.
```

### Reasoning Chain Model
```python
class ReasoningChain:
    coverage_analysis: CoverageAnalysis
    cost_analysis: CostAnalysis
    limit_analysis: LimitAnalysis
    exclusion_analysis: ExclusionAnalysis
    explanations: list[str]  # Human-readable explanations
```

## Implementation Phases

### Phase 1: Foundation
**Goal**: Data ingestion and basic models

1. **Create Pydantic models for CSV data**
   - `PlanBenefit` model matching CSV schema
   - CSV parser with validation
   - Handle missing/null values gracefully
   - Parse percentage strings ("35.00%") to floats
   - Handle "Not Applicable", "Not Covered" special values

2. **Build Plan aggregation**
   - Group CSV rows by PlanId
   - Create `Plan` objects with benefit dictionaries
   - Plan index for fast lookup

3. **Unit tests**
   - CSV parsing tests
   - Model validation tests
   - Edge case handling (empty values, malformed data)

**Deliverable**: Can load and validate plan data from CSV

---

### Phase 2: User Profiling (-2)
**Goal**: Extract user preferences and profile

1. **UserProfile model implementation**
   - Support structured input (dict/JSON)
   - Support natural language input (basic keyword extraction)
   - Default priority weights calculation

2. **User profiling agent**
   - Extract family composition
   - Infer expected usage from benefit requests
   - Calculate priority weights based on input

3. **Unit tests**
   - Profile creation from structured input
   - Profile creation from natural language (basic)

**Deliverable**: Can create user profiles from various input formats

---

### Phase 3: Scoring Agents (-3)
**Goal**: Individual scoring components

1. **Coverage Agent**
   - Score based on EHB coverage
   - Score based on required benefits coverage
   - Penalize excluded benefits
   - Score based on benefit breadth

2. **Cost Agent**
   - Extract and normalize cost-sharing values
   - Score based on copay preferences
   - Score based on coinsurance rates
   - Consider annual maximums from explanations

3. **Limit Agent**
   - Score quantity limits (more limits = lower score)
   - Score time-based limits
   - Consider if limits align with expected usage

4. **Exclusion Agent**
   - Analyze exclusion periods
   - Score based on exclusion complexity
   - Consider prior coverage requirements

5. **Scoring Orchestrator**
   - Weighted combination of agent scores
   - Normalize scores to 0-1 range
   - Handle missing data gracefully

**Deliverable**: Can score individual plans across multiple dimensions

---

### Phase 4: Reasoning Chain Builder (-4)
**Goal**: Generate human-readable explanations

1. **Reasoning template system**
   - Template-based explanation generation
   - Support for different explanation styles (detailed, concise)
   - Include specific plan details in explanations

2. **Reasoning chain components**
   - Coverage reasoning: "Plan covers 8/10 required benefits..."
   - Cost reasoning: "35% coinsurance for basic dental care..."
   - Limit reasoning: "2 exams per year limit may be restrictive..."
   - Trade-off identification: "Lower cost but excludes adult orthodontia"

3. **Gap analysis**
   - Identify missing benefits
   - Identify suboptimal cost-sharing
   - Identify restrictive limits

**Deliverable**: Can generate detailed reasoning chains for each plan

---

### Phase 5: Recommendation Engine
**Goal**: Rank and recommend plans

1. **Ranking algorithm**
   - Sort plans by overall weighted score
   - Handle ties with secondary criteria
   - Limit results to top N plans

2. **Recommendation formatter**
   - Create `Recommendation` objects
   - Generate strengths/weaknesses lists
   - Create comparison summaries

3. **Output formatting**
   - JSON output for API use
   - Human-readable text output
   - Markdown format for documentation

**Deliverable**: Complete recommendation pipeline

---

### Phase 6: CLI & Polish
**Goal**: User-facing interface and improvements

1. **CLI interface**
   - Command-line arguments for user profile
   - CSV file path specification
   - Output format options
   - Verbose/quiet modes

2. **Error handling**
   - Graceful handling of missing data
   - Clear error messages
   - Validation feedback

3. **Performance optimization**
   - Profile and optimize hot paths
   - Consider caching for repeated queries
   - Memory-efficient plan storage

4. **Documentation**
   - README with usage examples
   - API documentation
   - Example outputs

**Deliverable**: Production-ready CLI tool

---

### Phase 7: Advanced Features (Future)
**Optional enhancements**:

1. **LLM integration** (langchain)
   - Natural language user input parsing
   - More sophisticated explanation generation
   - Conversational interface

2. **Machine learning scoring**
   - Learn weights from user feedback
   - Personalized scoring based on historical data

3. **Plan comparison visualization**
   - Generate comparison tables
   - Visual scoring breakdowns

4. **Batch processing**
   - Process multiple user profiles
   - Generate comparison reports

## Scoring Algorithm Details

### Coverage Score (0-1)
```python
coverage_score = (
    required_benefits_covered_ratio * 0.4 +
    ehb_coverage_bonus * 0.2 +
    benefit_breadth_score * 0.2 +
    exclusion_penalty * 0.2
)
```

### Cost Score (0-1)
```python
cost_score = (
    copay_preference_alignment * 0.3 +
    coinsurance_rate_score * 0.3 +
    annual_maximum_score * 0.2 +
    out_of_network_cost_score * 0.2
)
```

### Limit Score (0-1)
```python
limit_score = (
    quantity_limit_score * 0.4 +
    time_limit_score * 0.3 +
    exclusion_period_penalty * 0.3
)
```

### Overall Score
```python
overall_score = (
    coverage_score * user_priorities.coverage_weight +
    cost_score * user_priorities.cost_weight +
    limit_score * user_priorities.limit_weight
)
```

## Example Output Format

```json
{
  "recommendations": [
    {
      "plan_id": "21989AK0080001-00",
      "rank": 1,
      "overall_score": 0.87,
      "user_fit_scores": {
        "coverage": 0.95,
        "cost": 0.80,
        "limits": 0.85
      },
      "strengths": [
        "Covers all 10 required benefits",
        "No charge for routine adult dental services",
        "Generous annual maximum ($1,000)"
      ],
      "weaknesses": [
        "20% coinsurance for basic adult care",
        "Adult orthodontia not covered"
      ],
      "reasoning": {
        "coverage": "Plan covers all required benefits including child orthodontia...",
        "cost": "Cost-sharing ranges from 0% (routine services) to 50% (major care)...",
        "limits": "Annual maximum of $1,000 applies to adult services only..."
      },
      "trade_offs": [
        {
          "aspect": "Child orthodontia coverage",
          "pro": "Covers medically necessary orthodontia at 50%",
          "con": "Only in-network coverage, out-of-network costs higher"
        }
      ]
    }
  ],
  "user_profile": {
    "family_size": 4,
    "children_count": 2,
    "adults_count": 2
  },
  "summary": "Found 12 plans matching your criteria. Top 3 recommendations..."
}
```

## Testing Strategy

### Unit Tests
- Each agent component (Coverage, Cost, Limit, Exclusion)
- Scoring algorithms with known inputs/outputs
- Model validation
- CSV parsing edge cases

### Integration Tests
- End-to-end recommendation pipeline
- User profile → recommendations flow
- Multiple plan scenarios

### Test Data
- Create synthetic test CSV with known characteristics
- Edge cases: missing data, unusual values, boundary conditions

### Performance Tests
- Large CSV files (1000+ plans)
- Multiple simultaneous recommendations

## Project Structure

```
src/scratchi/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── plan.py          # Plan, PlanBenefit models
│   ├── user.py          # UserProfile, PriorityWeights
│   └── recommendation.py # Recommendation, ReasoningChain
├── agents/
│   ├── __init__.py
│   ├── base.py          # Base agent protocol
│   ├── coverage.py      # Coverage scoring agent
│   ├── cost.py          # Cost scoring agent
│   ├── limit.py         # Limit scoring agent
│   └── exclusion.py     # Exclusion analysis agent
├── data/
│   ├── __init__.py
│   ├── loader.py        # CSV loading and parsing
│   └── normalizer.py    # Data normalization utilities
├── scoring/
│   ├── __init__.py
│   ├── orchestrator.py  # Scoring coordination
│   └── utils.py         # Scoring helper functions
├── reasoning/
│   ├── __init__.py
│   ├── builder.py       # Reasoning chain construction
│   └── templates.py     # Explanation templates
├── recommend/
│   ├── __init__.py
│   ├── engine.py        # Main recommendation engine
│   └── formatter.py     # Output formatting
└── cli/
    ├── __init__.py
    └── main.py          # CLI entry point

tests/
├── __init__.py
├── test_models/
├── test_agents/
├── test_data/
├── test_scoring/
├── test_reasoning/
└── test_recommend/

data/
├── sample.csv           # Sample data
└── benefits-and-cost-sharing-puf.csv  # Full dataset

docs/
└── plan-recommendation-engine.md  # This file
```

## Success Criteria

1. ✅ Can load and validate plan data from CSV
2. ✅ Can create user profiles from structured input
3. ✅ Can score plans across coverage, cost, and limits
4. ✅ Can generate human-readable reasoning chains
5. ✅ Can rank plans and provide top recommendations
6. ✅ CLI interface works with sample data
7. ✅ All unit tests pass
8. ✅ Code follows project style guide (PEP 8, type hints, etc.)

## Next Steps

1. Review and approve this plan
2. Set up project dependencies (`pyproject.toml`)
3. Create initial project structure
4. Begin Phase 1 implementation
