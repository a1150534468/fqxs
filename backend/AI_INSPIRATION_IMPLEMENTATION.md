# AI Inspiration Generation & Project Creation

## Overview

This implementation adds AI-powered inspiration generation and automated novel project creation to the TomatoFiction platform.

## Features

### 1. FastAPI Inspiration Generation Endpoint

**Endpoint**: `POST /api/ai/generate/inspiration`

**Purpose**: Analyze trending books and generate innovative novel concepts using LLM.

**Request**:
```json
{
  "trending_books": [
    {
      "title": "都市修仙传",
      "synopsis": "现代都市中的修仙故事",
      "tags": ["都市", "修仙"],
      "hot_score": 95.5
    }
  ],
  "genre_preference": "都市"
}
```

**Response**:
```json
{
  "inspirations": [
    {
      "title": "都市之觉醒",
      "synopsis": "创新的都市修仙故事...",
      "genre": "都市",
      "selling_points": ["独特世界观", "快节奏"],
      "target_audience": "18-35岁男性读者",
      "estimated_popularity": 85.0
    }
  ],
  "analysis_summary": "市场分析总结..."
}
```

### 2. Django Inspiration APIs

#### Generate Inspiration from Trends

**Endpoint**: `POST /api/inspirations/generate-from-trends/`

**Authentication**: Required (JWT)

**Purpose**: Call FastAPI to generate inspirations and return results.

**Request**: Same as FastAPI endpoint

**Response**: Same as FastAPI endpoint

#### Start Project from Inspiration

**Endpoint**: `POST /api/inspirations/{id}/start-project/`

**Authentication**: Required (JWT)

**Purpose**: Complete workflow to create a novel project from an inspiration.

**Request**:
```json
{
  "title": "都市修仙传说",
  "genre": "都市",
  "target_chapters": 100,
  "first_chapter_title": "第一章：觉醒"
}
```

**Response**:
```json
{
  "project_id": 1,
  "title": "都市修仙传说",
  "genre": "都市",
  "outline": "【题材】都市\n【目标章节】100\n...",
  "first_chapter": {
    "id": 1,
    "title": "第一章：觉醒",
    "word_count": 2500,
    "status": "pending_review"
  }
}
```

**Workflow**:
1. Create NovelProject record
2. Call FastAPI to generate outline
3. Call FastAPI to generate first chapter
4. Save chapter with status `pending_review`
5. Mark inspiration as used
6. Return project details

### 3. Celery Tasks

#### generate_inspiration_from_trends

**Purpose**: Scheduled task to analyze trending books and generate new inspirations.

**Usage**:
```python
from celery_tasks.ai_tasks import generate_inspiration_from_trends

# Run immediately
generate_inspiration_from_trends.delay()

# Schedule with task record
task = Task.objects.create(task_type='generate_inspiration', status='pending')
generate_inspiration_from_trends.delay(task_record_id=task.id)
```

**Process**:
1. Fetch top 20 unused inspirations by hot_score
2. Call FastAPI to analyze and generate new concepts
3. Save generated inspirations to database
4. Update task record with results

#### start_novel_project_from_inspiration

**Purpose**: Automated project creation from inspiration.

**Usage**:
```python
from celery_tasks.ai_tasks import start_novel_project_from_inspiration

start_novel_project_from_inspiration.delay(
    user_id=1,
    inspiration_id=5,
    title="自定义标题",
    genre="都市",
    target_chapters=100
)
```

**Process**:
1. Create NovelProject
2. Generate outline via FastAPI
3. Generate first chapter via FastAPI
4. Save chapter with `pending_review` status
5. Update project metadata
6. Mark inspiration as used

## LLM Provider Configuration

The system uses the LLM Provider configuration from Django:

1. FastAPI receives JWT token in Authorization header
2. Extracts token and calls Django API to fetch provider config
3. Uses configured provider (OpenAI, Qwen, etc.) for generation
4. Falls back to default settings if provider fetch fails

**Provider Selection**:
- For inspiration: Uses `task_type='chapter'` provider
- For outline: Uses `task_type='outline'` provider
- For chapter: Uses `task_type='chapter'` provider

## Error Handling

All endpoints and tasks include:
- Comprehensive error logging
- Retry logic (Celery tasks: 2-3 retries)
- Detailed error messages in responses
- Transaction rollback on failure
- Task status tracking

## Testing

Run the test script:

```bash
cd /Users/z/code/fqxs/backend

# Make sure services are running:
# Terminal 1: python manage.py runserver
# Terminal 2: cd ../fastapi_service && uvicorn main:app --port 8001

# Run tests
source .venv/bin/activate
python test_inspiration_api.py
```

## Frontend Integration

The frontend can now:

1. **Generate Inspirations**:
   ```typescript
   const response = await fetch('/api/inspirations/generate-from-trends/', {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${token}`,
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({
       trending_books: [...],
       genre_preference: '都市'
     })
   });
   ```

2. **Start Project**:
   ```typescript
   const response = await fetch(`/api/inspirations/${inspirationId}/start-project/`, {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${token}`,
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({
       title: '自定义标题',
       genre: '都市',
       target_chapters: 100
     })
   });
   ```

3. **View Generated Chapter**:
   - Chapter is created with status `pending_review`
   - Frontend can fetch and display for manual editing
   - User must modify content before publishing (>15% change required)

## File Changes

### New Files
- `/Users/z/code/fqxs/fastapi_service/models/inspiration_schemas.py`
- `/Users/z/code/fqxs/backend/test_inspiration_api.py`

### Modified Files
- `/Users/z/code/fqxs/fastapi_service/services/llm_client.py`
- `/Users/z/code/fqxs/fastapi_service/routers/ai_generate.py`
- `/Users/z/code/fqxs/backend/apps/inspirations/serializers.py`
- `/Users/z/code/fqxs/backend/apps/inspirations/views.py`
- `/Users/z/code/fqxs/backend/apps/inspirations/urls.py`
- `/Users/z/code/fqxs/backend/celery_tasks/ai_tasks.py`

## Next Steps

1. Start both services (Django + FastAPI)
2. Run test script to verify functionality
3. Integrate with frontend UI
4. Set up scheduled Celery tasks for automated inspiration generation
5. Monitor generation quality and adjust prompts as needed
