# API Reference

## Base URL

Local development:

- `http://localhost:8000`

## Authentication

The backend uses JWT bearer tokens.

Send authenticated requests with:

```http
Authorization: Bearer <access_token>
```

## Endpoints

### `POST /api/users/login/`

Authenticate a user and return JWT tokens.

Request body:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

Successful response:

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "is_active": true,
    "is_staff": true
  }
}
```

### `POST /api/users/refresh/`

Refresh the access token using a valid refresh token.

Request body:

```json
{
  "refresh": "<refresh_token>"
}
```

Successful response:

```json
{
  "access": "<new_access_token>"
}
```

### `GET /api/users/me/stats/`

Return aggregate stats for the current user.

Successful response:

```json
{
  "project_count": 3,
  "chapter_count": 28,
  "total_word_count": 71620
}
```

### `GET /api/inspirations/`

List inspirations with DRF pagination.

Successful response:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "source_url": "https://example.com/rank/1",
      "title": "Hot Novel",
      "synopsis": "A popular story idea",
      "tags": ["urban", "system"],
      "hot_score": "95.50",
      "rank_type": "hot",
      "is_used": false,
      "collected_at": "2026-04-04T09:00:00+08:00",
      "created_at": "2026-04-04T09:00:00+08:00",
      "updated_at": "2026-04-04T09:00:00+08:00"
    }
  ]
}
```

### `POST /api/inspirations/`

Create an inspiration record.

Request body:

```json
{
  "source_url": "https://example.com/rank/2",
  "title": "New Inspiration",
  "synopsis": "A new story idea",
  "tags": ["fantasy", "system"],
  "hot_score": "88.80",
  "rank_type": "new"
}
```

### `GET /api/inspirations/<id>/`

Retrieve a single inspiration.

### `PATCH /api/inspirations/<id>/`

Update part of an inspiration record.

Request body:

```json
{
  "title": "Updated Inspiration",
  "is_used": true
}
```

### `DELETE /api/inspirations/<id>/`

Delete an inspiration record.

### `POST /api/inspirations/bulk-mark-used/`

Bulk update `is_used` for multiple inspiration IDs.

Request body:

```json
{
  "ids": [1, 2, 3],
  "is_used": true
}
```

Successful response:

```json
{
  "requested_count": 3,
  "updated_count": 2,
  "is_used": true,
  "missing_ids": [3]
}
```

### `GET /api/novels/`

List current user's novel projects (soft-deleted records are excluded).

Supported query parameters:

- `status`: filter by one or more statuses (comma-separated), e.g. `active,paused`
- `type`: filter by project type (mapped to `genre`)
- `genre`: same as `type`
- `search`: keyword search on `title`, `genre`, `synopsis`, `outline`
- `created_after` / `created_before`: ISO 8601 datetime or `YYYY-MM-DD`
- `created_from` / `created_to`: aliases for `created_after` / `created_before`

Example:

```http
GET /api/novels/?status=paused,completed&type=Fantasy&search=kingdom&created_after=2026-04-01
```

Successful response:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 2,
      "user": 1,
      "inspiration": 7,
      "title": "Kingdom Reborn",
      "genre": "Fantasy",
      "synopsis": "...",
      "outline": "...",
      "ai_prompt_template": "...",
      "status": "paused",
      "target_chapters": 100,
      "current_chapter": 18,
      "update_frequency": 1,
      "last_update_at": null,
      "tomato_book_id": null,
      "created_at": "2026-04-03T12:15:00+08:00",
      "updated_at": "2026-04-04T09:20:00+08:00",
      "is_deleted": false
    }
  ]
}
```

### `POST /api/novels/`

Create a novel project for the authenticated user.

Request body:

```json
{
  "inspiration": 7,
  "title": "Urban Legend",
  "genre": "Urban",
  "synopsis": "A modern cultivation story",
  "outline": "Chapter plan",
  "ai_prompt_template": "Write chapter {chapter_number}",
  "status": "active",
  "target_chapters": 120,
  "current_chapter": 0,
  "update_frequency": 1,
  "tomato_book_id": null
}
```

### `GET /api/novels/<id>/`

Retrieve a single project owned by the authenticated user.

### `PATCH /api/novels/<id>/`

Partially update a project owned by the authenticated user.

### `DELETE /api/novels/<id>/`

Soft-delete a project (`is_deleted=true`).

### `GET /api/chapters/`

List chapters owned by the authenticated user (soft-deleted records are excluded).

Supported query parameters:

- `project_id`: filter by project ID
- `publish_status`: filter by one or more statuses (`draft,published,failed`)
- `search`: title keyword search (alias: `title`)
- `created_after` / `created_before`: ISO 8601 datetime or `YYYY-MM-DD`
- `created_from` / `created_to`: aliases for `created_after` / `created_before`

Example:

```http
GET /api/chapters/?project_id=12&publish_status=published&search=intro&created_after=2026-04-01
```

Successful response:

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 31,
      "project": 12,
      "chapter_number": 3,
      "title": "Intro Arc",
      "raw_content": "...",
      "final_content": "...",
      "word_count": 2618,
      "generation_prompt": "...",
      "llm_provider": null,
      "status": "published",
      "publish_status": "published",
      "generated_at": null,
      "reviewed_at": null,
      "published_at": "2026-04-04T11:00:00+08:00",
      "tomato_chapter_id": null,
      "read_count": 0,
      "created_at": "2026-04-04T10:30:00+08:00",
      "updated_at": "2026-04-04T11:00:00+08:00",
      "is_deleted": false
    }
  ]
}
```

