# Full Workflow Automated Test

## Overview

This test suite validates the complete TomatoFiction platform workflow from inspiration generation to chapter publishing.

## Test Coverage

### 1. Inspiration Generation Tests
- Create sample trending book inspirations
- Generate AI inspirations from trending books
- List and retrieve inspirations
- Verify inspiration data in database

### 2. Project Startup Tests
- Start a complete project from an inspiration
- Generate project outline via AI
- Create first chapter automatically
- Verify project and chapter creation in database
- Check chapter status (should be `pending_review`)

### 3. Automatic Chapter Generation Tests
- Trigger async chapter generation via Celery
- Check task status via API
- Verify chapter generation completion
- Validate chapter content and status

### 4. Chapter Editing Tests
- Retrieve chapter details via API
- Edit chapter content (simulate manual review)
- Update chapter status to `approved`
- Verify changes persisted correctly

### 5. Publishing Tests (Simulated)
- Publish approved chapters
- Update publishing status
- Verify publish timestamp and tomato chapter ID
- Check status transitions

### 6. Task Monitoring Tests
- List all tasks
- Filter tasks by status
- Filter tasks by type
- Verify task records and pagination

### 7. Additional API Tests
- List projects with filters
- List chapters with filters
- Get user statistics (project count, chapter count, word count)

## Prerequisites

1. **Backend Services Running**:
   ```bash
   # Django backend
   cd /Users/z/code/fqxs/backend
   python manage.py runserver
   
   # FastAPI service
   cd /Users/z/code/fqxs/fastapi_service
   uvicorn main:app --host 0.0.0.0 --port 8001
   
   # Celery worker (optional for async tests)
   cd /Users/z/code/fqxs/backend
   celery -A config worker -l info
   ```

2. **Database Setup**:
   ```bash
   cd /Users/z/code/fqxs/backend
   python manage.py migrate
   python manage.py create_admin  # Create initial admin user
   ```

3. **Environment Variables**:
   - Ensure `.env` file is configured correctly
   - Set `FASTAPI_MOCK_GENERATION=True` for testing without real LLM API calls

## Running Tests

### Run All Tests

```bash
cd /Users/z/code/fqxs/backend
python test_full_workflow.py
```

### Run with Custom URLs

```bash
python test_full_workflow.py --base-url http://localhost:8000 --fastapi-url http://localhost:8001
```

### Run with Docker

```bash
# If using Docker Compose
docker-compose up -d
python test_full_workflow.py --base-url http://localhost:8000 --fastapi-url http://localhost:8001
```

## Test Output

### Console Output

The test script provides real-time console output with:
- Timestamp for each test
- Pass/Fail status with ✓/✗ indicators
- Detailed error messages for failures
- Summary statistics at the end

Example:
```
[2026-04-08 12:00:00] [INFO] Starting Full Workflow Test Suite
[2026-04-08 12:00:01] [PASS] ✓ PASS: User Login - Successfully logged in and obtained JWT token
[2026-04-08 12:00:02] [PASS] ✓ PASS: Create Sample Inspirations - Created 3 new inspirations
...
```

### JSON Report

A detailed JSON report is saved to `test_report_YYYYMMDD_HHMMSS.json` with:
- Test execution timestamp
- Summary statistics (total, passed, failed, pass rate)
- Detailed results for each test including:
  - Test name
  - Pass/fail status
  - Message
  - Additional details (IDs, counts, etc.)
  - Execution timestamp

Example report structure:
```json
{
  "timestamp": "2026-04-08T12:00:00",
  "summary": {
    "total": 20,
    "passed": 18,
    "failed": 2,
    "pass_rate": "90.0%"
  },
  "results": [
    {
      "name": "User Login",
      "passed": true,
      "message": "Successfully logged in",
      "details": {"token_length": 200},
      "timestamp": "2026-04-08T12:00:01"
    }
  ]
}
```

## Verification Points

The test suite validates:

1. **API Response Codes**: All endpoints return correct HTTP status codes
2. **Database State**: Data is correctly persisted and retrievable
3. **Status Transitions**: Chapters move through correct status flow (generating → pending_review → approved → published)
4. **Data Integrity**: Generated content has proper structure and required fields
5. **Error Handling**: Failed operations return appropriate error messages
6. **Task Tracking**: Async tasks are properly recorded and trackable

## Common Issues

### Connection Refused
- Ensure Django backend is running on port 8000
- Ensure FastAPI service is running on port 8001

### Authentication Errors
- Test user is created automatically
- If issues persist, manually create user: `python manage.py createsuperuser`

### Task Timeout
- Celery worker may not be running (async tests will fail)
- Or set `FASTAPI_MOCK_GENERATION=True` for faster mock responses

### Database Errors
- Run migrations: `python manage.py migrate`
- Check database connection in `.env`

## Cleanup

To clean up test data:

```bash
cd /Users/z/code/fqxs/backend
python manage.py shell

# In Django shell:
from django.contrib.auth import get_user_model
from apps.inspirations.models import Inspiration
from apps.novels.models import NovelProject
from apps.chapters.models import Chapter
from apps.tasks.models import Task

User = get_user_model()
test_user = User.objects.filter(username='test_workflow_user').first()
if test_user:
    NovelProject.objects.filter(user=test_user).delete()
    test_user.delete()

# Clean up test inspirations
Inspiration.objects.filter(title__contains='测试').delete()
```

## Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed

## Integration with CI/CD

This test script can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Full Workflow Tests
  run: |
    cd backend
    python test_full_workflow.py
  env:
    FASTAPI_MOCK_GENERATION: true
```

## Notes

- Tests are designed to be idempotent (can run multiple times)
- Test user is created/reused automatically
- Mock mode is recommended for CI/CD to avoid LLM API costs
- Some tests may take 30+ seconds due to async task waiting
