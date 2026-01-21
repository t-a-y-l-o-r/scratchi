# Restructuring Plan: CLI Tool → Full-Stack Web Application

## Executive Summary

This document outlines the plan to restructure the current CLI-based medical plan recommendation tool into a full-stack web application with Django REST Framework, React, PostgreSQL, Memcached, Celery, and RabbitMQ.

## Current Architecture Analysis

### Existing Components

1. **Data Layer**
   - CSV loader using Polars for high-performance parsing
   - Plan models (Plan, PlanBenefit) using Pydantic
   - Data validation and normalization

2. **Business Logic**
   - Scoring agents (Coverage, Cost, Limit, Exclusion)
   - Scoring orchestrator
   - Recommendation engine
   - Reasoning builder

3. **User Management**
   - UserProfile model with preferences
   - Priority weights and budget constraints

4. **CLI Interface**
   - Argument parsing
   - Output formatting (JSON, Markdown, Text)

### Key Strengths to Preserve
- High-performance CSV parsing with Polars
- Well-structured Pydantic models
- Comprehensive scoring system
- Extensive test coverage
- Type-safe codebase

## Target Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  - User Profile Setup                                        │
│  - Plan Browser/List                                         │
│  - Recommendations Display                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│              Django REST Framework API                       │
│  - Authentication & Authorization                            │
│  - User Profile Management                                   │
│  - Plan CRUD Operations                                      │
│  - Recommendations Endpoints                                │
└──────┬──────────────────────┬───────────────────────────────┘
       │                      │
       │                      │
┌──────▼──────────┐  ┌───────▼────────────┐
│   PostgreSQL    │  │    Memcached       │
│   - Plans       │  │    - Plan Cache    │
│   - Benefits    │  │    - User Cache    │
│   - Users       │  │    - Rec Cache     │
│   - Profiles    │  │                    │
└─────────────────┘  └────────────────────┘
       │
       │
┌──────▼──────────────────────────────────────┐
│         Celery Workers (Async)               │
│  - CSV Upload & Processing                   │
│  - Plan Data Import                          │
│  - Recommendation Generation                 │
└──────┬───────────────────────────────────────┘
       │
┌──────▼──────────┐
│   RabbitMQ      │
│   (Message Queue)│
└─────────────────┘
```

## Project Structure

### Proposed Directory Layout

```
scratchi/
├── backend/                          # Django backend
│   ├── api/                          # Django REST Framework app
│   │   ├── views/
│   │   │   ├── user_profile.py
│   │   │   ├── plans.py
│   │   │   ├── recommendations.py
│   │   │   └── admin_upload.py      # Hidden CSV upload endpoint
│   │   ├── serializers/
│   │   ├── permissions.py
│   │   └── urls.py
│   ├── core/                         # Core Django app
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── plan.py
│   │   │   ├── benefit.py
│   │   │   └── recommendation.py
│   │   ├── management/
│   │   │   └── commands/
│   │   └── migrations/
│   ├── tasks/                        # Celery tasks
│   │   ├── csv_processing.py
│   │   ├── plan_import.py
│   │   └── recommendation_generation.py
│   ├── services/                     # Business logic services
│   │   ├── recommendation_service.py
│   │   ├── plan_service.py
│   │   └── scoring_service.py
│   ├── adapters/                     # Adapters for existing code
│   │   ├── plan_adapter.py           # Convert DB models ↔ Pydantic models
│   │   └── recommendation_adapter.py
│   ├── config/                       # Django settings
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   ├── production.py
│   │   │   └── celery.py
│   │   └── urls.py
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/                         # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Profile/
│   │   │   ├── Plans/
│   │   │   └── Recommendations/
│   │   ├── services/                 # API client
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── App.jsx
│   ├── package.json
│   └── vite.config.js                 # or create-react-app
│
├── shared/                           # Shared code (if needed)
│   └── models/                       # Shared Pydantic models
│
├── legacy/                           # Original CLI code (preserved)
│   └── src/scratchi/                 # Current codebase
│
├── docker-compose.yml                # Development environment
├── .env.example
└── README.md
```

## Database Schema Design

### Core Models

#### User & Profile
```python
# User (Django's built-in User model extended)
- id, username, email, password, etc.

# UserProfile
- user (OneToOne to User)
- family_size
- adults_count
- children_count
- expected_usage (Enum: LOW, MEDIUM, HIGH)
- preferred_cost_sharing (Enum: COPAY, COINSURANCE, EITHER)
- coverage_weight, cost_weight, limit_weight (FloatField)
- created_at, updated_at
```

#### Plans & Benefits
```python
# Plan
- plan_id (CharField, unique, indexed)
- standard_component_id (CharField)
- state_code (CharField, indexed)
- issuer_id (CharField)
- business_year (IntegerField, indexed)
- created_at, updated_at

