# System Architecture

## Overview

`fqxs` is structured as a backend-first platform for AI-assisted long-form fiction operations. The current repository contains the initial Django application layer and the local infrastructure required to run it.

## Runtime Components

### 1. Django Application

Location:

- `backend/`

Responsibilities:

- Authentication and authorization
- Data model management
- REST API endpoints
- Management commands
- Future admin and workflow orchestration APIs

### 2. MySQL

Defined in:

- `docker-compose.yml`

Responsibilities:

- Persistent relational storage
- Users, LLM providers, inspirations, projects, chapters, tasks, and stats
- Django migration target database

### 3. Redis

Defined in:

- `docker-compose.yml`

Responsibilities:

- Future Celery broker/backend
- Cache and task coordination

## Application Modules

### `apps.users`

- Custom `User` model
- JWT login and refresh APIs
- Admin bootstrap command

### `apps.llm_providers`

- Provider configuration per user
- Task-specific LLM routing metadata

### `apps.inspirations`

- Ranking-derived creative inputs
- Hot score, tags, collection status

### `apps.novels`

- Novel project records
- Project state and update pacing
- Inspiration linkage

### `apps.chapters`

- Chapter generation lifecycle
- Review and publish timestamps
- LLM provider linkage

### `apps.tasks`

- Async task tracking
- Retry and result metadata

### `apps.stats`

- Daily metric snapshots

## Data Flow

### Authentication flow

1. Client submits username and password to `/api/users/login/`
2. Django validates credentials with Simple JWT
3. API returns `access` token, `refresh` token, and serialized user info
4. Client uses `/api/users/refresh/` to renew the access token

### Content workflow target design

1. Collect inspirations into `Inspiration`
2. Create `NovelProject`
3. Generate `Chapter` records using configured `LLMProvider`
4. Track async work in `Task`
5. Aggregate operational results in `Stats`

## Deployment Shape

Current local development topology:

- `mysql` container
- `redis` container
- `django` container

Planned extension points:

- FastAPI service for AI generation
- Celery worker and beat
- Scrapy collectors
- Reverse proxy and production process supervision

## Constraints

- Manual review remains mandatory for generated content
- Authentication is JWT-based
- API keys are modeled but encryption-at-rest logic is not yet implemented
- Rate limiting and platform risk-control policies are planned but not yet enforced in code
