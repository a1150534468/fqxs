# fqxs

TomatoFiction Auto-Platform backend workspace for automated inspiration collection, novel project management, chapter generation workflow, task tracking, and JWT-authenticated administration.

## Project Overview

This repository currently contains the backend foundation for the `fqxs` project:

- Django 4.2 backend service
- MySQL 8 and Redis 7 local development environment via Docker Compose
- Custom user model and JWT authentication
- Core data models for providers, inspirations, novels, chapters, tasks, and stats
- Initial management command for bootstrapping the admin account

## Tech Stack

- Python 3.11
- Django 4.2
- Django REST Framework
- Simple JWT
- MySQL 8
- Redis 7
- Pytest + pytest-django
- Docker Compose

## Quick Start

### 1. Prepare environment variables

```bash
cp .env.example .env
```

### 2. Start infrastructure

```bash
docker compose up -d mysql redis
```

### 3. Start Django service

```bash
docker compose up -d django
```

### 4. Run migrations

```bash
cd backend
.venv/bin/python manage.py migrate
```

### 5. Create the initial admin account

```bash
cd backend
.venv/bin/python manage.py create_admin
```

### 6. Run the backend locally

```bash
cd backend
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

The Django API is exposed at `http://localhost:8000`.

## Development Guide

### Backend setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Run tests

```bash
cd backend
.venv/bin/python -m pytest -v
```

### Generate migrations

```bash
cd backend
.venv/bin/python manage.py makemigrations
.venv/bin/python manage.py migrate
```

### Useful paths

- Django settings: `backend/config/settings.py`
- Project URLs: `backend/config/urls.py`
- App models: `backend/apps/*/models.py`
- App tests: `backend/apps/*/tests.py`

## API Documentation

- Architecture: [docs/architecture.md](/Users/z/code/fqxs/docs/architecture.md)
- API reference: [docs/api.md](/Users/z/code/fqxs/docs/api.md)
- Management commands: [docs/backend-commands.md](/Users/z/code/fqxs/docs/backend-commands.md)

## Current Status

Implemented backend capabilities:

- Custom `User` model
- JWT login and refresh endpoints
- Data models for:
  - `LLMProvider`
  - `Inspiration`
  - `NovelProject`
  - `Chapter`
  - `Task`
  - `Stats`
- Initial Django migrations
- Admin bootstrap management command

Not yet implemented:

- Business CRUD APIs beyond auth
- Celery workers and scheduled jobs
- FastAPI AI service
- Scrapy spiders
- Frontend application