# PlanBenefit
- plan (ForeignKey to Plan, indexed)
- benefit_name (CharField, indexed)
- copay_inn_tier1, copay_inn_tier2, copay_outof_net (CharField, nullable)
- coins_inn_tier1, coins_inn_tier2, coins_outof_net (CharField, nullable)
- is_ehb, is_covered (CharField, nullable)
- quant_limit_on_svc (CharField, nullable)
- limit_qty (FloatField, nullable)
- limit_unit (CharField, nullable)
- exclusions, explanation, ehb_var_reason (TextField, nullable)
- is_excl_from_inn_moop, is_excl_from_oon_moop (CharField, nullable)
- created_at, updated_at

# Indexes:
# - Plan: (state_code, business_year), (issuer_id)
# - PlanBenefit: (plan_id, benefit_name), (plan_id, is_covered)
```

#### Recommendations
```python
# Recommendation
- id (AutoField)
- user (ForeignKey to User, indexed)
- plan (ForeignKey to Plan, indexed)
- overall_score (FloatField)
- rank (IntegerField)
- coverage_score, cost_score, limit_score, exclusion_score (FloatField)
- reasoning_chain (JSONField)  # Store ReasoningChain as JSON
- created_at, updated_at

# Indexes:
# - (user_id, created_at DESC) for user's recommendations
# - (user_id, overall_score DESC) for ranking queries
```

#### CSV Upload Tracking
```python
# CSVUpload
- id (AutoField)
- uploaded_by (ForeignKey to User)
- file_name (CharField)
- file_path (FileField)
- status (CharField: PENDING, PROCESSING, COMPLETED, FAILED)
- total_rows (IntegerField, nullable)
- processed_rows (IntegerField, nullable)
- error_message (TextField, nullable)
- created_at, updated_at, completed_at
```

## Migration Strategy

### Phase 1: Foundation Setup
**Goal**: Set up infrastructure and basic Django project

1. **Project Structure**
   - Create `backend/` directory with Django project
   - Set up Django apps: `api`, `core`, `tasks`
   - Configure Django settings (base, dev, prod)
   - Set up PostgreSQL connection
   - Configure Memcached
   - Set up Celery with RabbitMQ

2. **Database Models**
   - Create Django models for UserProfile, Plan, PlanBenefit, Recommendation
   - Create migrations
   - Set up database indexes
   - Create admin interface for data management

3. **Development Environment**
   - Docker Compose setup (PostgreSQL, RabbitMQ, Memcached)
   - Environment variable configuration
   - Development settings

### Phase 2: Data Layer Migration
**Goal**: Migrate CSV loading and data models to Django

1. **Adapter Layer**
   - Create adapters to convert between Django ORM models and Pydantic models
   - Preserve existing Pydantic models for business logic
   - Create service layer for data operations

2. **CSV Processing Task**
   - Create Celery task for async CSV processing
   - Migrate Polars-based CSV loader to work with Django
   - Store uploaded CSV files
   - Process CSV rows in batches
   - Create Plan and PlanBenefit records in database
   - Handle errors and track progress

3. **Admin Upload Endpoint**
   - Create hidden/admin-only endpoint for CSV upload
   - Return upload job ID
   - Allow status checking

4. **Caching Strategy**
   - Cache plan lists (by state, year)
   - Cache individual plans
   - Cache user profiles
   - Cache recommendations (with TTL)

### Phase 3: API Development
**Goal**: Build REST API endpoints

1. **Authentication & Authorization**
   - Set up Django REST Framework authentication
   - JWT or Session-based auth
   - Permission classes for admin endpoints

2. **User Profile API**
   - `GET /api/profile/` - Get current user's profile
   - `PUT /api/profile/` - Update profile
   - `POST /api/profile/` - Create profile

3. **Plans API**
   - `GET /api/plans/` - List plans (with filtering: state, year, issuer)
   - `GET /api/plans/{plan_id}/` - Get plan details
   - `GET /api/plans/{plan_id}/benefits/` - Get plan benefits

4. **Recommendations API**
   - `POST /api/recommendations/generate/` - Generate recommendations (async)
   - `GET /api/recommendations/` - List user's recommendations
   - `GET /api/recommendations/{id}/` - Get recommendation details
   - `GET /api/recommendations/status/{job_id}/` - Check generation status

5. **Admin API**
   - `POST /api/admin/upload-csv/` - Upload CSV (admin only)
   - `GET /api/admin/upload-status/{upload_id}/` - Check upload status

### Phase 4: Business Logic Integration
**Goal**: Integrate existing scoring and recommendation logic

1. **Service Layer**
   - Create `RecommendationService` that uses existing `RecommendationEngine`
   - Create `PlanService` for plan operations
   - Create `ScoringService` wrapper for scoring orchestrator

2. **Async Recommendation Generation**
   - Create Celery task for recommendation generation
   - Load plans from database
   - Convert to Pydantic models
   - Run existing recommendation engine
   - Store results in database
   - Cache recommendations

3. **Data Conversion**
   - Ensure seamless conversion between Django models and Pydantic models
   - Handle edge cases and data validation
   - Preserve all existing business logic

### Phase 5: Frontend Development
**Goal**: Build React frontend

1. **Project Setup**
   - Initialize React project (Vite or Create React App)
   - Set up routing (React Router)
   - Set up API client (Axios or Fetch)
   - Set up state management (Context API or Redux)

2. **User Profile Setup Page**
   - Form for family size, adults, children
   - Expected usage selection
   - Required benefits selection (multi-select)
   - Cost sharing preference
   - Priority weights (coverage/cost/limit sliders)
   - Budget constraints (optional)

3. **Plans List Page**
   - Table/list view of all plans
   - Filtering (state, year, issuer)
   - Search functionality
   - Pagination
   - Plan detail modal/page

4. **Recommendations Page**
   - Display ranked recommendations
   - Show scores (overall, coverage, cost, limit, exclusion)
   - Display reasoning chain
   - Show plan details
   - Allow regeneration

5. **Navigation & Layout**
   - Header with navigation
   - User menu
   - Responsive design

### Phase 6: Testing & Optimization
**Goal**: Ensure reliability and performance

1. **Backend Testing**
   - Unit tests for API endpoints
   - Integration tests for Celery tasks
   - Database query optimization
   - Cache hit rate monitoring

2. **Frontend Testing**
   - Component tests
   - Integration tests
   - E2E tests (optional)

3. **Performance Optimization**
   - Database query optimization (select_related, prefetch_related)
   - Caching strategy refinement
   - API response pagination
   - Frontend code splitting

4. **Error Handling**
   - Comprehensive error handling
   - User-friendly error messages
   - Logging and monitoring

## Technical Decisions

### 1. Preserving Existing Code
- **Decision**: Keep existing Pydantic models and business logic intact
- **Rationale**: Well-tested, type-safe code that works
- **Approach**: Create adapter layer to convert between Django ORM and Pydantic models

### 2. Database Choice
- **Decision**: PostgreSQL
- **Rationale**: 
  - Robust, production-ready
  - Excellent JSON support for reasoning chains
  - Strong indexing capabilities
  - Full-text search if needed later

### 3. Caching Strategy
- **Decision**: Memcached for simple key-value caching
- **Rationale**: Fast, simple, sufficient for current needs
- **Usage**:
  - Cache plan lists (key: `plans:state:{state}:year:{year}`)
  - Cache individual plans (key: `plan:{plan_id}`)
  - Cache recommendations (key: `recommendations:user:{user_id}`)
  - TTL: 1 hour for plans, 15 minutes for recommendations

### 4. Async Processing
- **Decision**: Celery + RabbitMQ
- **Rationale**: 
  - Industry standard for Django async tasks
  - Reliable message delivery
  - Good monitoring tools
- **Tasks**:
  - CSV processing (long-running)
  - Recommendation generation (can be slow with many plans)

### 5. API Authentication
- **Decision**: JWT tokens (or Django Session Auth)
- **Rationale**: 
  - JWT: Stateless, good for SPA
  - Session: Simpler, built-in to Django
  - Start with Session, migrate to JWT if needed

### 6. Frontend Framework
- **Decision**: React with modern tooling
- **Rationale**: 
  - Industry standard
  - Large ecosystem
  - Good performance
- **Stack**: React + React Router + Axios + Context API (or Zustand)

## Implementation Details

### CSV Upload Flow

```
1. Admin uploads CSV via POST /api/admin/upload-csv/
   → Returns: { upload_id: "uuid", status: "PENDING" }

