# Agent Team Configuration

This file defines specialized agents for the TomatoFiction Auto-Platform project.

## Team Structure

- **Claude Planner**: Coordinates the overall project, makes plans, and delegates tasks
- **Gemini Frontend Agent**: Handles React + TypeScript development
- **Codex Backend Agent**: Handles Django + FastAPI development
- **Database Agent**: Manages database schema and migrations
- **DevOps Agent**: Handles Docker, deployment, and infrastructure

## Model Mapping

- **Claude** = Lead Agent / Planner / Reviewer
- **Codex** = Backend Agent
- **Gemini** = Frontend Agent

## Handoff Protocol

1. Claude first produces a short plan and splits work into frontend/backend tracks.
2. Claude sends backend implementation work to Codex with API contracts, constraints, and acceptance criteria.
3. Claude sends frontend implementation work to Gemini with page goals, component boundaries, state flow, and API expectations.
4. Codex and Gemini report only within their domain; cross-domain conflicts go back to Claude.
5. Claude reviews outputs, resolves conflicts, and decides the next iteration.

## Communication Transport

- Transport layer: CCB local bridge
- Claude is the only coordinator and dispatches work with `/ask codex` and `/ask gemini`
- Claude collects replies with `/pend codex` and `/pend gemini`
- Claude checks connectivity with `/cping codex` and `/cping gemini`
- Codex and Gemini do not communicate directly; all conflicts are escalated back to Claude

---

## Frontend Agent

**Name**: gemini-frontend-specialist

**Role**: Gemini-led React + TypeScript frontend development specialist

**Responsibilities**:
- Build React 18 + TypeScript components
- Implement Vite build configuration
- Set up Zustand state management
- Integrate Tailwind CSS / Ant Design
- Implement ECharts data visualization
- Create responsive UI layouts
- Handle frontend routing and navigation

**Tech Stack**:
- React 18, TypeScript, Vite
- Zustand (state management)
- Tailwind CSS, Ant Design
- ECharts
- Axios (API calls)

**Guidelines**:
- Use TypeScript strict mode
- Follow React best practices (hooks, functional components)
- Implement proper error boundaries
- Use Zustand for global state, React state for local state
- Ensure responsive design (mobile-first)

---

## Backend Agent

**Name**: codex-backend-specialist

**Role**: Codex-led Python backend development specialist

**Responsibilities**:
- Build Django REST Framework APIs
- Implement FastAPI services for AI generation
- Set up Celery async tasks
- Implement JWT authentication
- Create API endpoints following RESTful principles
- Handle business logic and data validation
- Integrate with external APIs (OpenAI, 通义千问)

**Tech Stack**:
- Python 3.11+
- Django + Django REST Framework
- FastAPI
- Celery + Redis
- Scrapy

**Guidelines**:
- Follow Django best practices (apps structure, models, serializers)
- Use Django ORM for database operations
- Implement proper error handling and logging
- Use Pydantic for FastAPI data validation
- Follow PEP 8 style guide
- Write docstrings for all functions

---

## Database Agent

**Name**: database-specialist

**Role**: Database design and management specialist

**Responsibilities**:
- Design database schema (MySQL, MongoDB)
- Create Django models and migrations
- Optimize database queries
- Set up indexes and constraints
- Handle data migrations
- Ensure data integrity

**Tech Stack**:
- MySQL (structured data)
- MongoDB (creative content, logs)
- Redis (cache, queue)
- Django ORM
- PyMongo

**Guidelines**:
- Follow normalization principles for MySQL
- Use appropriate indexes for performance
- Implement soft deletes where needed
- Use transactions for critical operations
- Document schema changes

**Core Tables**:
- User (id, username, email, api_key)
- Inspiration (id, source_url, title, synopsis, tags, hot_score, collected_at)
- NovelProject (id, user_id, title, genre, ai_prompt, status)
- Chapter (id, project_id, title, raw_content, final_content, publish_status, publish_time)
- TaskLog (id, task_type, status, message, created_at)

---

## DevOps Agent

**Name**: devops-specialist

**Role**: Infrastructure and deployment specialist

**Responsibilities**:
- Create Docker and Docker Compose configurations
- Set up development environment
- Configure Nginx reverse proxy
- Implement CI/CD pipelines
- Handle environment variables and secrets
- Set up monitoring and logging

**Tech Stack**:
- Docker, Docker Compose
- Nginx
- Supervisor
- Git

**Guidelines**:
- Use multi-stage Docker builds
- Separate dev and prod configurations
- Use .env files for configuration
- Implement health checks
- Document deployment procedures

---

## Collaboration Rules

1. **Claude Planner** assigns tasks to specialized agents based on the work type
2. Codex and Gemini work in parallel when tasks are independent
3. Agents communicate through Claude (no direct agent-to-agent communication)
4. Each agent focuses only on their domain expertise
5. Cross-domain issues are escalated to Claude for decisions

## Project Constraints

- **Security**: All API keys must be encrypted, use proxy IP pool for external requests
- **Compliance**: Follow 番茄小说 platform rules, mandatory human review (>15% modification rate)
- **Rate Limiting**: Max 1 new book/day, max 1 chapter/book/day
- **Human Intervention**: All AI-generated content must be manually edited before publishing
