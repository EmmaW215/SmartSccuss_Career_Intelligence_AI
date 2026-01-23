# SmartSuccess.AI - AI Skills Lab
## Technical Design Plan

**Document Version:** 1.0  
**Created:** January 22, 2026  
**Status:** Ready for Implementation  
**Target Completion:** 20 weeks

---

# Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Database Design](#3-database-design)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [Backend Services](#5-backend-services)
6. [AI Workspace Implementation](#6-ai-workspace-implementation)
7. [AI Scoring Engine](#7-ai-scoring-engine)
8. [Frontend Implementation](#8-frontend-implementation)
9. [API Reference](#9-api-reference)
10. [Deployment & Infrastructure](#10-deployment--infrastructure)
11. [Testing Strategy](#11-testing-strategy)
12. [Implementation Checklist](#12-implementation-checklist)

---

# 1. Architecture Overview

## 1.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CDN (Vercel Edge Network)                                │
│                         - Static assets caching                                  │
│                         - Global distribution                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────────┐
│      FRONTEND (Vercel)            │   │        API GATEWAY (Vercel)            │
│      Next.js 15 App Router        │   │        Edge Functions                  │
│                                   │   │        - Rate Limiting                 │
│  Pages:                           │   │        - Auth Middleware               │
│  ├── / (Landing)                  │   │        - Request Validation            │
│  ├── /auth/* (Login/Register)     │   │                                        │
│  ├── /dashboard/*                 │   │  Routes:                               │
│  ├── /workspace/:id               │   │  ├── /api/auth/*                       │
│  ├── /results/:id                 │   │  ├── /api/tasks/*                      │
│  └── /business/*                  │   │  ├── /api/assessments/*                │
│                                   │   │  ├── /api/ai/*                         │
│  Components:                      │   │  └── /api/business/*                   │
│  ├── AIWorkspace                  │   │                                        │
│  ├── ScoreCard                    │   └───────────────┬───────────────────────┘
│  └── ComparisonView               │                   │
└───────────────────────────────────┘                   │
                                                        │
                    ┌───────────────────────────────────┴───────────────────┐
                    │                                                       │
                    ▼                                                       ▼
┌─────────────────────────────────────────┐   ┌─────────────────────────────────────┐
│        CORE BACKEND (Render)            │   │      EXECUTION SANDBOX (Fly.io)     │
│        FastAPI + Python 3.11            │   │      Docker Containers              │
│                                         │   │                                     │
│  Services:                              │   │  Per-Session Container:             │
│  ├── TaskService                        │   │  ├── Node.js 20 runtime             │
│  ├── AssessmentService                  │   │  ├── Python 3.11 runtime            │
│  ├── ScoringService                     │   │  ├── Isolated filesystem            │
│  ├── InvitationService                  │   │  ├── Network restrictions           │
│  └── ReportService                      │   │  ├── Resource limits                │
│                                         │   │  │   - CPU: 1 core                  │
│  Endpoints:                             │   │  │   - Memory: 2GB                  │
│  ├── POST /tasks                        │   │  │   - Timeout: 4 hours             │
│  ├── POST /assessments/start            │   │  └── Auto-cleanup on complete       │
│  ├── POST /assessments/:id/submit       │   │                                     │
│  ├── GET /assessments/:id/score         │   │  WebSocket: Real-time terminal      │
│  └── POST /scoring/evaluate             │   │                                     │
└──────────────────┬──────────────────────┘   └──────────────────┬──────────────────┘
                   │                                              │
                   │         ┌────────────────────────────────────┘
                   │         │
                   ▼         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────────┐  │
│  │    PostgreSQL       │  │      Redis          │  │    Cloudflare R2        │  │
│  │    (Supabase)       │  │    (Upstash)        │  │    (S3-compatible)      │  │
│  │                     │  │                     │  │                         │  │
│  │  Tables:            │  │  Keys:              │  │  Buckets:               │  │
│  │  ├── users          │  │  ├── session:*      │  │  ├── task-files/        │  │
│  │  ├── tasks          │  │  ├── rate:*         │  │  ├── submissions/       │  │
│  │  ├── assessments    │  │  ├── cache:*        │  │  ├── tracking-data/     │  │
│  │  ├── invitations    │  │  └── ws:*           │  │  └── reports/           │  │
│  │  ├── scores         │  │                     │  │                         │  │
│  │  └── api_keys       │  │                     │  │                         │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL SERVICES                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐  │
│  │   Anthropic     │  │    OpenAI       │  │     Clerk       │  │  Resend    │  │
│  │   Claude API    │  │    GPT API      │  │   Auth Service  │  │  Email     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1.2 Data Flow Diagrams

### Assessment Flow
```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         ASSESSMENT DATA FLOW                                      │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  1. START ASSESSMENT                                                              │
│  ─────────────────                                                                │
│  User clicks "Start" → API creates session → Sandbox container spawned           │
│       │                      │                        │                           │
│       │                      ▼                        ▼                           │
│       │               PostgreSQL:              Fly.io:                            │
│       │               INSERT assessment        docker run sandbox                 │
│       │               status='in_progress'     with volume mount                  │
│       │                                                                           │
│  2. DURING ASSESSMENT                                                             │
│  ────────────────────                                                             │
│                                                                                   │
│  ┌─────────────┐    WebSocket    ┌─────────────┐    HTTP    ┌─────────────┐      │
│  │  Workspace  │◀──────────────▶│  API Server │◀──────────▶│   Sandbox   │      │
│  │  (Browser)  │                │             │            │  Container  │      │
│  └──────┬──────┘                └──────┬──────┘            └─────────────┘      │
│         │                              │                                         │
│         │ Every 30 seconds:            │                                         │
│         │ - Code snapshot              │                                         │
│         │ - AI interactions            ▼                                         │
│         │                        ┌─────────────┐                                 │
│         └───────────────────────▶│    Redis    │ (temp storage)                  │
│                                  └──────┬──────┘                                 │
│                                         │ Batch write every 5 min                │
│                                         ▼                                        │
│                                  ┌─────────────┐                                 │
│                                  │ Cloudflare  │                                 │
│                                  │     R2      │                                 │
│                                  └─────────────┘                                 │
│                                                                                   │
│  3. SUBMIT & SCORE                                                               │
│  ────────────────                                                                 │
│                                                                                   │
│  User submits → Finalize tracking data → Trigger scoring pipeline                │
│       │                │                        │                                │
│       ▼                ▼                        ▼                                │
│  PostgreSQL:     Cloudflare R2:          Scoring Service:                        │
│  UPDATE status   Upload final            1. Fetch tracking data                  │
│  ='submitted'    tracking JSON           2. Run AI evaluators                    │
│                                          3. Calculate scores                     │
│                                          4. Generate report                      │
│                                                 │                                │
│                                                 ▼                                │
│                                          PostgreSQL:                             │
│                                          INSERT scores                           │
│                                          UPDATE status='scored'                  │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

# 2. Technology Stack

## 2.1 Frontend Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | Next.js | 15.x | React framework with App Router |
| Language | TypeScript | 5.x | Type safety |
| Styling | Tailwind CSS | 4.x | Utility-first CSS |
| UI Components | shadcn/ui | latest | Pre-built accessible components |
| State Management | Zustand | 4.x | Lightweight state management |
| Code Editor | Monaco Editor | 0.45.x | VS Code editor component |
| Terminal | Xterm.js | 5.x | Terminal emulator |
| Charts | Recharts | 2.x | Data visualization |
| Forms | React Hook Form | 7.x | Form handling |
| Validation | Zod | 3.x | Schema validation |
| HTTP Client | Axios | 1.x | API requests |
| WebSocket | Socket.io Client | 4.x | Real-time communication |

## 2.2 Backend Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | FastAPI | 0.109.x | High-performance Python API |
| Language | Python | 3.11 | Backend language |
| ORM | SQLAlchemy | 2.x | Database ORM |
| Migrations | Alembic | 1.x | Database migrations |
| Validation | Pydantic | 2.x | Data validation |
| Background Jobs | Celery | 5.x | Async task processing |
| WebSocket | python-socketio | 5.x | Real-time communication |
| HTTP Client | httpx | 0.26.x | Async HTTP requests |

## 2.3 Infrastructure Stack

| Service | Provider | Purpose |
|---------|----------|---------|
| Frontend Hosting | Vercel | Next.js deployment |
| Backend Hosting | Render | FastAPI deployment |
| Code Execution | Fly.io | Docker container execution |
| Database | Supabase | PostgreSQL hosting |
| Cache | Upstash | Redis hosting |
| File Storage | Cloudflare R2 | S3-compatible object storage |
| Auth | Clerk | Authentication service |
| Email | Resend | Transactional emails |
| Monitoring | Sentry | Error tracking |
| Analytics | PostHog | Product analytics |

## 2.4 Development Tools

| Tool | Purpose |
|------|---------|
| pnpm | Package manager (frontend) |
| Poetry | Package manager (backend) |
| Docker | Local development containers |
| GitHub Actions | CI/CD pipelines |
| Prisma (optional) | Database client alternative |

---

# 3. Database Design

## 3.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ENTITY RELATIONSHIP DIAGRAM                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐             │
│  │    users     │         │    tasks     │         │  task_files  │             │
│  ├──────────────┤         ├──────────────┤         ├──────────────┤             │
│  │ id (PK)      │────┐    │ id (PK)      │────┬───▶│ id (PK)      │             │
│  │ clerk_id     │    │    │ creator_id(FK)│◀──┤    │ task_id (FK) │             │
│  │ email        │    │    │ title        │    │    │ file_name    │             │
│  │ name         │    │    │ description  │    │    │ file_url     │             │
│  │ user_type    │    │    │ task_type    │    │    │ file_type    │             │
│  │ company_name │    │    │ difficulty   │    │    │ created_at   │             │
│  │ company_size │    │    │ time_limit   │    │    └──────────────┘             │
│  │ subscription │    │    │ is_default   │    │                                 │
│  │ created_at   │    │    │ created_at   │    │    ┌──────────────┐             │
│  │ updated_at   │    │    │ updated_at   │    │    │ eval_config  │             │
│  └──────────────┘    │    └──────────────┘    └───▶├──────────────┤             │
│         │            │           │                 │ id (PK)      │             │
│         │            │           │                 │ task_id (FK) │             │
│         │            │           │                 │ cat_weights  │             │
│         │            │           │                 │ sub_weights  │             │
│         │            │           │                 │ custom_cats  │             │
│         │            │           │                 └──────────────┘             │
│         │            │           │                                              │
│         │            │           │                                              │
│         ▼            │           ▼                                              │
│  ┌──────────────┐    │    ┌──────────────┐         ┌──────────────┐             │
│  │  api_keys    │    │    │ invitations  │         │ assessments  │             │
│  ├──────────────┤    │    ├──────────────┤         ├──────────────┤             │
│  │ id (PK)      │    │    │ id (PK)      │         │ id (PK)      │◀────┐       │
│  │ user_id (FK) │◀───┤    │ task_id (FK) │◀────────│ task_id (FK) │     │       │
│  │ provider     │    │    │ sender_id(FK)│◀───┐    │ user_id (FK) │◀────┤       │
│  │ key_encrypted│    │    │ email        │    │    │ invite_id(FK)│     │       │
│  │ created_at   │    │    │ status       │    │    │ status       │     │       │
│  └──────────────┘    │    │ access_link  │    │    │ started_at   │     │       │
│                      │    │ expires_at   │    │    │ submitted_at │     │       │
│                      │    │ created_at   │    │    │ tracking_url │     │       │
│                      │    └──────────────┘    │    │ created_at   │     │       │
│                      │                        │    └──────────────┘     │       │
│                      │                        │           │             │       │
│                      └────────────────────────┴───────────┼─────────────┘       │
│                                                           │                     │
│                                                           ▼                     │
│                                                    ┌──────────────┐             │
│                                                    │   scores     │             │
│                                                    ├──────────────┤             │
│                                                    │ id (PK)      │             │
│                                                    │ assess_id(FK)│             │
│                                                    │ final_score  │             │
│                                                    │ level        │             │
│                                                    │ cat_scores   │             │
│                                                    │ sub_scores   │             │
│                                                    │ strengths    │             │
│                                                    │ improvements │             │
│                                                    │ ai_highlights│             │
│                                                    │ created_at   │             │
│                                                    └──────────────┘             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 SQL Schema Definitions

```sql
-- =============================================================================
-- FILE: schema.sql
-- DATABASE: PostgreSQL 15+
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE user_type AS ENUM ('business', 'individual');
CREATE TYPE subscription_plan AS ENUM ('free', 'premium', 'business');
CREATE TYPE subscription_status AS ENUM ('active', 'inactive', 'trial', 'cancelled');
CREATE TYPE task_type AS ENUM (
    'code_generation', 
    'refactoring', 
    'bug_fix', 
    'system_design', 
    'multi_agent', 
    'open_ended'
);
CREATE TYPE difficulty_level AS ENUM ('basic', 'intermediate', 'advanced');
CREATE TYPE invitation_status AS ENUM ('sent', 'accepted', 'completed', 'expired');
CREATE TYPE assessment_status AS ENUM ('pending', 'in_progress', 'submitted', 'scoring', 'scored', 'failed');
CREATE TYPE proficiency_level AS ENUM ('operator', 'architect', 'innovator');
CREATE TYPE api_provider AS ENUM ('openai', 'anthropic', 'google', 'other');

-- =============================================================================
-- TABLE: users
-- =============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url TEXT,
    user_type user_type NOT NULL DEFAULT 'individual',
    
    -- Business user fields
    company_name VARCHAR(255),
    company_size VARCHAR(50),
    company_industry VARCHAR(100),
    
    -- Subscription
    subscription_plan subscription_plan NOT NULL DEFAULT 'free',
    subscription_status subscription_status NOT NULL DEFAULT 'active',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_business_user CHECK (
        user_type = 'individual' OR 
        (user_type = 'business' AND company_name IS NOT NULL)
    )
);

CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_user_type ON users(user_type);

-- =============================================================================
-- TABLE: api_keys (encrypted storage for user API keys)
-- =============================================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider api_provider NOT NULL,
    key_encrypted BYTEA NOT NULL,  -- AES-256 encrypted
    key_hint VARCHAR(20),  -- Last 4 chars for display: "...xxxx"
    is_valid BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, provider)
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);

-- =============================================================================
-- TABLE: tasks
-- =============================================================================

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Task info
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    task_type task_type NOT NULL,
    difficulty difficulty_level NOT NULL DEFAULT 'intermediate',
    time_limit_minutes INTEGER NOT NULL DEFAULT 120,
    
    -- Flags
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_public BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- API configuration
    uses_platform_keys BOOLEAN NOT NULL DEFAULT true,
    
    -- Access control
    access_start_date TIMESTAMP WITH TIME ZONE,
    access_end_date TIMESTAMP WITH TIME ZONE,
    max_attempts INTEGER DEFAULT 1,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_time_limit CHECK (time_limit_minutes >= 30 AND time_limit_minutes <= 480)
);

CREATE INDEX idx_tasks_creator_id ON tasks(creator_id);
CREATE INDEX idx_tasks_task_type ON tasks(task_type);
CREATE INDEX idx_tasks_is_default ON tasks(is_default);
CREATE INDEX idx_tasks_is_public ON tasks(is_public);

-- =============================================================================
-- TABLE: task_files (attachments for tasks)
-- =============================================================================

CREATE TABLE task_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- 'code', 'document', 'test', 'other'
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    
    -- For code files, store the relative path
    relative_path VARCHAR(500),
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_task_files_task_id ON task_files(task_id);

-- =============================================================================
-- TABLE: evaluation_configs (scoring configuration for tasks)
-- =============================================================================

CREATE TABLE evaluation_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID UNIQUE NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    
    -- Category weights (must sum to 100)
    category_weights JSONB NOT NULL DEFAULT '{
        "planning": 25,
        "prompt_engineering": 25,
        "tool_orchestration": 25,
        "outcome_quality": 25
    }',
    
    -- Subitem weights per category (each category's subitems must sum to 100)
    subitem_weights JSONB NOT NULL DEFAULT '{
        "planning": {
            "task_breakdown": 25,
            "time_estimation": 25,
            "milestone_definition": 25,
            "problem_understanding": 25
        },
        "prompt_engineering": {
            "clarity_specificity": 25,
            "context_management": 25,
            "iteration_efficiency": 25,
            "error_recovery": 25
        },
        "tool_orchestration": {
            "tool_selection": 25,
            "multi_tool_coordination": 25,
            "workflow_efficiency": 25,
            "resource_utilization": 25
        },
        "outcome_quality": {
            "correctness": 25,
            "code_quality": 25,
            "documentation": 25,
            "edge_case_handling": 25
        }
    }',
    
    -- Custom categories added by business users
    custom_categories JSONB DEFAULT '[]',
    
    -- Level thresholds
    level_thresholds JSONB NOT NULL DEFAULT '{
        "operator": {"min": 40, "max": 64},
        "architect": {"min": 65, "max": 84},
        "innovator": {"min": 85, "max": 100}
    }',
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- TABLE: invitations
-- =============================================================================

CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Recipient info
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),
    
    -- Status
    status invitation_status NOT NULL DEFAULT 'sent',
    
    -- Access
    access_link VARCHAR(100) UNIQUE NOT NULL,
    access_code VARCHAR(20),  -- Optional additional verification
    
    -- Timing
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    message TEXT,  -- Custom message from sender
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invitations_task_id ON invitations(task_id);
CREATE INDEX idx_invitations_sender_id ON invitations(sender_id);
CREATE INDEX idx_invitations_recipient_email ON invitations(recipient_email);
CREATE INDEX idx_invitations_access_link ON invitations(access_link);
CREATE INDEX idx_invitations_status ON invitations(status);

-- =============================================================================
-- TABLE: assessments
-- =============================================================================

CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invitation_id UUID REFERENCES invitations(id) ON DELETE SET NULL,
    
    -- Status
    status assessment_status NOT NULL DEFAULT 'pending',
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    submitted_at TIMESTAMP WITH TIME ZONE,
    scored_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    
    -- Tracking data (stored in R2)
    tracking_data_url TEXT,
    
    -- Submission
    submission_files JSONB DEFAULT '[]',  -- [{fileName, content}]
    submission_notes TEXT,
    
    -- Sandbox info
    sandbox_container_id VARCHAR(100),
    sandbox_status VARCHAR(50),
    
    -- Metadata
    attempt_number INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assessments_task_id ON assessments(task_id);
CREATE INDEX idx_assessments_user_id ON assessments(user_id);
CREATE INDEX idx_assessments_status ON assessments(status);
CREATE INDEX idx_assessments_invitation_id ON assessments(invitation_id);

-- =============================================================================
-- TABLE: scores
-- =============================================================================

CREATE TABLE scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID UNIQUE NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    
    -- Overall score
    final_score DECIMAL(5,2) NOT NULL,
    proficiency_level proficiency_level NOT NULL,
    
    -- Category scores
    category_scores JSONB NOT NULL,
    -- Example: {"planning": 72.5, "prompt_engineering": 68.0, ...}
    
    -- Subitem scores
    subitem_scores JSONB NOT NULL,
    -- Example: {"planning": {"task_breakdown": 75, ...}, ...}
    
    -- Feedback
    strengths JSONB NOT NULL DEFAULT '[]',
    improvements JSONB NOT NULL DEFAULT '[]',
    ai_highlights JSONB NOT NULL DEFAULT '[]',
    
    -- Detailed analysis (for report generation)
    detailed_analysis JSONB,
    
    -- Scoring metadata
    scoring_model VARCHAR(100),  -- Which AI model was used for scoring
    scoring_version VARCHAR(20),
    
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scores_assessment_id ON scores(assessment_id);
CREATE INDEX idx_scores_proficiency_level ON scores(proficiency_level);

-- =============================================================================
-- TABLE: tracking_events (for real-time tracking, optional - could use Redis)
-- =============================================================================

CREATE TABLE tracking_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    
    event_type VARCHAR(50) NOT NULL,
    -- Types: 'code_edit', 'ai_prompt', 'ai_response', 'file_op', 
    --        'terminal_cmd', 'model_switch', 'copy_paste'
    
    event_data JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tracking_events_assessment_id ON tracking_events(assessment_id);
CREATE INDEX idx_tracking_events_timestamp ON tracking_events(timestamp);

-- Partition by month for better performance (optional)
-- CREATE TABLE tracking_events_2026_01 PARTITION OF tracking_events
--     FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- =============================================================================
-- FUNCTIONS & TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to relevant tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assessments_updated_at
    BEFORE UPDATE ON assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_evaluation_configs_updated_at
    BEFORE UPDATE ON evaluation_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS
-- =============================================================================

-- View for assessment summaries with scores
CREATE VIEW assessment_summaries AS
SELECT 
    a.id,
    a.user_id,
    a.task_id,
    t.title as task_title,
    t.task_type,
    t.difficulty,
    a.status,
    a.started_at,
    a.submitted_at,
    a.time_spent_seconds,
    s.final_score,
    s.proficiency_level,
    s.strengths,
    s.improvements
FROM assessments a
JOIN tasks t ON a.task_id = t.id
LEFT JOIN scores s ON a.id = s.assessment_id;

-- View for business user candidate tracking
CREATE VIEW candidate_tracking AS
SELECT 
    i.id as invitation_id,
    i.sender_id as business_user_id,
    i.recipient_email,
    i.recipient_name,
    i.status as invitation_status,
    i.sent_at,
    t.id as task_id,
    t.title as task_title,
    a.id as assessment_id,
    a.status as assessment_status,
    a.submitted_at,
    s.final_score,
    s.proficiency_level
FROM invitations i
JOIN tasks t ON i.task_id = t.id
LEFT JOIN assessments a ON i.id = a.invitation_id
LEFT JOIN scores s ON a.id = s.assessment_id;

-- =============================================================================
-- SEED DATA: Default Tasks
-- =============================================================================

-- Insert default tasks (run separately)
-- See seed_data.sql for complete seed data
```

## 3.3 Seed Data for Default Tasks

```sql
-- =============================================================================
-- FILE: seed_data.sql
-- Default tasks for AI Skills Lab
-- =============================================================================

-- Insert default tasks
INSERT INTO tasks (id, title, description, task_type, difficulty, time_limit_minutes, is_default, is_public, uses_platform_keys)
VALUES
-- Code Generation Tasks
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Build a REST API with AI Assistance',
    E'## Task Description\n\nBuild a simple REST API for a todo list application using AI assistance.\n\n## Requirements\n\n1. Create endpoints for CRUD operations on todos\n2. Implement proper error handling\n3. Add input validation\n4. Write basic tests\n\n## Tech Stack\n- Python with FastAPI OR Node.js with Express\n- Your choice of database (SQLite for simplicity)\n\n## Deliverables\n- Working API code\n- Basic documentation\n- At least 3 test cases\n\n## Evaluation Focus\n- How you use AI to scaffold the project\n- Your iteration process with AI\n- Code quality of the final result',
    'code_generation',
    'basic',
    120,
    true,
    true,
    true
),
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567891',
    'Create a React Dashboard Component',
    E'## Task Description\n\nBuild a data dashboard component using React and AI assistance.\n\n## Requirements\n\n1. Display at least 3 different chart types\n2. Implement responsive design\n3. Add loading and error states\n4. Create reusable chart components\n\n## Tech Stack\n- React 18+\n- Recharts or Chart.js\n- Tailwind CSS\n\n## Deliverables\n- Working React component\n- Sample data integration\n- Responsive layout\n\n## Evaluation Focus\n- Component architecture decisions\n- AI prompt strategies for UI development\n- Code reusability',
    'code_generation',
    'intermediate',
    180,
    true,
    true,
    true
),

-- Refactoring Tasks
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567892',
    'Migrate Express API to FastAPI',
    E'## Task Description\n\nRefactor an existing Express.js API to Python FastAPI using AI assistance.\n\n## Starting Code\n(Provided in task files)\n\n## Requirements\n\n1. Maintain all existing functionality\n2. Add proper type hints\n3. Implement Pydantic models\n4. Update tests for pytest\n\n## Deliverables\n- Complete FastAPI application\n- Updated tests\n- Migration notes\n\n## Evaluation Focus\n- Understanding of both frameworks\n- AI-assisted code translation\n- Handling edge cases in migration',
    'refactoring',
    'intermediate',
    240,
    true,
    true,
    true
),

-- Bug Fix Tasks
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567893',
    'Debug Authentication Flow',
    E'## Task Description\n\nFix authentication bugs in a provided codebase using AI assistance.\n\n## Bug Report\n(Provided in task files)\n\n## Requirements\n\n1. Identify root cause of auth failures\n2. Fix the bugs without breaking other features\n3. Add regression tests\n4. Document the fix\n\n## Deliverables\n- Fixed code\n- Test cases\n- Bug analysis report\n\n## Evaluation Focus\n- Debugging methodology\n- AI-assisted diagnosis\n- Comprehensive testing',
    'bug_fix',
    'basic',
    120,
    true,
    true,
    true
),
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567894',
    'Fix Race Condition in Async Code',
    E'## Task Description\n\nIdentify and fix race conditions in an async Python application.\n\n## Starting Code\n(Provided in task files - contains intentional race conditions)\n\n## Requirements\n\n1. Identify all race conditions\n2. Implement proper synchronization\n3. Maintain performance\n4. Add concurrency tests\n\n## Deliverables\n- Fixed async code\n- Concurrency test suite\n- Analysis document\n\n## Evaluation Focus\n- Understanding of async patterns\n- AI-assisted concurrent debugging\n- Solution correctness',
    'bug_fix',
    'intermediate',
    180,
    true,
    true,
    true
),

-- System Design Tasks
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567895',
    'Design an AI-Powered Search Feature',
    E'## Task Description\n\nDesign and prototype an AI-powered semantic search feature.\n\n## Requirements\n\n1. Design the system architecture\n2. Implement a working prototype\n3. Handle edge cases (empty results, long queries)\n4. Consider scalability\n\n## Deliverables\n- Architecture diagram (can be ASCII or description)\n- Working prototype code\n- Design document\n\n## Evaluation Focus\n- System design thinking\n- AI integration patterns\n- Practical implementation',
    'system_design',
    'intermediate',
    180,
    true,
    true,
    true
),
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567896',
    'Design Real-Time Notification System',
    E'## Task Description\n\nDesign a scalable real-time notification system with AI assistance.\n\n## Requirements\n\n1. Support multiple notification channels (email, push, in-app)\n2. Handle high throughput\n3. Implement user preferences\n4. Design for fault tolerance\n\n## Deliverables\n- Complete system design\n- Data models\n- API specifications\n- Prototype of core components\n\n## Evaluation Focus\n- Distributed systems knowledge\n- AI-assisted architecture decisions\n- Scalability considerations',
    'system_design',
    'advanced',
    240,
    true,
    true,
    true
),

-- Multi-Agent Tasks
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567897',
    'Build a Code Review Agent Workflow',
    E'## Task Description\n\nCreate a multi-agent workflow for automated code review.\n\n## Requirements\n\n1. Design agent roles (reviewer, suggester, security checker)\n2. Implement agent communication\n3. Create feedback aggregation\n4. Handle conflicts between agents\n\n## Deliverables\n- Working multi-agent system\n- Agent prompt designs\n- Demo with sample code review\n\n## Evaluation Focus\n- Multi-agent architecture\n- Prompt engineering for agents\n- System coordination',
    'multi_agent',
    'advanced',
    240,
    true,
    true,
    true
),
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567898',
    'Create a Research Assistant Pipeline',
    E'## Task Description\n\nBuild a multi-agent research assistant that can gather, analyze, and summarize information.\n\n## Requirements\n\n1. Implement search agent\n2. Create analysis agent\n3. Build summarization agent\n4. Design orchestration layer\n\n## Deliverables\n- Complete agent pipeline\n- Orchestration logic\n- Demo with research query\n\n## Evaluation Focus\n- Agent specialization\n- Information flow design\n- Result quality',
    'multi_agent',
    'advanced',
    300,
    true,
    true,
    true
),

-- Open-Ended Tasks
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567899',
    'Improve User Retention with AI',
    E'## Task Description\n\nPropose and prototype an AI-powered feature to improve user retention for a SaaS product.\n\n## Context\nYou are given analytics data showing user drop-off patterns.\n(Data provided in task files)\n\n## Requirements\n\n1. Analyze the provided data\n2. Propose an AI-powered solution\n3. Build a working prototype\n4. Estimate impact\n\n## Deliverables\n- Analysis document\n- Solution proposal\n- Working prototype\n- Impact estimation\n\n## Evaluation Focus\n- Business problem understanding\n- Creative AI application\n- Practical implementation',
    'open_ended',
    'advanced',
    240,
    true,
    true,
    true
),
(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567900',
    'Automate Customer Support Workflow',
    E'## Task Description\n\nDesign and implement an AI-powered customer support automation system.\n\n## Requirements\n\n1. Classify incoming support tickets\n2. Route to appropriate teams or auto-respond\n3. Generate response suggestions\n4. Implement escalation logic\n\n## Deliverables\n- System design\n- Working prototype\n- Sample ticket processing\n- Metrics dashboard design\n\n## Evaluation Focus\n- End-to-end thinking\n- AI workflow design\n- Business value delivery',
    'open_ended',
    'advanced',
    300,
    true,
    true,
    true
);

-- Insert evaluation configs for default tasks
INSERT INTO evaluation_configs (task_id, category_weights, subitem_weights)
SELECT 
    id,
    '{"planning": 25, "prompt_engineering": 25, "tool_orchestration": 25, "outcome_quality": 25}'::jsonb,
    CASE task_type
        WHEN 'code_generation' THEN '{
            "planning": {"task_breakdown": 20, "time_estimation": 25, "milestone_definition": 25, "problem_understanding": 30},
            "prompt_engineering": {"clarity_specificity": 35, "context_management": 25, "iteration_efficiency": 25, "error_recovery": 15},
            "tool_orchestration": {"tool_selection": 30, "multi_tool_coordination": 20, "workflow_efficiency": 30, "resource_utilization": 20},
            "outcome_quality": {"correctness": 40, "code_quality": 30, "documentation": 15, "edge_case_handling": 15}
        }'::jsonb
        WHEN 'refactoring' THEN '{
            "planning": {"task_breakdown": 30, "time_estimation": 20, "milestone_definition": 25, "problem_understanding": 25},
            "prompt_engineering": {"clarity_specificity": 25, "context_management": 30, "iteration_efficiency": 25, "error_recovery": 20},
            "tool_orchestration": {"tool_selection": 25, "multi_tool_coordination": 25, "workflow_efficiency": 30, "resource_utilization": 20},
            "outcome_quality": {"correctness": 35, "code_quality": 35, "documentation": 15, "edge_case_handling": 15}
        }'::jsonb
        WHEN 'bug_fix' THEN '{
            "planning": {"task_breakdown": 20, "time_estimation": 25, "milestone_definition": 20, "problem_understanding": 35},
            "prompt_engineering": {"clarity_specificity": 25, "context_management": 30, "iteration_efficiency": 30, "error_recovery": 15},
            "tool_orchestration": {"tool_selection": 25, "multi_tool_coordination": 20, "workflow_efficiency": 35, "resource_utilization": 20},
            "outcome_quality": {"correctness": 45, "code_quality": 25, "documentation": 15, "edge_case_handling": 15}
        }'::jsonb
        WHEN 'system_design' THEN '{
            "planning": {"task_breakdown": 35, "time_estimation": 20, "milestone_definition": 25, "problem_understanding": 20},
            "prompt_engineering": {"clarity_specificity": 25, "context_management": 25, "iteration_efficiency": 25, "error_recovery": 25},
            "tool_orchestration": {"tool_selection": 30, "multi_tool_coordination": 30, "workflow_efficiency": 25, "resource_utilization": 15},
            "outcome_quality": {"correctness": 30, "code_quality": 25, "documentation": 25, "edge_case_handling": 20}
        }'::jsonb
        WHEN 'multi_agent' THEN '{
            "planning": {"task_breakdown": 35, "time_estimation": 20, "milestone_definition": 25, "problem_understanding": 20},
            "prompt_engineering": {"clarity_specificity": 25, "context_management": 30, "iteration_efficiency": 25, "error_recovery": 20},
            "tool_orchestration": {"tool_selection": 35, "multi_tool_coordination": 35, "workflow_efficiency": 20, "resource_utilization": 10},
            "outcome_quality": {"correctness": 35, "code_quality": 25, "documentation": 20, "edge_case_handling": 20}
        }'::jsonb
        WHEN 'open_ended' THEN '{
            "planning": {"task_breakdown": 30, "time_estimation": 20, "milestone_definition": 25, "problem_understanding": 25},
            "prompt_engineering": {"clarity_specificity": 20, "context_management": 25, "iteration_efficiency": 25, "error_recovery": 30},
            "tool_orchestration": {"tool_selection": 30, "multi_tool_coordination": 30, "workflow_efficiency": 25, "resource_utilization": 15},
            "outcome_quality": {"correctness": 25, "code_quality": 20, "documentation": 30, "edge_case_handling": 25}
        }'::jsonb
    END
FROM tasks
WHERE is_default = true;
```

---

# 4. Authentication & Authorization

## 4.1 Clerk Integration

### Setup Configuration

```typescript
// =============================================================================
// FILE: src/lib/auth/clerk-config.ts
// =============================================================================

import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// Public routes that don't require authentication
const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/api/webhooks(.*)',
  '/results/(.*)',  // Public shareable results
  '/invite/(.*)',   // Invitation links
]);

// Routes that require business user type
const isBusinessRoute = createRouteMatcher([
  '/business(.*)',
  '/api/business(.*)',
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
};
```

### User Sync Webhook

```typescript
// =============================================================================
// FILE: src/app/api/webhooks/clerk/route.ts
// =============================================================================

import { Webhook } from 'svix';
import { headers } from 'next/headers';
import { WebhookEvent } from '@clerk/nextjs/server';
import { db } from '@/lib/db';
import { users } from '@/lib/db/schema';

export async function POST(req: Request) {
  const WEBHOOK_SECRET = process.env.CLERK_WEBHOOK_SECRET;

  if (!WEBHOOK_SECRET) {
    throw new Error('Please add CLERK_WEBHOOK_SECRET to .env');
  }

  const headerPayload = headers();
  const svix_id = headerPayload.get('svix-id');
  const svix_timestamp = headerPayload.get('svix-timestamp');
  const svix_signature = headerPayload.get('svix-signature');

  if (!svix_id || !svix_timestamp || !svix_signature) {
    return new Response('Error occurred -- missing svix headers', { status: 400 });
  }

  const payload = await req.json();
  const body = JSON.stringify(payload);

  const wh = new Webhook(WEBHOOK_SECRET);
  let evt: WebhookEvent;

  try {
    evt = wh.verify(body, {
      'svix-id': svix_id,
      'svix-timestamp': svix_timestamp,
      'svix-signature': svix_signature,
    }) as WebhookEvent;
  } catch (err) {
    console.error('Error verifying webhook:', err);
    return new Response('Error occurred', { status: 400 });
  }

  const eventType = evt.type;

  if (eventType === 'user.created') {
    const { id, email_addresses, first_name, last_name, image_url, unsafe_metadata } = evt.data;

    const email = email_addresses[0]?.email_address;
    const name = [first_name, last_name].filter(Boolean).join(' ') || 'User';
    const userType = (unsafe_metadata?.user_type as 'business' | 'individual') || 'individual';

    await db.insert(users).values({
      clerkId: id,
      email: email!,
      name,
      avatarUrl: image_url,
      userType,
      companyName: unsafe_metadata?.company_name as string,
      companySize: unsafe_metadata?.company_size as string,
      companyIndustry: unsafe_metadata?.company_industry as string,
    });
  }

  if (eventType === 'user.updated') {
    const { id, email_addresses, first_name, last_name, image_url } = evt.data;

    const email = email_addresses[0]?.email_address;
    const name = [first_name, last_name].filter(Boolean).join(' ');

    await db
      .update(users)
      .set({
        email: email!,
        name,
        avatarUrl: image_url,
        updatedAt: new Date(),
      })
      .where(eq(users.clerkId, id));
  }

  if (eventType === 'user.deleted') {
    const { id } = evt.data;
    await db.delete(users).where(eq(users.clerkId, id!));
  }

  return new Response('', { status: 200 });
}
```

## 4.2 Custom Sign-Up Flow

```typescript
// =============================================================================
// FILE: src/app/sign-up/[[...sign-up]]/page.tsx
// =============================================================================

'use client';

import { useState } from 'react';
import { useSignUp } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function SignUpPage() {
  const { isLoaded, signUp, setActive } = useSignUp();
  const router = useRouter();
  
  const [step, setStep] = useState<'type' | 'details' | 'verify'>('type');
  const [userType, setUserType] = useState<'individual' | 'business'>('individual');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    firstName: '',
    lastName: '',
    companyName: '',
    companySize: '',
    companyIndustry: '',
  });
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmitDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;
    
    setLoading(true);
    setError('');

    try {
      await signUp.create({
        emailAddress: formData.email,
        password: formData.password,
        firstName: formData.firstName,
        lastName: formData.lastName,
        unsafeMetadata: {
          user_type: userType,
          company_name: formData.companyName,
          company_size: formData.companySize,
          company_industry: formData.companyIndustry,
        },
      });

      await signUp.prepareEmailAddressVerification({ strategy: 'email_code' });
      setStep('verify');
    } catch (err: any) {
      setError(err.errors?.[0]?.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoaded) return;

    setLoading(true);
    setError('');

    try {
      const completeSignUp = await signUp.attemptEmailAddressVerification({
        code: verificationCode,
      });

      if (completeSignUp.status === 'complete') {
        await setActive({ session: completeSignUp.createdSessionId });
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.errors?.[0]?.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  // Step 1: Select User Type
  if (step === 'type') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Join SmartSuccess.AI</CardTitle>
            <CardDescription>Select your account type to get started</CardDescription>
          </CardHeader>
          <CardContent>
            <RadioGroup
              value={userType}
              onValueChange={(v) => setUserType(v as 'individual' | 'business')}
              className="space-y-4"
            >
              <div className={`flex items-start space-x-4 p-4 rounded-lg border-2 cursor-pointer
                ${userType === 'individual' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}
                onClick={() => setUserType('individual')}
              >
                <RadioGroupItem value="individual" id="individual" />
                <div className="flex-1">
                  <Label htmlFor="individual" className="text-lg font-medium cursor-pointer">
                    Individual
                  </Label>
                  <p className="text-sm text-gray-500 mt-1">
                    Practice AI skills, earn certifications, and share your results with potential employers.
                  </p>
                  <ul className="text-sm text-gray-600 mt-2 space-y-1">
                    <li>✓ Access to default assessment tasks</li>
                    <li>✓ Platform-provided API keys</li>
                    <li>✓ Shareable skill certificates</li>
                  </ul>
                </div>
              </div>

              <div className={`flex items-start space-x-4 p-4 rounded-lg border-2 cursor-pointer
                ${userType === 'business' ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}
                onClick={() => setUserType('business')}
              >
                <RadioGroupItem value="business" id="business" />
                <div className="flex-1">
                  <Label htmlFor="business" className="text-lg font-medium cursor-pointer">
                    Business
                  </Label>
                  <p className="text-sm text-gray-500 mt-1">
                    Create custom assessments, invite candidates, and compare their AI skills.
                  </p>
                  <ul className="text-sm text-gray-600 mt-2 space-y-1">
                    <li>✓ Create custom assessment tasks</li>
                    <li>✓ Invite and track candidates</li>
                    <li>✓ Compare candidates side-by-side</li>
                    <li>✓ Export detailed reports</li>
                  </ul>
                </div>
              </div>
            </RadioGroup>

            <Button 
              className="w-full mt-6" 
              onClick={() => setStep('details')}
            >
              Continue
            </Button>

            <p className="text-center text-sm text-gray-500 mt-4">
              Already have an account?{' '}
              <a href="/sign-in" className="text-blue-600 hover:underline">
                Sign in
              </a>
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Step 2: Enter Details
  if (step === 'details') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">
              {userType === 'business' ? 'Business Account' : 'Create Account'}
            </CardTitle>
            <CardDescription>
              {userType === 'business' 
                ? 'Set up your business account to start hiring'
                : 'Enter your details to create your account'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitDetails} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    value={formData.firstName}
                    onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    value={formData.lastName}
                    onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  minLength={8}
                />
              </div>

              {userType === 'business' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="companyName">Company Name</Label>
                    <Input
                      id="companyName"
                      value={formData.companyName}
                      onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="companySize">Company Size</Label>
                      <select
                        id="companySize"
                        className="w-full h-10 rounded-md border border-input bg-background px-3"
                        value={formData.companySize}
                        onChange={(e) => setFormData({ ...formData, companySize: e.target.value })}
                        required
                      >
                        <option value="">Select...</option>
                        <option value="1-10">1-10</option>
                        <option value="11-50">11-50</option>
                        <option value="51-200">51-200</option>
                        <option value="201-500">201-500</option>
                        <option value="500+">500+</option>
                      </select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="companyIndustry">Industry</Label>
                      <select
                        id="companyIndustry"
                        className="w-full h-10 rounded-md border border-input bg-background px-3"
                        value={formData.companyIndustry}
                        onChange={(e) => setFormData({ ...formData, companyIndustry: e.target.value })}
                        required
                      >
                        <option value="">Select...</option>
                        <option value="technology">Technology</option>
                        <option value="finance">Finance</option>
                        <option value="healthcare">Healthcare</option>
                        <option value="retail">Retail</option>
                        <option value="manufacturing">Manufacturing</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                  </div>
                </>
              )}

              {error && (
                <p className="text-sm text-red-500">{error}</p>
              )}

              <div className="flex gap-3">
                <Button 
                  type="button" 
                  variant="outline" 
                  className="flex-1"
                  onClick={() => setStep('type')}
                >
                  Back
                </Button>
                <Button type="submit" className="flex-1" disabled={loading}>
                  {loading ? 'Creating...' : 'Create Account'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Step 3: Verify Email
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Verify Your Email</CardTitle>
          <CardDescription>
            We sent a verification code to {formData.email}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleVerify} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="code">Verification Code</Label>
              <Input
                id="code"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                placeholder="Enter 6-digit code"
                required
              />
            </div>

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Verifying...' : 'Verify Email'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

## 4.3 Authorization Helper

```typescript
// =============================================================================
// FILE: src/lib/auth/authorization.ts
// =============================================================================

import { auth, currentUser } from '@clerk/nextjs/server';
import { db } from '@/lib/db';
import { users, tasks, assessments, invitations } from '@/lib/db/schema';
import { eq, and } from 'drizzle-orm';

export async function getCurrentUser() {
  const { userId } = await auth();
  if (!userId) return null;

  const user = await db.query.users.findFirst({
    where: eq(users.clerkId, userId),
  });

  return user;
}

export async function requireUser() {
  const user = await getCurrentUser();
  if (!user) {
    throw new Error('Unauthorized');
  }
  return user;
}

export async function requireBusinessUser() {
  const user = await requireUser();
  if (user.userType !== 'business') {
    throw new Error('Business account required');
  }
  return user;
}

export async function canAccessTask(taskId: string) {
  const user = await getCurrentUser();
  
  const task = await db.query.tasks.findFirst({
    where: eq(tasks.id, taskId),
  });

  if (!task) return false;

  // Default tasks are accessible to all
  if (task.isDefault) return true;

  // Public tasks are accessible to all
  if (task.isPublic) return true;

  // Creator can access their own tasks
  if (user && task.creatorId === user.id) return true;

  // Check if user was invited
  if (user) {
    const invitation = await db.query.invitations.findFirst({
      where: and(
        eq(invitations.taskId, taskId),
        eq(invitations.recipientEmail, user.email),
        eq(invitations.status, 'accepted')
      ),
    });
    if (invitation) return true;
  }

  return false;
}

export async function canManageTask(taskId: string) {
  const user = await requireUser();
  
  const task = await db.query.tasks.findFirst({
    where: and(
      eq(tasks.id, taskId),
      eq(tasks.creatorId, user.id)
    ),
  });

  return !!task;
}

export async function canViewAssessment(assessmentId: string) {
  const user = await getCurrentUser();
  
  const assessment = await db.query.assessments.findFirst({
    where: eq(assessments.id, assessmentId),
    with: {
      task: true,
      invitation: true,
    },
  });

  if (!assessment) return false;

  // User can view their own assessment
  if (user && assessment.userId === user.id) return true;

  // Task creator can view assessments for their task
  if (user && assessment.task.creatorId === user.id) return true;

  // Check if assessment has public sharing enabled (future feature)
  // if (assessment.isPublic) return true;

  return false;
}
```
# 5. Backend Services

## 5.1 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── config.py                  # Configuration management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # Dependency injection
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py            # Auth endpoints
│   │   │   ├── tasks.py           # Task CRUD
│   │   │   ├── assessments.py     # Assessment management
│   │   │   ├── invitations.py     # Invitation system
│   │   │   ├── scoring.py         # Scoring endpoints
│   │   │   ├── ai_proxy.py        # AI model proxy
│   │   │   └── business.py        # Business user features
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py            # Auth middleware
│   │       └── rate_limit.py      # Rate limiting
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_service.py
│   │   ├── assessment_service.py
│   │   ├── invitation_service.py
│   │   ├── scoring_service.py
│   │   ├── ai_service.py
│   │   ├── sandbox_service.py
│   │   ├── storage_service.py
│   │   └── email_service.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── assessment.py
│   │   ├── invitation.py
│   │   ├── score.py
│   │   └── tracking.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── task.py
│   │   ├── assessment.py
│   │   ├── invitation.py
│   │   ├── score.py
│   │   └── ai.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py            # Database connection
│   │   ├── redis.py               # Redis connection
│   │   ├── storage.py             # R2/S3 connection
│   │   └── security.py            # Encryption utilities
│   │
│   └── scoring/
│       ├── __init__.py
│       ├── pipeline.py            # Scoring pipeline
│       ├── evaluators/
│       │   ├── __init__.py
│       │   ├── planning.py
│       │   ├── prompt_engineering.py
│       │   ├── tool_orchestration.py
│       │   └── outcome_quality.py
│       └── prompts/
│           ├── __init__.py
│           └── evaluation_prompts.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_tasks.py
│   ├── test_assessments.py
│   └── test_scoring.py
│
├── alembic/                       # Database migrations
│   ├── versions/
│   └── env.py
│
├── pyproject.toml
├── poetry.lock
├── Dockerfile
└── docker-compose.yml
```

## 5.2 Configuration Management

```python
# =============================================================================
# FILE: app/config.py
# =============================================================================

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Skills Lab"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str
    
    # Storage (Cloudflare R2)
    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET_NAME: str = "ai-skills-lab"
    R2_PUBLIC_URL: Optional[str] = None
    
    # AI Providers
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    
    # Clerk Auth
    CLERK_SECRET_KEY: str
    CLERK_WEBHOOK_SECRET: str
    
    # Email (Resend)
    RESEND_API_KEY: str
    EMAIL_FROM: str = "AI Skills Lab <noreply@smartsuccess.ai>"
    
    # Sandbox (Fly.io)
    FLY_API_TOKEN: str
    FLY_APP_NAME: str = "ai-skills-lab-sandbox"
    
    # Encryption
    ENCRYPTION_KEY: str  # 32 bytes, base64 encoded
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    AI_RATE_LIMIT_PER_MINUTE: int = 30
    
    # Scoring
    SCORING_MODEL: str = "claude-sonnet-4-20250514"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

## 5.3 Database Connection

```python
# =============================================================================
# FILE: app/core/database.py
# =============================================================================

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

## 5.4 Assessment Service

```python
# =============================================================================
# FILE: app/services/assessment_service.py
# =============================================================================

from uuid import UUID, uuid4
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment, AssessmentStatus
from app.models.task import Task
from app.models.invitation import Invitation, InvitationStatus
from app.schemas.assessment import (
    AssessmentCreate, 
    AssessmentUpdate, 
    AssessmentResponse,
    AssessmentStartResponse,
    SubmissionData,
)
from app.services.sandbox_service import SandboxService
from app.services.storage_service import StorageService
from app.core.redis import redis_client

class AssessmentService:
    def __init__(
        self, 
        db: AsyncSession,
        sandbox_service: SandboxService,
        storage_service: StorageService,
    ):
        self.db = db
        self.sandbox = sandbox_service
        self.storage = storage_service

    async def create_assessment(
        self,
        user_id: UUID,
        task_id: UUID,
        invitation_id: Optional[UUID] = None,
    ) -> Assessment:
        """Create a new assessment session."""
        
        # Check if task exists and is accessible
        task = await self.db.get(Task, task_id)
        if not task:
            raise ValueError("Task not found")
        
        # Check attempt limits
        existing_count = await self._count_user_attempts(user_id, task_id)
        if task.max_attempts and existing_count >= task.max_attempts:
            raise ValueError(f"Maximum attempts ({task.max_attempts}) reached")
        
        # Create assessment
        assessment = Assessment(
            id=uuid4(),
            task_id=task_id,
            user_id=user_id,
            invitation_id=invitation_id,
            status=AssessmentStatus.PENDING,
            attempt_number=existing_count + 1,
        )
        
        self.db.add(assessment)
        await self.db.flush()
        
        return assessment

    async def start_assessment(self, assessment_id: UUID) -> AssessmentStartResponse:
        """Start an assessment and provision sandbox environment."""
        
        assessment = await self.db.get(
            Assessment, 
            assessment_id,
            options=[selectinload(Assessment.task)]
        )
        
        if not assessment:
            raise ValueError("Assessment not found")
        
        if assessment.status != AssessmentStatus.PENDING:
            raise ValueError(f"Assessment cannot be started (status: {assessment.status})")
        
        # Provision sandbox container
        sandbox_info = await self.sandbox.create_container(
            assessment_id=str(assessment_id),
            task_files=assessment.task.files if assessment.task else [],
            time_limit_minutes=assessment.task.time_limit_minutes,
        )
        
        # Update assessment
        assessment.status = AssessmentStatus.IN_PROGRESS
        assessment.started_at = datetime.utcnow()
        assessment.sandbox_container_id = sandbox_info.container_id
        assessment.sandbox_status = "running"
        
        await self.db.flush()
        
        # Initialize tracking in Redis
        await self._init_tracking(assessment_id)
        
        # Calculate deadline
        deadline = assessment.started_at + timedelta(
            minutes=assessment.task.time_limit_minutes
        )
        
        return AssessmentStartResponse(
            assessment_id=assessment_id,
            sandbox_url=sandbox_info.url,
            websocket_url=sandbox_info.ws_url,
            started_at=assessment.started_at,
            deadline=deadline,
            time_limit_minutes=assessment.task.time_limit_minutes,
        )

    async def track_event(
        self,
        assessment_id: UUID,
        event_type: str,
        event_data: dict,
    ) -> None:
        """Record a tracking event."""
        
        event = {
            "type": event_type,
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Store in Redis list (batch write to R2 periodically)
        key = f"tracking:{assessment_id}:events"
        await redis_client.rpush(key, json.dumps(event))
        
        # Update metrics in Redis hash
        metrics_key = f"tracking:{assessment_id}:metrics"
        
        if event_type == "ai_prompt":
            await redis_client.hincrby(metrics_key, "total_ai_prompts", 1)
            await redis_client.hincrby(
                metrics_key, 
                "total_tokens", 
                event_data.get("token_count", 0)
            )
        elif event_type == "code_edit":
            await redis_client.hincrby(metrics_key, "code_iterations", 1)
        elif event_type == "model_switch":
            models_key = f"tracking:{assessment_id}:models"
            await redis_client.sadd(models_key, event_data.get("model"))

    async def submit_assessment(
        self,
        assessment_id: UUID,
        submission: SubmissionData,
    ) -> Assessment:
        """Submit an assessment for scoring."""
        
        assessment = await self.db.get(Assessment, assessment_id)
        
        if not assessment:
            raise ValueError("Assessment not found")
        
        if assessment.status != AssessmentStatus.IN_PROGRESS:
            raise ValueError("Assessment is not in progress")
        
        # Calculate time spent
        time_spent = int((datetime.utcnow() - assessment.started_at).total_seconds())
        
        # Finalize tracking data
        tracking_data = await self._finalize_tracking(assessment_id)
        
        # Upload tracking data to R2
        tracking_url = await self.storage.upload_json(
            f"tracking/{assessment_id}/data.json",
            tracking_data,
        )
        
        # Update assessment
        assessment.status = AssessmentStatus.SUBMITTED
        assessment.submitted_at = datetime.utcnow()
        assessment.time_spent_seconds = time_spent
        assessment.tracking_data_url = tracking_url
        assessment.submission_files = [
            {"fileName": f.file_name, "content": f.content}
            for f in submission.files
        ]
        assessment.submission_notes = submission.notes
        
        # Cleanup sandbox
        if assessment.sandbox_container_id:
            await self.sandbox.destroy_container(assessment.sandbox_container_id)
            assessment.sandbox_status = "terminated"
        
        await self.db.flush()
        
        # Trigger scoring (async background job)
        from app.services.scoring_service import trigger_scoring
        await trigger_scoring(assessment_id)
        
        return assessment

    async def get_assessment_with_score(
        self,
        assessment_id: UUID,
    ) -> Optional[AssessmentResponse]:
        """Get assessment with score details."""
        
        result = await self.db.execute(
            select(Assessment)
            .options(
                selectinload(Assessment.task),
                selectinload(Assessment.score),
                selectinload(Assessment.user),
            )
            .where(Assessment.id == assessment_id)
        )
        
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            return None
        
        return AssessmentResponse.from_orm(assessment)

    async def list_user_assessments(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> List[AssessmentResponse]:
        """List assessments for a user."""
        
        result = await self.db.execute(
            select(Assessment)
            .options(
                selectinload(Assessment.task),
                selectinload(Assessment.score),
            )
            .where(Assessment.user_id == user_id)
            .order_by(Assessment.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        assessments = result.scalars().all()
        
        return [AssessmentResponse.from_orm(a) for a in assessments]

    async def _count_user_attempts(self, user_id: UUID, task_id: UUID) -> int:
        """Count how many times a user has attempted a task."""
        
        result = await self.db.execute(
            select(Assessment)
            .where(and_(
                Assessment.user_id == user_id,
                Assessment.task_id == task_id,
            ))
        )
        
        return len(result.scalars().all())

    async def _init_tracking(self, assessment_id: UUID) -> None:
        """Initialize tracking data in Redis."""
        
        metrics_key = f"tracking:{assessment_id}:metrics"
        await redis_client.hset(metrics_key, mapping={
            "total_ai_prompts": 0,
            "total_tokens": 0,
            "code_iterations": 0,
            "started_at": datetime.utcnow().isoformat(),
        })

    async def _finalize_tracking(self, assessment_id: UUID) -> dict:
        """Finalize and compile tracking data."""
        
        events_key = f"tracking:{assessment_id}:events"
        metrics_key = f"tracking:{assessment_id}:metrics"
        models_key = f"tracking:{assessment_id}:models"
        
        # Get all events
        events_raw = await redis_client.lrange(events_key, 0, -1)
        events = [json.loads(e) for e in events_raw]
        
        # Get metrics
        metrics = await redis_client.hgetall(metrics_key)
        
        # Get models used
        models = await redis_client.smembers(models_key)
        
        # Compile tracking data
        tracking_data = {
            "assessment_id": str(assessment_id),
            "events": events,
            "metrics": {
                "total_ai_prompts": int(metrics.get("total_ai_prompts", 0)),
                "total_tokens": int(metrics.get("total_tokens", 0)),
                "code_iterations": int(metrics.get("code_iterations", 0)),
                "models_used": list(models),
            },
            "finalized_at": datetime.utcnow().isoformat(),
        }
        
        # Cleanup Redis
        await redis_client.delete(events_key, metrics_key, models_key)
        
        return tracking_data
```

## 5.5 AI Proxy Service

```python
# =============================================================================
# FILE: app/services/ai_service.py
# =============================================================================

from typing import Optional, AsyncGenerator
from uuid import UUID
import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import settings
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    ChatMessage,
    ModelInfo,
)
from app.services.assessment_service import AssessmentService

class AIService:
    def __init__(self):
        self.anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        self.models = {
            "claude-sonnet-4-20250514": {
                "provider": "anthropic",
                "name": "Claude Sonnet 4",
                "max_tokens": 8192,
            },
            "claude-3-haiku-20240307": {
                "provider": "anthropic", 
                "name": "Claude 3 Haiku",
                "max_tokens": 4096,
            },
            "gpt-4o": {
                "provider": "openai",
                "name": "GPT-4o",
                "max_tokens": 4096,
            },
            "gpt-4o-mini": {
                "provider": "openai",
                "name": "GPT-4o Mini",
                "max_tokens": 4096,
            },
        }

    async def chat(
        self,
        request: ChatRequest,
        assessment_id: Optional[UUID] = None,
        custom_api_key: Optional[str] = None,
    ) -> ChatResponse:
        """Send a chat request to the specified model."""
        
        model_info = self.models.get(request.model)
        if not model_info:
            raise ValueError(f"Unknown model: {request.model}")
        
        provider = model_info["provider"]
        
        # Track the request if assessment_id provided
        if assessment_id:
            await self._track_request(assessment_id, request)
        
        # Route to appropriate provider
        if provider == "anthropic":
            response = await self._anthropic_chat(request, custom_api_key)
        elif provider == "openai":
            response = await self._openai_chat(request, custom_api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Track the response
        if assessment_id:
            await self._track_response(assessment_id, response)
        
        return response

    async def chat_stream(
        self,
        request: ChatRequest,
        assessment_id: Optional[UUID] = None,
        custom_api_key: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response."""
        
        model_info = self.models.get(request.model)
        if not model_info:
            raise ValueError(f"Unknown model: {request.model}")
        
        provider = model_info["provider"]
        
        if assessment_id:
            await self._track_request(assessment_id, request)
        
        full_response = ""
        
        if provider == "anthropic":
            async for chunk in self._anthropic_stream(request, custom_api_key):
                full_response += chunk
                yield chunk
        elif provider == "openai":
            async for chunk in self._openai_stream(request, custom_api_key):
                full_response += chunk
                yield chunk
        
        if assessment_id:
            await self._track_response(
                assessment_id, 
                ChatResponse(
                    content=full_response,
                    model=request.model,
                    usage={"total_tokens": len(full_response.split())},  # Approximate
                )
            )

    async def _anthropic_chat(
        self, 
        request: ChatRequest,
        custom_api_key: Optional[str] = None,
    ) -> ChatResponse:
        """Send chat to Anthropic."""
        
        client = self.anthropic
        if custom_api_key:
            client = AsyncAnthropic(api_key=custom_api_key)
        
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ]
        
        response = await client.messages.create(
            model=request.model,
            max_tokens=request.max_tokens or 4096,
            messages=messages,
            system=request.system_prompt,
        )
        
        return ChatResponse(
            content=response.content[0].text,
            model=request.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
        )

    async def _openai_chat(
        self,
        request: ChatRequest,
        custom_api_key: Optional[str] = None,
    ) -> ChatResponse:
        """Send chat to OpenAI."""
        
        client = self.openai
        if custom_api_key:
            client = AsyncOpenAI(api_key=custom_api_key)
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        messages.extend([
            {"role": m.role, "content": m.content}
            for m in request.messages
        ])
        
        response = await client.chat.completions.create(
            model=request.model,
            max_tokens=request.max_tokens or 4096,
            messages=messages,
        )
        
        return ChatResponse(
            content=response.choices[0].message.content,
            model=request.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        )

    async def _anthropic_stream(
        self,
        request: ChatRequest,
        custom_api_key: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from Anthropic."""
        
        client = self.anthropic
        if custom_api_key:
            client = AsyncAnthropic(api_key=custom_api_key)
        
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ]
        
        async with client.messages.stream(
            model=request.model,
            max_tokens=request.max_tokens or 4096,
            messages=messages,
            system=request.system_prompt,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _openai_stream(
        self,
        request: ChatRequest,
        custom_api_key: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenAI."""
        
        client = self.openai
        if custom_api_key:
            client = AsyncOpenAI(api_key=custom_api_key)
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        
        messages.extend([
            {"role": m.role, "content": m.content}
            for m in request.messages
        ])
        
        stream = await client.chat.completions.create(
            model=request.model,
            max_tokens=request.max_tokens or 4096,
            messages=messages,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _track_request(self, assessment_id: UUID, request: ChatRequest):
        """Track AI request for scoring."""
        from app.services.assessment_service import AssessmentService
        
        # This would be injected properly in real implementation
        event_data = {
            "model": request.model,
            "prompt": request.messages[-1].content if request.messages else "",
            "message_count": len(request.messages),
        }
        
        # Store in Redis for batch processing
        from app.core.redis import redis_client
        import json
        
        key = f"tracking:{assessment_id}:events"
        event = {
            "type": "ai_prompt",
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await redis_client.rpush(key, json.dumps(event))

    async def _track_response(self, assessment_id: UUID, response: ChatResponse):
        """Track AI response for scoring."""
        from app.core.redis import redis_client
        import json
        
        event_data = {
            "model": response.model,
            "response_length": len(response.content),
            "token_count": response.usage.get("total_tokens", 0),
        }
        
        key = f"tracking:{assessment_id}:events"
        event = {
            "type": "ai_response",
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await redis_client.rpush(key, json.dumps(event))
        
        # Update metrics
        metrics_key = f"tracking:{assessment_id}:metrics"
        await redis_client.hincrby(metrics_key, "total_ai_prompts", 1)
        await redis_client.hincrby(
            metrics_key, 
            "total_tokens", 
            response.usage.get("total_tokens", 0)
        )

    def list_models(self) -> list[ModelInfo]:
        """List available AI models."""
        return [
            ModelInfo(
                id=model_id,
                name=info["name"],
                provider=info["provider"],
                max_tokens=info["max_tokens"],
            )
            for model_id, info in self.models.items()
        ]
```

## 5.6 Sandbox Service (Fly.io Integration)

```python
# =============================================================================
# FILE: app/services/sandbox_service.py
# =============================================================================

import httpx
from typing import Optional, List
from dataclasses import dataclass
from app.config import settings

@dataclass
class SandboxInfo:
    container_id: str
    url: str
    ws_url: str
    status: str

class SandboxService:
    """Service for managing isolated code execution environments on Fly.io."""
    
    def __init__(self):
        self.api_url = "https://api.machines.dev/v1"
        self.app_name = settings.FLY_APP_NAME
        self.headers = {
            "Authorization": f"Bearer {settings.FLY_API_TOKEN}",
            "Content-Type": "application/json",
        }

    async def create_container(
        self,
        assessment_id: str,
        task_files: List[dict],
        time_limit_minutes: int,
    ) -> SandboxInfo:
        """Create a new sandbox container for an assessment."""
        
        # Machine configuration
        machine_config = {
            "name": f"sandbox-{assessment_id[:8]}",
            "config": {
                "image": "registry.fly.io/ai-skills-lab-sandbox:latest",
                "env": {
                    "ASSESSMENT_ID": assessment_id,
                    "TIME_LIMIT_MINUTES": str(time_limit_minutes),
                },
                "guest": {
                    "cpu_kind": "shared",
                    "cpus": 1,
                    "memory_mb": 2048,
                },
                "services": [
                    {
                        "ports": [
                            {"port": 443, "handlers": ["tls", "http"]},
                            {"port": 80, "handlers": ["http"]},
                        ],
                        "protocol": "tcp",
                        "internal_port": 3000,
                    }
                ],
                "auto_destroy": True,
                "restart": {
                    "policy": "no",
                },
                "metadata": {
                    "assessment_id": assessment_id,
                },
            },
        }
        
        async with httpx.AsyncClient() as client:
            # Create the machine
            response = await client.post(
                f"{self.api_url}/apps/{self.app_name}/machines",
                headers=self.headers,
                json=machine_config,
                timeout=60.0,
            )
            response.raise_for_status()
            
            machine_data = response.json()
            machine_id = machine_data["id"]
            
            # Wait for machine to be ready
            await self._wait_for_machine(client, machine_id)
            
            # Get the allocated IP/hostname
            hostname = f"{machine_id}.{self.app_name}.internal"
            public_url = f"https://{self.app_name}.fly.dev/sandbox/{assessment_id}"
            ws_url = f"wss://{self.app_name}.fly.dev/sandbox/{assessment_id}/ws"
            
            # Upload task files to the container
            if task_files:
                await self._upload_files(client, machine_id, task_files)
            
            return SandboxInfo(
                container_id=machine_id,
                url=public_url,
                ws_url=ws_url,
                status="running",
            )

    async def destroy_container(self, container_id: str) -> None:
        """Destroy a sandbox container."""
        
        async with httpx.AsyncClient() as client:
            try:
                # Stop the machine
                await client.post(
                    f"{self.api_url}/apps/{self.app_name}/machines/{container_id}/stop",
                    headers=self.headers,
                    timeout=30.0,
                )
                
                # Delete the machine
                await client.delete(
                    f"{self.api_url}/apps/{self.app_name}/machines/{container_id}",
                    headers=self.headers,
                    timeout=30.0,
                )
            except httpx.HTTPError as e:
                # Log but don't raise - container might already be gone
                print(f"Error destroying container {container_id}: {e}")

    async def get_container_status(self, container_id: str) -> Optional[str]:
        """Get the status of a sandbox container."""
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.api_url}/apps/{self.app_name}/machines/{container_id}",
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get("state")
            except httpx.HTTPError:
                return None

    async def _wait_for_machine(
        self, 
        client: httpx.AsyncClient, 
        machine_id: str,
        timeout: int = 60,
    ) -> None:
        """Wait for a machine to be in 'started' state."""
        
        import asyncio
        
        for _ in range(timeout // 2):
            response = await client.get(
                f"{self.api_url}/apps/{self.app_name}/machines/{machine_id}",
                headers=self.headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("state") == "started":
                    return
            
            await asyncio.sleep(2)
        
        raise TimeoutError(f"Machine {machine_id} did not start in time")

    async def _upload_files(
        self,
        client: httpx.AsyncClient,
        machine_id: str,
        files: List[dict],
    ) -> None:
        """Upload task files to the sandbox container."""
        
        # This would use the Fly.io exec API or a custom endpoint
        # on the sandbox container to upload files
        
        for file in files:
            # Implementation depends on sandbox container setup
            pass
```

---

# 6. AI Workspace Implementation

## 6.1 Workspace Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         AI WORKSPACE COMPONENT TREE                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  <WorkspacePage>                                                                 │
│  │                                                                               │
│  ├── <WorkspaceProvider>              // Context for workspace state             │
│  │   │                                                                           │
│  │   ├── <WorkspaceHeader>            // Timer, task info, submit button         │
│  │   │   ├── <TaskInfo />                                                        │
│  │   │   ├── <Timer />                                                           │
│  │   │   └── <SubmitButton />                                                    │
│  │   │                                                                           │
│  │   ├── <ResizablePanels>            // Main workspace layout                   │
│  │   │   │                                                                       │
│  │   │   ├── <LeftPanel>              // File explorer + task description        │
│  │   │   │   ├── <FileExplorer />                                                │
│  │   │   │   └── <TaskDescription />                                             │
│  │   │   │                                                                       │
│  │   │   ├── <CenterPanel>            // Code editor                             │
│  │   │   │   ├── <EditorTabs />                                                  │
│  │   │   │   └── <MonacoEditor />                                                │
│  │   │   │                                                                       │
│  │   │   └── <RightPanel>             // AI chat                                 │
│  │   │       ├── <ModelSelector />                                               │
│  │   │       ├── <ChatHistory />                                                 │
│  │   │       └── <ChatInput />                                                   │
│  │   │                                                                           │
│  │   └── <BottomPanel>                // Terminal (collapsible)                  │
│  │       └── <XtermTerminal />                                                   │
│  │                                                                               │
│  └── <TrackingLayer />                // Invisible, captures all events          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 6.2 Workspace Context & State

```typescript
// =============================================================================
// FILE: src/components/workspace/WorkspaceContext.tsx
// =============================================================================

'use client';

import React, { createContext, useContext, useReducer, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

// Types
interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  content?: string;
  children?: FileNode[];
  path: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  timestamp: Date;
}

interface WorkspaceState {
  // Assessment info
  assessmentId: string;
  taskId: string;
  taskTitle: string;
  taskDescription: string;
  timeLimit: number;
  deadline: Date | null;
  
  // File system
  files: FileNode[];
  activeFileId: string | null;
  openFileIds: string[];
  
  // Editor
  editorContent: Record<string, string>;  // fileId -> content
  
  // AI Chat
  selectedModel: string;
  chatMessages: ChatMessage[];
  isAiLoading: boolean;
  
  // Terminal
  terminalOutput: string[];
  isTerminalOpen: boolean;
  
  // Status
  status: 'loading' | 'ready' | 'submitting' | 'submitted' | 'error';
  error: string | null;
  
  // Tracking
  startedAt: Date | null;
  timeSpent: number;  // seconds
}

type WorkspaceAction =
  | { type: 'SET_ASSESSMENT_INFO'; payload: Partial<WorkspaceState> }
  | { type: 'SET_FILES'; payload: FileNode[] }
  | { type: 'OPEN_FILE'; payload: string }
  | { type: 'CLOSE_FILE'; payload: string }
  | { type: 'SET_ACTIVE_FILE'; payload: string }
  | { type: 'UPDATE_FILE_CONTENT'; payload: { fileId: string; content: string } }
  | { type: 'CREATE_FILE'; payload: { path: string; content?: string } }
  | { type: 'DELETE_FILE'; payload: string }
  | { type: 'SET_MODEL'; payload: string }
  | { type: 'ADD_CHAT_MESSAGE'; payload: ChatMessage }
  | { type: 'SET_AI_LOADING'; payload: boolean }
  | { type: 'APPEND_TERMINAL_OUTPUT'; payload: string }
  | { type: 'TOGGLE_TERMINAL' }
  | { type: 'SET_STATUS'; payload: WorkspaceState['status'] }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'UPDATE_TIME_SPENT'; payload: number };

const initialState: WorkspaceState = {
  assessmentId: '',
  taskId: '',
  taskTitle: '',
  taskDescription: '',
  timeLimit: 120,
  deadline: null,
  files: [],
  activeFileId: null,
  openFileIds: [],
  editorContent: {},
  selectedModel: 'claude-sonnet-4-20250514',
  chatMessages: [],
  isAiLoading: false,
  terminalOutput: [],
  isTerminalOpen: false,
  status: 'loading',
  error: null,
  startedAt: null,
  timeSpent: 0,
};

function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case 'SET_ASSESSMENT_INFO':
      return { ...state, ...action.payload };
    
    case 'SET_FILES':
      return { ...state, files: action.payload };
    
    case 'OPEN_FILE':
      if (state.openFileIds.includes(action.payload)) {
        return { ...state, activeFileId: action.payload };
      }
      return {
        ...state,
        openFileIds: [...state.openFileIds, action.payload],
        activeFileId: action.payload,
      };
    
    case 'CLOSE_FILE':
      const newOpenIds = state.openFileIds.filter(id => id !== action.payload);
      const newActiveId = state.activeFileId === action.payload
        ? newOpenIds[newOpenIds.length - 1] || null
        : state.activeFileId;
      return {
        ...state,
        openFileIds: newOpenIds,
        activeFileId: newActiveId,
      };
    
    case 'SET_ACTIVE_FILE':
      return { ...state, activeFileId: action.payload };
    
    case 'UPDATE_FILE_CONTENT':
      return {
        ...state,
        editorContent: {
          ...state.editorContent,
          [action.payload.fileId]: action.payload.content,
        },
      };
    
    case 'SET_MODEL':
      return { ...state, selectedModel: action.payload };
    
    case 'ADD_CHAT_MESSAGE':
      return {
        ...state,
        chatMessages: [...state.chatMessages, action.payload],
      };
    
    case 'SET_AI_LOADING':
      return { ...state, isAiLoading: action.payload };
    
    case 'APPEND_TERMINAL_OUTPUT':
      return {
        ...state,
        terminalOutput: [...state.terminalOutput, action.payload],
      };
    
    case 'TOGGLE_TERMINAL':
      return { ...state, isTerminalOpen: !state.isTerminalOpen };
    
    case 'SET_STATUS':
      return { ...state, status: action.payload };
    
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    
    case 'UPDATE_TIME_SPENT':
      return { ...state, timeSpent: action.payload };
    
    default:
      return state;
  }
}

// Context
interface WorkspaceContextType {
  state: WorkspaceState;
  dispatch: React.Dispatch<WorkspaceAction>;
  
  // Actions
  openFile: (fileId: string) => void;
  closeFile: (fileId: string) => void;
  updateFileContent: (fileId: string, content: string) => void;
  sendChatMessage: (message: string) => Promise<void>;
  runTerminalCommand: (command: string) => Promise<void>;
  submitAssessment: () => Promise<void>;
  
  // Socket
  socket: Socket | null;
}

const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within WorkspaceProvider');
  }
  return context;
}

// Provider
interface WorkspaceProviderProps {
  assessmentId: string;
  children: React.ReactNode;
}

export function WorkspaceProvider({ assessmentId, children }: WorkspaceProviderProps) {
  const [state, dispatch] = useReducer(workspaceReducer, {
    ...initialState,
    assessmentId,
  });
  
  const socketRef = useRef<Socket | null>(null);
  const trackingRef = useRef<TrackingManager | null>(null);

  // Initialize workspace
  useEffect(() => {
    async function initWorkspace() {
      try {
        // Fetch assessment data
        const response = await fetch(`/api/assessments/${assessmentId}`);
        if (!response.ok) throw new Error('Failed to fetch assessment');
        
        const data = await response.json();
        
        dispatch({
          type: 'SET_ASSESSMENT_INFO',
          payload: {
            taskId: data.task.id,
            taskTitle: data.task.title,
            taskDescription: data.task.description,
            timeLimit: data.task.timeLimitMinutes,
            deadline: new Date(data.deadline),
            startedAt: new Date(data.startedAt),
            status: 'ready',
          },
        });
        
        // Initialize files
        if (data.task.files?.length > 0) {
          dispatch({ type: 'SET_FILES', payload: buildFileTree(data.task.files) });
        } else {
          // Create default file structure
          dispatch({
            type: 'SET_FILES',
            payload: [
              {
                id: 'main',
                name: 'main.py',
                type: 'file',
                path: '/main.py',
                content: '# Start coding here\n',
              },
            ],
          });
        }
        
        // Connect to WebSocket
        socketRef.current = io(data.sandboxWsUrl, {
          transports: ['websocket'],
        });
        
        socketRef.current.on('terminal:output', (data: string) => {
          dispatch({ type: 'APPEND_TERMINAL_OUTPUT', payload: data });
        });
        
        // Initialize tracking
        trackingRef.current = new TrackingManager(assessmentId);
        
      } catch (error) {
        dispatch({ type: 'SET_STATUS', payload: 'error' });
        dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
      }
    }
    
    initWorkspace();
    
    return () => {
      socketRef.current?.disconnect();
      trackingRef.current?.flush();
    };
  }, [assessmentId]);

  // Timer update
  useEffect(() => {
    if (state.status !== 'ready' || !state.startedAt) return;
    
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.startedAt!.getTime()) / 1000);
      dispatch({ type: 'UPDATE_TIME_SPENT', payload: elapsed });
    }, 1000);
    
    return () => clearInterval(interval);
  }, [state.status, state.startedAt]);

  // Actions
  const openFile = (fileId: string) => {
    dispatch({ type: 'OPEN_FILE', payload: fileId });
    trackingRef.current?.track('file_open', { fileId });
  };

  const closeFile = (fileId: string) => {
    dispatch({ type: 'CLOSE_FILE', payload: fileId });
  };

  const updateFileContent = (fileId: string, content: string) => {
    dispatch({ type: 'UPDATE_FILE_CONTENT', payload: { fileId, content } });
    
    // Debounced tracking
    trackingRef.current?.trackCodeChange(fileId, content);
  };

  const sendChatMessage = async (message: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };
    
    dispatch({ type: 'ADD_CHAT_MESSAGE', payload: userMessage });
    dispatch({ type: 'SET_AI_LOADING', payload: true });
    
    // Track AI prompt
    trackingRef.current?.track('ai_prompt', {
      model: state.selectedModel,
      prompt: message,
    });
    
    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          assessmentId,
          model: state.selectedModel,
          messages: [
            ...state.chatMessages.map(m => ({ role: m.role, content: m.content })),
            { role: 'user', content: message },
          ],
        }),
      });
      
      if (!response.ok) throw new Error('AI request failed');
      
      const data = await response.json();
      
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.content,
        model: state.selectedModel,
        timestamp: new Date(),
      };
      
      dispatch({ type: 'ADD_CHAT_MESSAGE', payload: assistantMessage });
      
      // Track AI response
      trackingRef.current?.track('ai_response', {
        model: state.selectedModel,
        responseLength: data.content.length,
        tokenCount: data.usage?.totalTokens,
      });
      
    } catch (error) {
      dispatch({
        type: 'SET_ERROR',
        payload: 'Failed to get AI response. Please try again.',
      });
    } finally {
      dispatch({ type: 'SET_AI_LOADING', payload: false });
    }
  };

  const runTerminalCommand = async (command: string) => {
    trackingRef.current?.track('terminal_command', { command });
    
    socketRef.current?.emit('terminal:input', command);
  };

  const submitAssessment = async () => {
    dispatch({ type: 'SET_STATUS', payload: 'submitting' });
    
    try {
      // Flush tracking data
      await trackingRef.current?.flush();
      
      // Prepare submission
      const files = Object.entries(state.editorContent).map(([fileId, content]) => {
        const file = findFileById(state.files, fileId);
        return {
          fileName: file?.name || fileId,
          content,
        };
      });
      
      const response = await fetch(`/api/assessments/${assessmentId}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files,
          notes: '', // Could add a notes field
        }),
      });
      
      if (!response.ok) throw new Error('Submission failed');
      
      dispatch({ type: 'SET_STATUS', payload: 'submitted' });
      
    } catch (error) {
      dispatch({ type: 'SET_STATUS', payload: 'error' });
      dispatch({ type: 'SET_ERROR', payload: (error as Error).message });
    }
  };

  const value: WorkspaceContextType = {
    state,
    dispatch,
    openFile,
    closeFile,
    updateFileContent,
    sendChatMessage,
    runTerminalCommand,
    submitAssessment,
    socket: socketRef.current,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

// Helper functions
function buildFileTree(files: any[]): FileNode[] {
  // Implementation to build file tree from flat list
  return files.map(f => ({
    id: f.id,
    name: f.fileName,
    type: 'file' as const,
    path: f.relativePath || `/${f.fileName}`,
    content: f.content || '',
  }));
}

function findFileById(files: FileNode[], id: string): FileNode | null {
  for (const file of files) {
    if (file.id === id) return file;
    if (file.children) {
      const found = findFileById(file.children, id);
      if (found) return found;
    }
  }
  return null;
}

// Tracking Manager
class TrackingManager {
  private assessmentId: string;
  private events: any[] = [];
  private codeSnapshots: Map<string, string> = new Map();
  private lastSnapshotTime: number = 0;
  
  constructor(assessmentId: string) {
    this.assessmentId = assessmentId;
    
    // Flush events periodically
    setInterval(() => this.flush(), 30000);
  }
  
  track(eventType: string, data: any) {
    this.events.push({
      type: eventType,
      data,
      timestamp: new Date().toISOString(),
    });
    
    // Flush if too many events
    if (this.events.length >= 50) {
      this.flush();
    }
  }
  
  trackCodeChange(fileId: string, content: string) {
    const now = Date.now();
    
    // Debounce: only snapshot every 30 seconds
    if (now - this.lastSnapshotTime < 30000) {
      return;
    }
    
    this.lastSnapshotTime = now;
    this.codeSnapshots.set(fileId, content);
    
    this.track('code_snapshot', {
      fileId,
      contentLength: content.length,
    });
  }
  
  async flush() {
    if (this.events.length === 0) return;
    
    const eventsToSend = [...this.events];
    this.events = [];
    
    try {
      await fetch(`/api/assessments/${this.assessmentId}/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events: eventsToSend }),
      });
    } catch (error) {
      // Re-add events on failure
      this.events = [...eventsToSend, ...this.events];
      console.error('Failed to flush tracking events:', error);
    }
  }
}
```

## 6.3 Monaco Editor Component

```typescript
// =============================================================================
// FILE: src/components/workspace/MonacoEditor.tsx
// =============================================================================

'use client';

import React, { useRef, useEffect } from 'react';
import Editor, { OnMount, OnChange } from '@monaco-editor/react';
import { useWorkspace } from './WorkspaceContext';

interface MonacoEditorProps {
  fileId: string;
  language?: string;
}

export function MonacoEditor({ fileId, language }: MonacoEditorProps) {
  const { state, updateFileContent } = useWorkspace();
  const editorRef = useRef<any>(null);
  
  const content = state.editorContent[fileId] || '';
  
  // Determine language from file extension
  const detectedLanguage = language || detectLanguage(
    state.files.find(f => f.id === fileId)?.name || ''
  );

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    
    // Configure editor
    editor.updateOptions({
      fontSize: 14,
      minimap: { enabled: true },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      tabSize: 2,
      wordWrap: 'on',
    });
    
    // Add custom keybindings
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      // Auto-save is handled by onChange
      console.log('Saved');
    });
  };

  const handleChange: OnChange = (value) => {
    if (value !== undefined) {
      updateFileContent(fileId, value);
    }
  };

  return (
    <div className="h-full w-full">
      <Editor
        height="100%"
        language={detectedLanguage}
        value={content}
        theme="vs-dark"
        onMount={handleEditorMount}
        onChange={handleChange}
        options={{
          readOnly: state.status !== 'ready',
        }}
      />
    </div>
  );
}

function detectLanguage(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'py': 'python',
    'rb': 'ruby',
    'go': 'go',
    'rs': 'rust',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
    'h': 'c',
    'hpp': 'cpp',
    'cs': 'csharp',
    'php': 'php',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'json': 'json',
    'xml': 'xml',
    'yaml': 'yaml',
    'yml': 'yaml',
    'md': 'markdown',
    'sql': 'sql',
    'sh': 'shell',
    'bash': 'shell',
  };
  
  return languageMap[ext || ''] || 'plaintext';
}
```

## 6.4 AI Chat Panel Component

```typescript
// =============================================================================
// FILE: src/components/workspace/AIChatPanel.tsx
// =============================================================================

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useWorkspace } from './WorkspaceContext';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, Send, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const MODELS = [
  { id: 'claude-sonnet-4-20250514', name: 'Claude Sonnet 4', icon: '🟣' },
  { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', icon: '🟣' },
  { id: 'gpt-4o', name: 'GPT-4o', icon: '🟢' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini', icon: '🟢' },
];

export function AIChatPanel() {
  const { state, dispatch, sendChatMessage } = useWorkspace();
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.chatMessages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || state.isAiLoading) return;
    
    const message = input.trim();
    setInput('');
    
    await sendChatMessage(message);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Model Selector */}
      <div className="p-3 border-b border-gray-700">
        <Select
          value={state.selectedModel}
          onValueChange={(value) => dispatch({ type: 'SET_MODEL', payload: value })}
        >
          <SelectTrigger className="w-full bg-gray-800 border-gray-700 text-white">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent className="bg-gray-800 border-gray-700">
            {MODELS.map((model) => (
              <SelectItem 
                key={model.id} 
                value={model.id}
                className="text-white hover:bg-gray-700"
              >
                <span className="flex items-center gap-2">
                  <span>{model.icon}</span>
                  <span>{model.name}</span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Chat History */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
          {state.chatMessages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <p className="text-lg mb-2">👋 Hi! I'm your AI assistant.</p>
              <p className="text-sm">
                Ask me anything about your task. I can help with:
              </p>
              <ul className="text-sm mt-2 space-y-1">
                <li>• Understanding requirements</li>
                <li>• Writing and debugging code</li>
                <li>• Explaining concepts</li>
                <li>• Suggesting approaches</li>
              </ul>
            </div>
          )}
          
          {state.chatMessages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          
          {state.isAiLoading && (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-gray-700">
        <div className="flex gap-2">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything... (Shift+Enter for new line)"
            className="flex-1 min-h-[60px] max-h-[200px] bg-gray-800 border-gray-700 
                       text-white placeholder:text-gray-500 resize-none"
            disabled={state.isAiLoading || state.status !== 'ready'}
          />
          <Button 
            type="submit" 
            size="icon"
            disabled={!input.trim() || state.isAiLoading || state.status !== 'ready'}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  );
}

// Chat Message Component
interface ChatMessageProps {
  message: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    model?: string;
    timestamp: Date;
  };
}

function ChatMessage({ message }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-blue-600 text-white rounded-lg px-4 py-2">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] bg-gray-800 text-gray-100 rounded-lg px-4 py-2">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">
            {message.model?.split('-').slice(0, 2).join(' ')}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3 text-gray-400" />
            )}
          </Button>
        </div>
        
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
```
# 7. AI Scoring Engine

## 7.1 Scoring Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SCORING PIPELINE ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐                                                             │
│  │  Assessment     │                                                             │
│  │  Submitted      │                                                             │
│  └────────┬────────┘                                                             │
│           │                                                                      │
│           ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 1: DATA COLLECTION                                                 │    │
│  │  ───────────────────────                                                 │    │
│  │  • Fetch tracking data from R2                                           │    │
│  │  • Fetch submission files                                                │    │
│  │  • Fetch task requirements                                               │    │
│  │  • Fetch evaluation config                                               │    │
│  └────────────────────────────────┬────────────────────────────────────────┘    │
│                                   │                                              │
│                                   ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 2: DATA PREPROCESSING                                              │    │
│  │  ──────────────────────────                                              │    │
│  │                                                                          │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       │    │
│  │  │ AI Interaction   │  │ Code Evolution   │  │ Time Analysis    │       │    │
│  │  │ Extractor        │  │ Analyzer         │  │                  │       │    │
│  │  │                  │  │                  │  │ • Time per file  │       │    │
│  │  │ • Prompts        │  │ • Diff timeline  │  │ • AI vs coding   │       │    │
│  │  │ • Responses      │  │ • Iterations     │  │ • Idle time      │       │    │
│  │  │ • Models used    │  │ • Final vs init  │  │                  │       │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘       │    │
│  │                                                                          │    │
│  └────────────────────────────────┬────────────────────────────────────────┘    │
│                                   │                                              │
│                                   ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 3: CATEGORY EVALUATION (Parallel)                                  │    │
│  │  ──────────────────────────────────────                                  │    │
│  │                                                                          │    │
│  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌───────────┐ │    │
│  │  │ Planning       │ │ Prompt         │ │ Tool           │ │ Outcome   │ │    │
│  │  │ Evaluator      │ │ Engineering    │ │ Orchestration  │ │ Quality   │ │    │
│  │  │                │ │ Evaluator      │ │ Evaluator      │ │ Evaluator │ │    │
│  │  │ AI Model Call  │ │ AI Model Call  │ │ AI Model Call  │ │ Code      │ │    │
│  │  │ with prompt    │ │ with prompt    │ │ with prompt    │ │ Analysis  │ │    │
│  │  └───────┬────────┘ └───────┬────────┘ └───────┬────────┘ └─────┬─────┘ │    │
│  │          │                  │                  │                │       │    │
│  │          ▼                  ▼                  ▼                ▼       │    │
│  │      Subitem            Subitem            Subitem          Subitem     │    │
│  │      Scores             Scores             Scores           Scores      │    │
│  │                                                                          │    │
│  └────────────────────────────────┬────────────────────────────────────────┘    │
│                                   │                                              │
│                                   ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 4: SCORE CALCULATION                                               │    │
│  │  ─────────────────────────                                               │    │
│  │                                                                          │    │
│  │  For each subitem:                                                       │    │
│  │    weighted_score = raw_score × subitem_weight_for_task_type             │    │
│  │                                                                          │    │
│  │  For each category:                                                      │    │
│  │    category_score = sum(weighted_subitem_scores) × category_weight       │    │
│  │                                                                          │    │
│  │  Final score = sum(category_scores)                                      │    │
│  │                                                                          │    │
│  └────────────────────────────────┬────────────────────────────────────────┘    │
│                                   │                                              │
│                                   ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  STEP 5: LEVEL DETERMINATION & FEEDBACK                                  │    │
│  │  ──────────────────────────────────────                                  │    │
│  │                                                                          │    │
│  │  • Determine proficiency level from score                                │    │
│  │  • Generate strengths list                                               │    │
│  │  • Generate improvements list                                            │    │
│  │  • Extract AI interaction highlights                                     │    │
│  │  • Create detailed analysis report                                       │    │
│  │                                                                          │    │
│  └────────────────────────────────┬────────────────────────────────────────┘    │
│                                   │                                              │
│                                   ▼                                              │
│  ┌─────────────────┐                                                             │
│  │  Save Score to  │                                                             │
│  │  Database       │                                                             │
│  └─────────────────┘                                                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Scoring Service Implementation

```python
# =============================================================================
# FILE: app/scoring/pipeline.py
# =============================================================================

import asyncio
from uuid import UUID
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.assessment import Assessment, AssessmentStatus
from app.models.score import Score
from app.models.task import Task
from app.schemas.score import ScoreCreate, CategoryScore, SubitemScore
from app.services.storage_service import StorageService
from app.services.ai_service import AIService
from app.scoring.evaluators import (
    PlanningEvaluator,
    PromptEngineeringEvaluator,
    ToolOrchestrationEvaluator,
    OutcomeQualityEvaluator,
)
from app.config import settings

@dataclass
class ProcessedData:
    """Preprocessed assessment data for scoring."""
    assessment_id: str
    task: Dict[str, Any]
    tracking_data: Dict[str, Any]
    submission: Dict[str, Any]
    eval_config: Dict[str, Any]
    
    # Extracted features
    ai_interactions: List[Dict]
    code_snapshots: List[Dict]
    time_metrics: Dict[str, int]
    models_used: List[str]

class ScoringPipeline:
    """Main scoring pipeline for AI Skills Lab assessments."""
    
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageService,
        ai_service: AIService,
    ):
        self.db = db
        self.storage = storage
        self.ai_service = ai_service
        
        # Initialize evaluators
        self.evaluators = {
            'planning': PlanningEvaluator(ai_service),
            'prompt_engineering': PromptEngineeringEvaluator(ai_service),
            'tool_orchestration': ToolOrchestrationEvaluator(ai_service),
            'outcome_quality': OutcomeQualityEvaluator(ai_service),
        }

    async def score_assessment(self, assessment_id: UUID) -> Score:
        """Main entry point for scoring an assessment."""
        
        # Update status to scoring
        assessment = await self.db.get(Assessment, assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")
        
        assessment.status = AssessmentStatus.SCORING
        await self.db.flush()
        
        try:
            # Step 1: Collect data
            processed_data = await self._collect_and_preprocess(assessment)
            
            # Step 2: Run evaluators in parallel
            category_results = await self._run_evaluators(processed_data)
            
            # Step 3: Calculate final scores
            score_result = self._calculate_scores(
                category_results, 
                processed_data.eval_config
            )
            
            # Step 4: Generate feedback
            feedback = await self._generate_feedback(
                processed_data, 
                category_results,
                score_result
            )
            
            # Step 5: Save score
            score = Score(
                assessment_id=assessment_id,
                final_score=score_result['final_score'],
                proficiency_level=score_result['level'],
                category_scores=score_result['category_scores'],
                subitem_scores=score_result['subitem_scores'],
                strengths=feedback['strengths'],
                improvements=feedback['improvements'],
                ai_highlights=feedback['highlights'],
                detailed_analysis=feedback['detailed_analysis'],
                scoring_model=settings.SCORING_MODEL,
                scoring_version="1.0",
            )
            
            self.db.add(score)
            
            # Update assessment status
            assessment.status = AssessmentStatus.SCORED
            assessment.scored_at = datetime.utcnow()
            
            await self.db.flush()
            
            return score
            
        except Exception as e:
            assessment.status = AssessmentStatus.FAILED
            await self.db.flush()
            raise

    async def _collect_and_preprocess(self, assessment: Assessment) -> ProcessedData:
        """Collect and preprocess all data needed for scoring."""
        
        # Fetch task with config
        task = await self.db.get(
            Task, 
            assessment.task_id,
            options=[selectinload(Task.evaluation_config)]
        )
        
        # Fetch tracking data from R2
        tracking_data = {}
        if assessment.tracking_data_url:
            tracking_data = await self.storage.download_json(
                assessment.tracking_data_url
            )
        
        # Extract AI interactions
        ai_interactions = [
            event for event in tracking_data.get('events', [])
            if event['type'] in ('ai_prompt', 'ai_response')
        ]
        
        # Extract code snapshots
        code_snapshots = [
            event for event in tracking_data.get('events', [])
            if event['type'] == 'code_snapshot'
        ]
        
        # Calculate time metrics
        time_metrics = self._calculate_time_metrics(tracking_data)
        
        # Get models used
        models_used = list(set(
            event['data'].get('model') 
            for event in ai_interactions 
            if event['data'].get('model')
        ))
        
        return ProcessedData(
            assessment_id=str(assessment.id),
            task={
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'task_type': task.task_type.value,
                'difficulty': task.difficulty.value,
            },
            tracking_data=tracking_data,
            submission={
                'files': assessment.submission_files or [],
                'notes': assessment.submission_notes,
                'time_spent': assessment.time_spent_seconds,
            },
            eval_config={
                'category_weights': task.evaluation_config.category_weights,
                'subitem_weights': task.evaluation_config.subitem_weights,
                'level_thresholds': task.evaluation_config.level_thresholds,
            },
            ai_interactions=ai_interactions,
            code_snapshots=code_snapshots,
            time_metrics=time_metrics,
            models_used=models_used,
        )

    async def _run_evaluators(
        self, 
        data: ProcessedData
    ) -> Dict[str, Dict[str, Any]]:
        """Run all category evaluators in parallel."""
        
        # Create evaluation tasks
        tasks = {
            category: evaluator.evaluate(data)
            for category, evaluator in self.evaluators.items()
        }
        
        # Run in parallel
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        # Map results back to categories
        category_results = {}
        for category, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                # Log error and use default scores
                print(f"Error in {category} evaluator: {result}")
                category_results[category] = {
                    'subitems': {},
                    'reasoning': f"Evaluation failed: {str(result)}",
                    'error': True,
                }
            else:
                category_results[category] = result
        
        return category_results

    def _calculate_scores(
        self,
        category_results: Dict[str, Dict],
        eval_config: Dict,
    ) -> Dict[str, Any]:
        """Calculate final scores using weights."""
        
        category_weights = eval_config['category_weights']
        subitem_weights = eval_config['subitem_weights']
        level_thresholds = eval_config['level_thresholds']
        
        category_scores = {}
        subitem_scores = {}
        
        for category, result in category_results.items():
            if result.get('error'):
                category_scores[category] = 50  # Default score on error
                subitem_scores[category] = {}
                continue
            
            # Calculate weighted subitem scores
            category_subitem_scores = {}
            category_total = 0
            
            for subitem, raw_score in result.get('subitems', {}).items():
                # Get weight for this subitem
                weight = subitem_weights.get(category, {}).get(subitem, 25) / 100
                weighted_score = raw_score * weight
                category_subitem_scores[subitem] = {
                    'raw': raw_score,
                    'weight': weight * 100,
                    'weighted': weighted_score,
                }
                category_total += weighted_score
            
            subitem_scores[category] = category_subitem_scores
            category_scores[category] = category_total
        
        # Calculate final score
        final_score = sum(
            score * (category_weights.get(cat, 25) / 100)
            for cat, score in category_scores.items()
        )
        
        # Determine level
        level = 'operator'
        for level_name, thresholds in level_thresholds.items():
            if thresholds['min'] <= final_score <= thresholds['max']:
                level = level_name
                break
        
        return {
            'final_score': round(final_score, 2),
            'level': level,
            'category_scores': category_scores,
            'subitem_scores': subitem_scores,
        }

    async def _generate_feedback(
        self,
        data: ProcessedData,
        category_results: Dict[str, Dict],
        score_result: Dict,
    ) -> Dict[str, Any]:
        """Generate human-readable feedback."""
        
        # Collect strengths and improvements from evaluators
        strengths = []
        improvements = []
        
        for category, result in category_results.items():
            if not result.get('error'):
                strengths.extend(result.get('strengths', []))
                improvements.extend(result.get('improvements', []))
        
        # Deduplicate and limit
        strengths = list(set(strengths))[:5]
        improvements = list(set(improvements))[:5]
        
        # Extract AI interaction highlights
        highlights = self._extract_highlights(data.ai_interactions)
        
        # Generate detailed analysis
        detailed_analysis = {
            'summary': self._generate_summary(score_result, data),
            'category_analysis': {
                cat: result.get('reasoning', '')
                for cat, result in category_results.items()
            },
            'time_analysis': data.time_metrics,
            'ai_usage_analysis': {
                'total_prompts': len([
                    i for i in data.ai_interactions 
                    if i['type'] == 'ai_prompt'
                ]),
                'models_used': data.models_used,
                'prompt_patterns': self._analyze_prompt_patterns(data.ai_interactions),
            },
        }
        
        return {
            'strengths': strengths,
            'improvements': improvements,
            'highlights': highlights,
            'detailed_analysis': detailed_analysis,
        }

    def _calculate_time_metrics(self, tracking_data: Dict) -> Dict[str, int]:
        """Calculate time spent on different activities."""
        
        events = tracking_data.get('events', [])
        
        metrics = {
            'total_time': 0,
            'ai_interaction_time': 0,
            'coding_time': 0,
            'idle_time': 0,
        }
        
        if not events:
            return metrics
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda x: x['timestamp'])
        
        for i, event in enumerate(sorted_events[:-1]):
            current_time = datetime.fromisoformat(event['timestamp'])
            next_time = datetime.fromisoformat(sorted_events[i + 1]['timestamp'])
            duration = (next_time - current_time).total_seconds()
            
            # Cap at 5 minutes to handle idle periods
            duration = min(duration, 300)
            
            if event['type'] in ('ai_prompt', 'ai_response'):
                metrics['ai_interaction_time'] += duration
            elif event['type'] in ('code_edit', 'code_snapshot'):
                metrics['coding_time'] += duration
            else:
                metrics['idle_time'] += duration
        
        metrics['total_time'] = (
            metrics['ai_interaction_time'] + 
            metrics['coding_time'] + 
            metrics['idle_time']
        )
        
        return metrics

    def _extract_highlights(self, ai_interactions: List[Dict]) -> List[Dict]:
        """Extract notable AI interactions as highlights."""
        
        highlights = []
        
        prompts = [i for i in ai_interactions if i['type'] == 'ai_prompt']
        
        # Find first prompt (shows initial approach)
        if prompts:
            highlights.append({
                'type': 'first_prompt',
                'description': 'Initial approach to the problem',
                'content': prompts[0]['data'].get('prompt', '')[:200],
            })
        
        # Find longest prompt (shows detailed thinking)
        if prompts:
            longest = max(prompts, key=lambda x: len(x['data'].get('prompt', '')))
            if len(longest['data'].get('prompt', '')) > 100:
                highlights.append({
                    'type': 'detailed_prompt',
                    'description': 'Most detailed prompt showing problem decomposition',
                    'content': longest['data'].get('prompt', '')[:200],
                })
        
        return highlights[:3]

    def _analyze_prompt_patterns(self, ai_interactions: List[Dict]) -> Dict:
        """Analyze patterns in AI prompts."""
        
        prompts = [
            i['data'].get('prompt', '') 
            for i in ai_interactions 
            if i['type'] == 'ai_prompt'
        ]
        
        if not prompts:
            return {}
        
        return {
            'total_prompts': len(prompts),
            'avg_prompt_length': sum(len(p) for p in prompts) // len(prompts),
            'used_code_blocks': any('```' in p for p in prompts),
            'asked_questions': sum(1 for p in prompts if '?' in p),
        }

    def _generate_summary(self, score_result: Dict, data: ProcessedData) -> str:
        """Generate a text summary of the assessment."""
        
        level = score_result['level']
        score = score_result['final_score']
        
        level_descriptions = {
            'operator': 'demonstrating solid fundamentals in AI tool usage',
            'architect': 'showing advanced ability to orchestrate AI tools effectively',
            'innovator': 'exhibiting exceptional creativity and mastery with AI',
        }
        
        return (
            f"Assessment completed with a score of {score}/100, "
            f"achieving the {level.title()} level. "
            f"The candidate demonstrated proficiency {level_descriptions.get(level, '')}. "
            f"Total time spent: {data.time_metrics.get('total_time', 0) // 60} minutes."
        )
```

## 7.3 Category Evaluators

```python
# =============================================================================
# FILE: app/scoring/evaluators/prompt_engineering.py
# =============================================================================

from typing import Dict, Any, List
from app.services.ai_service import AIService
from app.scoring.evaluators.base import BaseEvaluator

class PromptEngineeringEvaluator(BaseEvaluator):
    """Evaluator for Prompt Engineering category."""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service

    async def evaluate(self, data: 'ProcessedData') -> Dict[str, Any]:
        """Evaluate prompt engineering skills."""
        
        # Extract relevant data
        ai_interactions = data.ai_interactions
        prompts = [
            i['data'].get('prompt', '') 
            for i in ai_interactions 
            if i['type'] == 'ai_prompt'
        ]
        responses = [
            i['data'] 
            for i in ai_interactions 
            if i['type'] == 'ai_response'
        ]
        
        if not prompts:
            return self._default_result("No AI interactions found")
        
        # Prepare evaluation prompt
        evaluation_prompt = self._build_evaluation_prompt(
            prompts, responses, data.task
        )
        
        # Call AI for evaluation
        result = await self.ai_service.chat(
            ChatRequest(
                model="claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": evaluation_prompt}],
                system_prompt=self._system_prompt(),
            )
        )
        
        # Parse response
        return self._parse_response(result.content)

    def _system_prompt(self) -> str:
        return """You are an expert evaluator assessing AI prompt engineering skills.
        
Your task is to evaluate how effectively a candidate uses AI tools based on their prompts and the responses they received.

Be objective and fair. Consider:
- Clarity and specificity of prompts
- Effective use of context
- How quickly they iterate to good solutions
- How they handle errors or misunderstandings

Always respond with valid JSON in the exact format specified."""

    def _build_evaluation_prompt(
        self, 
        prompts: List[str], 
        responses: List[Dict],
        task: Dict
    ) -> str:
        
        # Sample prompts if too many
        sample_prompts = prompts[:10] if len(prompts) > 10 else prompts
        
        prompts_text = "\n\n---\n\n".join([
            f"PROMPT {i+1}:\n{p[:500]}"
            for i, p in enumerate(sample_prompts)
        ])
        
        return f"""## Task Context
Title: {task['title']}
Type: {task['task_type']}
Difficulty: {task['difficulty']}

## Candidate's AI Prompts
Total prompts: {len(prompts)}
Showing first {len(sample_prompts)} prompts:

{prompts_text}

## Evaluation Criteria

Score each criterion from 1-10:

1. **Clarity & Specificity** (clarity_specificity)
   - Are prompts clear and unambiguous?
   - Do they include necessary context and constraints?
   - Are requirements well-defined?

2. **Context Management** (context_management)
   - Does the candidate reference previous responses appropriately?
   - Is information organized logically across prompts?
   - Do they avoid unnecessary repetition?

3. **Iteration Efficiency** (iteration_efficiency)
   - How many prompts to reach good solutions? (fewer = better)
   - Do they refine prompts based on feedback?
   - Are iterations targeted and purposeful?

4. **Error Recovery** (error_recovery)
   - How do they handle incorrect AI responses?
   - Are corrections clear and specific?
   - Do they verify AI outputs?

## Response Format

Respond with ONLY this JSON structure:
{{
  "subitems": {{
    "clarity_specificity": <score 1-10>,
    "context_management": <score 1-10>,
    "iteration_efficiency": <score 1-10>,
    "error_recovery": <score 1-10>
  }},
  "reasoning": "<2-3 sentence explanation>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<improvement 1>", "<improvement 2>"]
}}"""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI's evaluation response."""
        import json
        
        try:
            # Try to extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            
            result = json.loads(json_str)
            
            # Normalize scores to 0-100 scale
            subitems = result.get('subitems', {})
            normalized_subitems = {
                k: v * 10 for k, v in subitems.items()
            }
            
            return {
                'subitems': normalized_subitems,
                'reasoning': result.get('reasoning', ''),
                'strengths': result.get('strengths', []),
                'improvements': result.get('improvements', []),
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            return self._default_result(f"Failed to parse evaluation: {e}")

    def _default_result(self, reason: str) -> Dict[str, Any]:
        """Return default result when evaluation fails."""
        return {
            'subitems': {
                'clarity_specificity': 50,
                'context_management': 50,
                'iteration_efficiency': 50,
                'error_recovery': 50,
            },
            'reasoning': reason,
            'strengths': [],
            'improvements': [],
            'error': True,
        }
```

---

# 8. Frontend Implementation (Continued)

## 8.1 Results Page Component

```typescript
// =============================================================================
// FILE: src/app/results/[id]/page.tsx
// =============================================================================

import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { getAssessmentWithScore } from '@/lib/api/assessments';
import { ScoreCard } from '@/components/results/ScoreCard';
import { CategoryBreakdown } from '@/components/results/CategoryBreakdown';
import { AIHighlights } from '@/components/results/AIHighlights';
import { ShareButtons } from '@/components/results/ShareButtons';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ResultsPageProps {
  params: { id: string };
}

export default async function ResultsPage({ params }: ResultsPageProps) {
  const assessment = await getAssessmentWithScore(params.id);
  
  if (!assessment || !assessment.score) {
    notFound();
  }

  const { task, score, user, submittedAt } = assessment;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            AI Skills Assessment Results
          </h1>
          <p className="text-gray-600">
            {task.title} • Completed {new Date(submittedAt).toLocaleDateString()}
          </p>
        </div>

        {/* Main Score Card */}
        <Card className="mb-8 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 p-8 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 mb-2">Overall Score</p>
                <div className="flex items-baseline gap-4">
                  <span className="text-6xl font-bold">{score.finalScore}</span>
                  <span className="text-2xl">/100</span>
                </div>
              </div>
              
              <div className="text-right">
                <p className="text-blue-100 mb-2">Proficiency Level</p>
                <LevelBadge level={score.proficiencyLevel} />
              </div>
            </div>
          </div>
          
          <CardContent className="p-6">
            <p className="text-gray-700">
              {score.detailedAnalysis?.summary}
            </p>
          </CardContent>
        </Card>

        {/* Category Breakdown */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Category Scores</CardTitle>
            </CardHeader>
            <CardContent>
              <CategoryBreakdown 
                categoryScores={score.categoryScores}
                subitemScores={score.subitemScores}
              />
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Score Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <RadarChart data={score.categoryScores} />
            </CardContent>
          </Card>
        </div>

        {/* Strengths & Improvements */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-green-700">💪 Strengths</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {score.strengths.map((strength, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-green-500 mt-1">✓</span>
                    <span>{strength}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="text-orange-700">📈 Areas for Growth</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {score.improvements.map((improvement, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-orange-500 mt-1">→</span>
                    <span>{improvement}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* AI Highlights */}
        {score.aiHighlights?.length > 0 && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>🤖 AI Interaction Highlights</CardTitle>
            </CardHeader>
            <CardContent>
              <AIHighlights highlights={score.aiHighlights} />
            </CardContent>
          </Card>
        )}

        {/* Share Section */}
        <Card>
          <CardHeader>
            <CardTitle>Share Your Results</CardTitle>
          </CardHeader>
          <CardContent>
            <ShareButtons 
              assessmentId={params.id}
              score={score.finalScore}
              level={score.proficiencyLevel}
              taskTitle={task.title}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// Level Badge Component
function LevelBadge({ level }: { level: string }) {
  const config = {
    operator: {
      label: 'AI Operator',
      color: 'bg-blue-500',
      icon: '🔧',
    },
    architect: {
      label: 'AI Architect',
      color: 'bg-purple-500',
      icon: '🏗️',
    },
    innovator: {
      label: 'AI Innovator',
      color: 'bg-amber-500',
      icon: '🚀',
    },
  }[level] || { label: level, color: 'bg-gray-500', icon: '📊' };

  return (
    <div className={`${config.color} text-white px-4 py-2 rounded-lg inline-flex items-center gap-2`}>
      <span className="text-2xl">{config.icon}</span>
      <span className="text-xl font-semibold">{config.label}</span>
    </div>
  );
}
```

## 8.2 Share Buttons Component

```typescript
// =============================================================================
// FILE: src/components/results/ShareButtons.tsx
// =============================================================================

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Linkedin, 
  Twitter, 
  Mail, 
  Link, 
  Check, 
  Copy 
} from 'lucide-react';
import { toast } from 'sonner';

interface ShareButtonsProps {
  assessmentId: string;
  score: number;
  level: string;
  taskTitle: string;
}

export function ShareButtons({ 
  assessmentId, 
  score, 
  level, 
  taskTitle 
}: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);
  
  const shareUrl = `${process.env.NEXT_PUBLIC_APP_URL}/results/${assessmentId}`;
  
  const levelEmoji = {
    operator: '🔧',
    architect: '🏗️',
    innovator: '🚀',
  }[level] || '📊';
  
  const shareText = `I just scored ${score}/100 on the "${taskTitle}" AI assessment and earned the ${level.charAt(0).toUpperCase() + level.slice(1)} badge ${levelEmoji}! Check out SmartSuccess.AI to test your AI skills.`;

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    toast.success('Link copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleLinkedIn = () => {
    const linkedInUrl = new URL('https://www.linkedin.com/sharing/share-offsite/');
    linkedInUrl.searchParams.set('url', shareUrl);
    window.open(linkedInUrl.toString(), '_blank', 'width=600,height=400');
  };

  const handleTwitter = () => {
    const twitterUrl = new URL('https://twitter.com/intent/tweet');
    twitterUrl.searchParams.set('text', shareText);
    twitterUrl.searchParams.set('url', shareUrl);
    window.open(twitterUrl.toString(), '_blank', 'width=600,height=400');
  };

  const handleEmail = () => {
    const subject = encodeURIComponent(`My AI Skills Assessment Results - ${taskTitle}`);
    const body = encodeURIComponent(`${shareText}\n\nView my results: ${shareUrl}`);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  };

  return (
    <div className="space-y-4">
      {/* Share URL */}
      <div className="flex gap-2">
        <Input 
          value={shareUrl} 
          readOnly 
          className="flex-1 bg-gray-50"
        />
        <Button 
          variant="outline" 
          size="icon"
          onClick={handleCopyLink}
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Social Buttons */}
      <div className="flex gap-3">
        <Button 
          onClick={handleLinkedIn}
          className="flex-1 bg-[#0077B5] hover:bg-[#006396]"
        >
          <Linkedin className="h-4 w-4 mr-2" />
          Share on LinkedIn
        </Button>
        
        <Button 
          onClick={handleTwitter}
          className="flex-1 bg-black hover:bg-gray-800"
        >
          <Twitter className="h-4 w-4 mr-2" />
          Post on X
        </Button>
        
        <Button 
          onClick={handleEmail}
          variant="outline"
          className="flex-1"
        >
          <Mail className="h-4 w-4 mr-2" />
          Email
        </Button>
      </div>

      {/* Preview Card */}
      <div className="mt-6 p-4 border rounded-lg bg-white">
        <p className="text-sm text-gray-500 mb-2">Preview:</p>
        <div className="border rounded-lg p-4 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-600 to-purple-600 flex items-center justify-center text-white font-bold">
              {score}
            </div>
            <div>
              <p className="font-semibold">AI Skills Verified</p>
              <p className="text-sm text-gray-600">{taskTitle}</p>
            </div>
          </div>
          <p className="text-sm">
            {levelEmoji} {level.charAt(0).toUpperCase() + level.slice(1)} Level
          </p>
        </div>
      </div>
    </div>
  );
}
```

---

# 9. API Reference

## 9.1 Complete API Endpoints

### Authentication

```yaml
POST /api/auth/sync
  Description: Sync user from Clerk webhook
  Auth: Webhook signature
  Body:
    type: string (user.created | user.updated | user.deleted)
    data: ClerkUserData
  Response: 200 OK

GET /api/auth/me
  Description: Get current user
  Auth: Bearer token
  Response:
    id: string
    email: string
    name: string
    userType: "business" | "individual"
    subscription: SubscriptionInfo
```

### Tasks

```yaml
GET /api/tasks
  Description: List available tasks
  Auth: Bearer token
  Query:
    type?: TaskType
    difficulty?: Difficulty
    isDefault?: boolean
    limit?: number (default: 20)
    offset?: number (default: 0)
  Response:
    tasks: Task[]
    total: number
    hasMore: boolean

GET /api/tasks/:id
  Description: Get task details
  Auth: Bearer token
  Response: Task with files and eval config

POST /api/tasks
  Description: Create custom task (Business only)
  Auth: Bearer token (Business)
  Body:
    title: string
    description: string
    taskType: TaskType
    difficulty: Difficulty
    timeLimitMinutes: number
    files?: FileUpload[]
    evaluationConfig?: EvalConfig
    apiConfig?: ApiConfig
  Response: Task

PUT /api/tasks/:id
  Description: Update task
  Auth: Bearer token (Owner only)
  Body: Partial<Task>
  Response: Task

DELETE /api/tasks/:id
  Description: Delete task
  Auth: Bearer token (Owner only)
  Response: 204 No Content
```

### Assessments

```yaml
POST /api/assessments
  Description: Create new assessment
  Auth: Bearer token
  Body:
    taskId: string
    invitationId?: string
  Response:
    assessmentId: string
    status: "pending"

POST /api/assessments/:id/start
  Description: Start assessment (provision sandbox)
  Auth: Bearer token (Owner only)
  Response:
    assessmentId: string
    sandboxUrl: string
    websocketUrl: string
    startedAt: string (ISO)
    deadline: string (ISO)
    timeLimitMinutes: number

POST /api/assessments/:id/track
  Description: Submit tracking events
  Auth: Bearer token (Owner only)
  Body:
    events: TrackingEvent[]
  Response: 200 OK

POST /api/assessments/:id/submit
  Description: Submit assessment
  Auth: Bearer token (Owner only)
  Body:
    files: SubmissionFile[]
    notes?: string
  Response:
    assessmentId: string
    status: "submitted"
    submittedAt: string

GET /api/assessments/:id
  Description: Get assessment with score
  Auth: Bearer token (Owner or Task creator)
  Response: AssessmentWithScore

GET /api/assessments
  Description: List user's assessments
  Auth: Bearer token
  Query:
    status?: AssessmentStatus
    limit?: number
    offset?: number
  Response:
    assessments: Assessment[]
    total: number
```

### AI Proxy

```yaml
POST /api/ai/chat
  Description: Send AI chat request
  Auth: Bearer token
  Body:
    assessmentId?: string
    model: string
    messages: ChatMessage[]
    systemPrompt?: string
    maxTokens?: number
  Response:
    content: string
    model: string
    usage:
      inputTokens: number
      outputTokens: number
      totalTokens: number

POST /api/ai/chat/stream
  Description: Stream AI chat response
  Auth: Bearer token
  Body: Same as /api/ai/chat
  Response: Server-Sent Events stream

GET /api/ai/models
  Description: List available AI models
  Auth: Bearer token
  Response:
    models: ModelInfo[]
```

### Invitations (Business)

```yaml
POST /api/invitations
  Description: Create and send invitation
  Auth: Bearer token (Business only)
  Body:
    taskId: string
    recipientEmail: string
    recipientName?: string
    message?: string
    expiresAt?: string (ISO)
  Response:
    invitationId: string
    accessLink: string
    status: "sent"

GET /api/invitations
  Description: List sent invitations
  Auth: Bearer token (Business only)
  Query:
    taskId?: string
    status?: InvitationStatus
  Response:
    invitations: Invitation[]

GET /api/invitations/:id
  Description: Get invitation details
  Auth: Bearer token or public access link
  Response: Invitation with task info

POST /api/invitations/:id/accept
  Description: Accept invitation
  Auth: Bearer token
  Response:
    assessmentId: string
    redirectUrl: string

DELETE /api/invitations/:id
  Description: Cancel invitation
  Auth: Bearer token (Sender only)
  Response: 204 No Content
```

### Business Reports

```yaml
GET /api/business/candidates
  Description: List all candidates
  Auth: Bearer token (Business only)
  Query:
    taskId?: string
    status?: string
    sortBy?: "score" | "date" | "name"
    order?: "asc" | "desc"
  Response:
    candidates: CandidateInfo[]

GET /api/business/candidates/compare
  Description: Compare multiple candidates
  Auth: Bearer token (Business only)
  Query:
    ids: string[] (comma-separated assessment IDs)
  Response:
    candidates: CandidateComparison[]
    ranking: string[] (ordered assessment IDs)

GET /api/business/reports/:assessmentId
  Description: Get detailed candidate report
  Auth: Bearer token (Business only)
  Response: DetailedReport

GET /api/business/reports/:assessmentId/export
  Description: Export report as PDF or CSV
  Auth: Bearer token (Business only)
  Query:
    format: "pdf" | "csv"
  Response: File download
```

---

# 10. Deployment & Infrastructure

## 10.1 Environment Variables

```bash
# =============================================================================
# FILE: .env.example
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
NODE_ENV=production
NEXT_PUBLIC_APP_URL=https://smartsuccess.ai
API_URL=https://api.smartsuccess.ai

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE (Supabase)
# ─────────────────────────────────────────────────────────────────────────────
DATABASE_URL=postgresql://user:password@db.xxx.supabase.co:5432/postgres
DIRECT_URL=postgresql://user:password@db.xxx.supabase.co:5432/postgres

# ─────────────────────────────────────────────────────────────────────────────
# REDIS (Upstash)
# ─────────────────────────────────────────────────────────────────────────────
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# ─────────────────────────────────────────────────────────────────────────────
# STORAGE (Cloudflare R2)
# ─────────────────────────────────────────────────────────────────────────────
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=ai-skills-lab
R2_PUBLIC_URL=https://files.smartsuccess.ai

# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION (Clerk)
# ─────────────────────────────────────────────────────────────────────────────
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_xxx
CLERK_SECRET_KEY=sk_xxx
CLERK_WEBHOOK_SECRET=whsec_xxx

# ─────────────────────────────────────────────────────────────────────────────
# AI PROVIDERS
# ─────────────────────────────────────────────────────────────────────────────
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL (Resend)
# ─────────────────────────────────────────────────────────────────────────────
RESEND_API_KEY=re_xxx

# ─────────────────────────────────────────────────────────────────────────────
# SANDBOX (Fly.io)
# ─────────────────────────────────────────────────────────────────────────────
FLY_API_TOKEN=xxx
FLY_APP_NAME=ai-skills-lab-sandbox

# ─────────────────────────────────────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────────────────────────────────────
ENCRYPTION_KEY=base64_encoded_32_byte_key
```

## 10.2 Docker Configuration for Sandbox

```dockerfile
# =============================================================================
# FILE: sandbox/Dockerfile
# =============================================================================

FROM node:20-bookworm-slim

# Install Python and common tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash sandbox
WORKDIR /home/sandbox

# Install global npm packages
RUN npm install -g typescript ts-node nodemon

# Copy sandbox server
COPY --chown=sandbox:sandbox server/ ./server/
RUN cd server && npm install

# Switch to non-root user
USER sandbox

# Expose ports
EXPOSE 3000

# Start sandbox server
CMD ["node", "server/index.js"]
```

```javascript
// =============================================================================
// FILE: sandbox/server/index.js
// =============================================================================

const express = require('express');
const { Server } = require('socket.io');
const http = require('http');
const pty = require('node-pty');
const fs = require('fs').promises;
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: '*' }
});

const WORKSPACE_DIR = '/home/sandbox/workspace';
const ASSESSMENT_ID = process.env.ASSESSMENT_ID;
const TIME_LIMIT = parseInt(process.env.TIME_LIMIT_MINUTES || '120') * 60 * 1000;

// Initialize workspace
async function initWorkspace() {
  await fs.mkdir(WORKSPACE_DIR, { recursive: true });
  console.log(`Workspace initialized: ${WORKSPACE_DIR}`);
}

// File operations API
app.use(express.json());

app.get('/files', async (req, res) => {
  try {
    const files = await listFiles(WORKSPACE_DIR);
    res.json({ files });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/files/*', async (req, res) => {
  const filePath = path.join(WORKSPACE_DIR, req.params[0]);
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    res.json({ content });
  } catch (error) {
    res.status(404).json({ error: 'File not found' });
  }
});

app.put('/files/*', async (req, res) => {
  const filePath = path.join(WORKSPACE_DIR, req.params[0]);
  try {
    await fs.mkdir(path.dirname(filePath), { recursive: true });
    await fs.writeFile(filePath, req.body.content);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Terminal WebSocket
io.on('connection', (socket) => {
  console.log('Terminal connected');
  
  const shell = pty.spawn('bash', [], {
    name: 'xterm-color',
    cols: 80,
    rows: 24,
    cwd: WORKSPACE_DIR,
    env: process.env,
  });

  shell.on('data', (data) => {
    socket.emit('terminal:output', data);
  });

  socket.on('terminal:input', (data) => {
    shell.write(data);
  });

  socket.on('terminal:resize', ({ cols, rows }) => {
    shell.resize(cols, rows);
  });

  socket.on('disconnect', () => {
    shell.kill();
    console.log('Terminal disconnected');
  });
});

// Auto-shutdown after time limit
setTimeout(() => {
  console.log('Time limit reached, shutting down...');
  process.exit(0);
}, TIME_LIMIT);

// Start server
initWorkspace().then(() => {
  server.listen(3000, () => {
    console.log(`Sandbox server running on port 3000`);
    console.log(`Assessment: ${ASSESSMENT_ID}`);
    console.log(`Time limit: ${TIME_LIMIT / 60000} minutes`);
  });
});

// Helper: List files recursively
async function listFiles(dir, base = '') {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    const relativePath = path.join(base, entry.name);
    
    if (entry.isDirectory()) {
      files.push({
        name: entry.name,
        path: relativePath,
        type: 'folder',
        children: await listFiles(fullPath, relativePath),
      });
    } else {
      files.push({
        name: entry.name,
        path: relativePath,
        type: 'file',
      });
    }
  }
  
  return files;
}
```

## 10.3 GitHub Actions CI/CD

```yaml
# =============================================================================
# FILE: .github/workflows/deploy.yml
# =============================================================================

name: Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}

jobs:
  # ─────────────────────────────────────────────────────────────────────────
  # Test
  # ─────────────────────────────────────────────────────────────────────────
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install frontend dependencies
        run: |
          cd frontend
          pnpm install
      
      - name: Install backend dependencies
        run: |
          cd backend
          pip install poetry
          poetry install
      
      - name: Run frontend tests
        run: |
          cd frontend
          pnpm test
      
      - name: Run backend tests
        run: |
          cd backend
          poetry run pytest

  # ─────────────────────────────────────────────────────────────────────────
  # Deploy Frontend (Vercel)
  # ─────────────────────────────────────────────────────────────────────────
  deploy-frontend:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          working-directory: frontend

  # ─────────────────────────────────────────────────────────────────────────
  # Deploy Backend (Render)
  # ─────────────────────────────────────────────────────────────────────────
  deploy-backend:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Render
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}

  # ─────────────────────────────────────────────────────────────────────────
  # Deploy Sandbox (Fly.io)
  # ─────────────────────────────────────────────────────────────────────────
  deploy-sandbox:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: superfly/flyctl-actions/setup-flyctl@master
      
      - name: Deploy sandbox image
        run: |
          cd sandbox
          flyctl deploy --remote-only
```

---

# 11. Testing Strategy

## 11.1 Testing Pyramid

```
                    ┌─────────────┐
                    │    E2E      │  5%
                    │  (Playwright)│
                   ┌┴─────────────┴┐
                   │  Integration  │  25%
                   │   (API tests) │
                  ┌┴───────────────┴┐
                  │     Unit        │  70%
                  │  (Jest/Pytest)  │
                  └─────────────────┘
```

## 11.2 Test Examples

```python
# =============================================================================
# FILE: backend/tests/test_scoring.py
# =============================================================================

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.scoring.pipeline import ScoringPipeline, ProcessedData
from app.scoring.evaluators.prompt_engineering import PromptEngineeringEvaluator

@pytest.fixture
def mock_processed_data():
    return ProcessedData(
        assessment_id=str(uuid4()),
        task={
            'id': str(uuid4()),
            'title': 'Test Task',
            'description': 'Test description',
            'task_type': 'code_generation',
            'difficulty': 'intermediate',
        },
        tracking_data={
            'events': [
                {'type': 'ai_prompt', 'data': {'prompt': 'Write a function', 'model': 'claude'}, 'timestamp': '2026-01-01T10:00:00'},
                {'type': 'ai_response', 'data': {'response_length': 500}, 'timestamp': '2026-01-01T10:00:05'},
            ]
        },
        submission={
            'files': [{'fileName': 'main.py', 'content': 'def hello(): pass'}],
            'notes': '',
            'time_spent': 3600,
        },
        eval_config={
            'category_weights': {'planning': 25, 'prompt_engineering': 25, 'tool_orchestration': 25, 'outcome_quality': 25},
            'subitem_weights': {...},
            'level_thresholds': {...},
        },
        ai_interactions=[...],
        code_snapshots=[],
        time_metrics={'total_time': 3600},
        models_used=['claude'],
    )

class TestScoringPipeline:
    
    @pytest.mark.asyncio
    async def test_score_calculation(self, mock_processed_data):
        """Test that scores are calculated correctly."""
        
        pipeline = ScoringPipeline(
            db=AsyncMock(),
            storage=AsyncMock(),
            ai_service=AsyncMock(),
        )
        
        # Mock evaluator results
        category_results = {
            'planning': {'subitems': {'task_breakdown': 80, 'time_estimation': 70}, 'error': False},
            'prompt_engineering': {'subitems': {'clarity_specificity': 85}, 'error': False},
            'tool_orchestration': {'subitems': {'tool_selection': 75}, 'error': False},
            'outcome_quality': {'subitems': {'correctness': 90}, 'error': False},
        }
        
        score_result = pipeline._calculate_scores(
            category_results,
            mock_processed_data.eval_config,
        )
        
        assert 0 <= score_result['final_score'] <= 100
        assert score_result['level'] in ('operator', 'architect', 'innovator')
        assert 'category_scores' in score_result

    @pytest.mark.asyncio
    async def test_level_determination(self):
        """Test proficiency level is determined correctly."""
        
        test_cases = [
            (45, 'operator'),
            (65, 'architect'),
            (90, 'innovator'),
        ]
        
        for score, expected_level in test_cases:
            # ... test implementation

class TestPromptEngineeringEvaluator:
    
    @pytest.mark.asyncio
    async def test_evaluate_with_prompts(self):
        """Test evaluation with actual prompts."""
        
        ai_service = AsyncMock()
        ai_service.chat.return_value = AsyncMock(
            content='{"subitems": {"clarity_specificity": 8}, "reasoning": "Good", "strengths": [], "improvements": []}'
        )
        
        evaluator = PromptEngineeringEvaluator(ai_service)
        
        # ... test implementation
```

---

# 12. Implementation Checklist

## Phase 1: Foundation (Weeks 1-4)

### Week 1: Project Setup & Auth
- [ ] Initialize Next.js project with TypeScript
- [ ] Set up Tailwind CSS and shadcn/ui
- [ ] Initialize FastAPI backend project
- [ ] Set up PostgreSQL database with Supabase
- [ ] Create database schema and run migrations
- [ ] Integrate Clerk authentication
- [ ] Build custom sign-up flow (user type selection)
- [ ] Create user sync webhook
- [ ] Test authentication end-to-end

### Week 2: Task Management
- [ ] Create Task model and API endpoints
- [ ] Build task listing page
- [ ] Build task detail page
- [ ] Implement task creation form (Business users)
- [ ] Set up Cloudflare R2 for file storage
- [ ] Implement file upload for task attachments
- [ ] Create evaluation config schema
- [ ] Seed default tasks database

### Week 3: Basic Workspace
- [ ] Set up Monaco Editor component
- [ ] Create file explorer component
- [ ] Implement file CRUD operations
- [ ] Build basic AI chat panel
- [ ] Integrate Anthropic Claude API
- [ ] Integrate OpenAI API
- [ ] Implement model selector
- [ ] Create workspace context/state management

### Week 4: Assessment Flow
- [ ] Create Assessment model and endpoints
- [ ] Build assessment start flow
- [ ] Implement basic tracking (code changes)
- [ ] Create submission endpoint
- [ ] Build submission confirmation UI
- [ ] Set up Redis for temporary tracking storage
- [ ] Test complete assessment flow

## Phase 2: Workspace Enhancement (Weeks 5-8)

### Week 5: Multi-Model AI Chat
- [ ] Implement streaming responses
- [ ] Add message history with markdown rendering
- [ ] Create syntax highlighting for code blocks
- [ ] Add copy code button
- [ ] Implement model switching
- [ ] Add rate limiting for AI requests
- [ ] Create API key validation

### Week 6: File System & Terminal
- [ ] Enhance file explorer with folders
- [ ] Implement file creation/deletion
- [ ] Add file rename functionality
- [ ] Integrate Xterm.js terminal
- [ ] Set up WebSocket for terminal
- [ ] Create sandbox Docker image
- [ ] Deploy sandbox to Fly.io
- [ ] Test terminal commands

### Week 7: Tracking System
- [ ] Implement comprehensive event tracking
- [ ] Track AI prompt/response pairs
- [ ] Track code snapshots (debounced)
- [ ] Track file operations
- [ ] Track terminal commands
- [ ] Track model switches
- [ ] Implement tracking data aggregation
- [ ] Build tracking data upload to R2

### Week 8: Session Management
- [ ] Implement timer component
- [ ] Add deadline warnings
- [ ] Create auto-submit on timeout
- [ ] Build session recovery (reconnect)
- [ ] Implement sandbox cleanup
- [ ] Add session status indicators
- [ ] Test long-running sessions

## Phase 3: AI Scoring (Weeks 9-12)

### Week 9: Scoring Pipeline
- [ ] Create scoring service architecture
- [ ] Implement data preprocessing
- [ ] Build AI interaction extractor
- [ ] Create code evolution analyzer
- [ ] Implement time metrics calculator
- [ ] Set up async scoring job queue

### Week 10: Category Evaluators
- [ ] Implement Planning evaluator
- [ ] Implement Prompt Engineering evaluator
- [ ] Implement Tool Orchestration evaluator
- [ ] Implement Outcome Quality evaluator
- [ ] Create evaluation prompts
- [ ] Test evaluators with sample data

### Week 11: Score Calculation
- [ ] Implement weight application
- [ ] Create subitem score aggregation
- [ ] Build category score calculation
- [ ] Implement level determination
- [ ] Create score normalization
- [ ] Handle evaluation errors gracefully

### Week 12: Reports & Visualization
- [ ] Build results page
- [ ] Create score card component
- [ ] Implement category breakdown chart
- [ ] Build radar chart for categories
- [ ] Create strengths/improvements lists
- [ ] Implement AI highlights display
- [ ] Add share buttons

## Phase 4: Business Features (Weeks 13-16)

### Week 13: Custom Task Creation
- [ ] Build task creation wizard
- [ ] Implement file upload for task materials
- [ ] Create evaluation config editor
- [ ] Add weight customization UI
- [ ] Implement custom category addition
- [ ] Build task preview mode
- [ ] Add task duplication

### Week 14: Invitation System
- [ ] Create invitation model and endpoints
- [ ] Build invitation creation form
- [ ] Implement email sending (Resend)
- [ ] Create invitation landing page
- [ ] Implement invitation acceptance flow
- [ ] Add invitation expiration handling
- [ ] Build invitation management UI

### Week 15: Candidate Management
- [ ] Create business dashboard
- [ ] Build candidate list view
- [ ] Implement candidate filtering/sorting
- [ ] Create side-by-side comparison view
- [ ] Build detailed candidate report
- [ ] Add score ranking algorithm
- [ ] Implement candidate notes

### Week 16: Export & Analytics
- [ ] Implement PDF report generation
- [ ] Create CSV export
- [ ] Build analytics dashboard
- [ ] Add usage statistics
- [ ] Create billing integration hooks
- [ ] Implement subscription management

## Phase 5: Polish & Launch (Weeks 17-20)

### Week 17: Performance
- [ ] Optimize database queries
- [ ] Implement caching strategies
- [ ] Add lazy loading
- [ ] Optimize bundle size
- [ ] Set up CDN for static assets
- [ ] Profile and fix bottlenecks

### Week 18: Security
- [ ] Security audit
- [ ] Implement input sanitization
- [ ] Add rate limiting everywhere
- [ ] Set up WAF rules
- [ ] Implement audit logging
- [ ] Test sandbox isolation
- [ ] Penetration testing

### Week 19: Social & Integration
- [ ] Implement LinkedIn sharing
- [ ] Add Twitter/X sharing
- [ ] Create embeddable badge
- [ ] Build public profile page
- [ ] Add OpenGraph meta tags
- [ ] Create sitemap
- [ ] SEO optimization

### Week 20: Launch Prep
- [ ] End-to-end testing
- [ ] Load testing
- [ ] Create documentation
- [ ] Set up monitoring (Sentry)
- [ ] Configure alerts
- [ ] Prepare launch checklist
- [ ] Deploy to production
- [ ] Monitor launch metrics

---

**Document End**

*AI Skills Lab - Technical Design Plan v1.0*
*Ready for Implementation*