2. Celery task processes CSV:
   - Read CSV with Polars (existing code)
   - Parse rows in batches (e.g., 1000 rows)
   - Create PlanBenefit records
   - Aggregate into Plan records
   - Update upload status

3. Client polls GET /api/admin/upload-status/{upload_id}/
   → Returns: { status: "PROCESSING", processed_rows: 5000, total_rows: 10000 }

4. On completion:
   → Status: "COMPLETED", total_rows: 10000, processed_rows: 10000
```

### Recommendation Generation Flow

```
1. User creates/updates profile via PUT /api/profile/

2. User requests recommendations via POST /api/recommendations/generate/
   → Returns: { job_id: "uuid", status: "PENDING" }

3. Celery task generates recommendations:
   - Load user profile
   - Load all plans (or filtered subset) from database
   - Convert to Pydantic models
   - Run RecommendationEngine (existing code)
   - Store recommendations in database
   - Cache results

4. Client polls GET /api/recommendations/status/{job_id}/
   → Returns: { status: "COMPLETED", recommendation_ids: [...] }

5. Client fetches recommendations via GET /api/recommendations/
```

### Data Model Conversion

```python
# Adapter pattern for converting between Django ORM and Pydantic

class PlanAdapter:
    @staticmethod
    def to_pydantic(django_plan: Plan) -> scratchi.models.plan.Plan:
        """Convert Django Plan model to Pydantic Plan model."""
        benefits = [
            PlanBenefitAdapter.to_pydantic(b) 
            for b in django_plan.benefits.all()
        ]
        return scratchi.models.plan.Plan.from_benefits(benefits)
    
    @staticmethod
    def from_pydantic(pydantic_plan: scratchi.models.plan.Plan) -> Plan:
        """Create/update Django Plan from Pydantic model."""
        # Implementation