### `POST /api/chapters/`

Create a chapter in one of the current user's projects.

Request body:

```json
{
  "project_id": 12,
  "chapter_number": 4,
  "title": "Conflict",
  "raw_content": "AI draft",
  "final_content": "Editor revised content",
  "generation_prompt": "continue chapter 3",
  "publish_status": "draft"
}
```

Notes:

- `project_id` is required.
- `word_count` is automatically calculated from `final_content`.
- `publish_status` is mapped internally to chapter `status`.

### `GET /api/chapters/<id>/`

Retrieve one chapter owned by the authenticated user.

### `PATCH /api/chapters/<id>/`

Update chapter fields. If `final_content` changes, `word_count` is recalculated automatically.

### `DELETE /api/chapters/<id>/`

Soft-delete a chapter (`is_deleted=true`).

### `POST /api/chapters/generate-async/`

Trigger asynchronous chapter generation with Celery.

Request body:

```json
{
  "project_id": 12,
  "chapter_number": 5,
  "chapter_title": "Night Raid"
}
```

Successful response (`202 Accepted`):

```json
{
  "task_id": "f4b92285-71dd-47c5-b74d-8593f0b9e9eb",
  "task_record_id": 18,
  "status": "pending"
}
```

Notes:

- `project_id` must belong to the authenticated user.
- The worker will call FastAPI (`/api/ai/generate/chapter`) and create/update the chapter record.

### `GET /api/tasks/<task_id>/status/`

Query Celery task runtime status and linked backend task metadata.

Successful response:

```json
{
  "task_id": "f4b92285-71dd-47c5-b74d-8593f0b9e9eb",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "chapter_id": 33,
    "created": true
  },
  "task_record": {
    "id": 18,
    "task_type": "generate_chapter",
    "status": "success",
    "retry_count": 0,
    "error_message": "",
    "created_at": "2026-04-05T00:42:10.317298+08:00",
    "updated_at": "2026-04-05T00:42:14.018773+08:00"
  }
}
```

Notes:

- Requires JWT authentication.
- `result` is `null` while the Celery task is not ready yet.

## Celery Runtime

Start worker:

```bash
celery -A config worker -l info
```

Start beat scheduler:

```bash
celery -A config beat -l info
```

Start monitoring dashboard:

```bash
celery -A config flower --port=5555
```

## Error Behavior

Current auth endpoints follow DRF + Simple JWT defaults:

- `200 OK` on success
- `401 Unauthorized` for invalid credentials or invalid refresh tokens
- `400 Bad Request` for malformed request payloads

Current inspirations and novels endpoints follow DRF defaults:

- `200 OK` for list, retrieve, update, and custom bulk actions
- `201 Created` for create
- `204 No Content` for delete
- `400 Bad Request` for validation errors (for example invalid `created_after` format)
- `401 Unauthorized` for missing or invalid JWT
- `404 Not Found` for missing IDs or resources outside user scope

Chapter endpoints add the following validation behavior:

- `400 Bad Request` when `project_id` is missing or not owned by the current user
- `400 Bad Request` for unsupported `publish_status` values
- `400 Bad Request` when `chapter_number <= 0`
