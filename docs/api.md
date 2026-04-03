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

## Available Endpoints

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

## Planned API Surface

The following domains are modeled in the database but do not yet expose CRUD APIs in this repository:

- Users
- LLM providers
- Inspirations
- Novel projects
- Chapters
- Tasks
- Stats

## Error Behavior

Current auth endpoints follow DRF + Simple JWT defaults:

- `200 OK` on success
- `401 Unauthorized` for invalid credentials or invalid refresh tokens
- `400 Bad Request` for malformed request payloads