```

## Dependencies

### Backend (requirements.txt)
```
Django>=5.0
djangorestframework>=3.14
django-cors-headers>=4.0
psycopg2-binary>=2.9
celery>=5.3
redis>=5.0  # For Celery broker (or use RabbitMQ directly)
python-memcached>=1.59
polars>=1.37.0  # Existing dependency
pydantic>=2.0.0  # Existing dependency
pydantic-settings>=2.0.0  # Existing dependency
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "@tanstack/react-query": "^5.0.0"
  }
}
```

## Migration Checklist

### Backend
- [ ] Set up Django project structure
- [ ] Configure PostgreSQL, Memcached, RabbitMQ
- [ ] Create database models
- [ ] Create migrations and run them
- [ ] Set up Celery
- [ ] Create adapter layer
- [ ] Migrate CSV loader to Celery task
- [ ] Create API endpoints
- [ ] Implement caching
- [ ] Write tests
- [ ] Set up admin interface

### Frontend
- [ ] Initialize React project
- [ ] Set up routing
- [ ] Create API client
- [ ] Build profile setup page
- [ ] Build plans list page
- [ ] Build recommendations page
- [ ] Add navigation
- [ ] Style with CSS/Tailwind
- [ ] Write tests
- [ ] Optimize bundle size

### Integration
- [ ] Connect frontend to backend
- [ ] Test end-to-end flows
- [ ] Performance testing
- [ ] Security review
- [ ] Documentation

## Risk Mitigation

### Risk 1: Data Migration Complexity
- **Mitigation**: Use adapter pattern to preserve existing models
- **Fallback**: Gradual migration, keep both systems running initially

### Risk 2: Performance with Large Datasets
- **Mitigation**: 
  - Batch processing for CSV uploads
  - Database indexing
  - Caching strategy
  - Pagination for API responses

### Risk 3: Async Task Failures
- **Mitigation**:
  - Comprehensive error handling
  - Task retry logic
  - Status tracking
  - Admin notifications

### Risk 4: Frontend-Backend Integration
- **Mitigation**:
  - Clear API contracts
  - API documentation (OpenAPI/Swagger)
  - Mock API for frontend development

## Success Criteria

1. ✅ Users can upload CSV files via admin endpoint
2. ✅ CSV processing happens asynchronously
3. ✅ Users can create and update profiles
4. ✅ Users can view all plans with filtering
5. ✅ Users can generate recommendations
6. ✅ Recommendations are generated asynchronously
7. ✅ All existing business logic is preserved
8. ✅ Performance is acceptable (<2s for API responses)
9. ✅ System handles errors gracefully
10. ✅ Code is well-tested and maintainable

## Next Steps

1. Review and approve this plan
2. Set up development environment
3. Begin Phase 1 implementation
4. Regular check-ins and adjustments

## Questions to Resolve

1. **Authentication**: JWT vs Session-based?
2. **Frontend Framework**: Any preference beyond React?
3. **Deployment**: Where will this be hosted? (affects some decisions)
4. **Admin Access**: How should admin authentication work?
5. **CSV Upload**: Should there be file size limits?
6. **Recommendations**: Should they be regenerated automatically when profile changes?
