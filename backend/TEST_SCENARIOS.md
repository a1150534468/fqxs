# Test Scenarios Quick Reference

## Test Execution Flow

```
1. Setup & Authentication
   └─> Create/Get test user
   └─> Login and obtain JWT token

2. Inspiration Generation
   └─> Create sample trending books
   └─> Generate AI inspirations from trends
   └─> List and verify inspirations

3. Project Startup
   └─> Select inspiration
   └─> Start project (creates project + outline + first chapter)
   └─> Verify database records

4. Chapter Generation
   └─> Trigger async generation for chapter 2
   └─> Check task status
   └─> Wait for completion
   └─> Verify chapter created with status=pending_review

5. Chapter Editing
   └─> Retrieve chapter details
   └─> Modify content (simulate manual review)
   └─> Update status to approved

6. Publishing
   └─> Publish approved chapter
   └─> Update status to published
   └─> Verify publish timestamp and tomato_chapter_id

7. Task Monitoring
   └─> List all tasks
   └─> Filter by status
   └─> Filter by type

8. Additional Validations
   └─> List projects
   └─> List chapters
   └─> Get user statistics
```

## API Endpoints Tested

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/users/login/` | POST | JWT authentication |
| `/api/users/stats/` | GET | User statistics |
| `/api/inspirations/` | GET | List inspirations |
| `/api/inspirations/` | POST | Create inspiration |
| `/api/inspirations/generate-from-trends/` | POST | AI generation |
| `/api/inspirations/{id}/start-project/` | POST | Start project |
| `/api/novels/` | GET | List projects |
| `/api/chapters/` | GET | List chapters |
| `/api/chapters/{id}/` | GET | Get chapter detail |
| `/api/chapters/{id}/` | PATCH | Update chapter |
| `/api/chapters/generate-async/` | POST | Async generation |
| `/api/tasks/` | GET | List tasks |
| `/api/tasks/{id}/status/` | GET | Task status |

## Expected Status Transitions

### Chapter Lifecycle
```
generating → pending_review → approved → published
                    ↓
                  failed
```

### Task Lifecycle
```
pending → running → success
              ↓
            failed → retry
```

### Project Status
```
active → paused → completed
    ↓
 abandoned
```

## Test Data

### Sample Inspirations
- 都市修仙传 (Urban Cultivation)
- 重生之商业帝国 (Rebirth Business Empire)
- 星际争霸之虫族崛起 (StarCraft Zerg Rise)

### Test User
- Username: `test_workflow_user`
- Password: `test_password_123`
- Email: `test_workflow@example.com`

### Test Project
- Title: 测试小说项目
- Genre: 都市
- Target Chapters: 50
- First Chapter: 第一章：觉醒

## Validation Checks

### Project Creation
- [x] Project record exists in database
- [x] Project status is 'active'
- [x] Outline is generated and not empty
- [x] Current chapter is set to 1
- [x] First chapter exists
- [x] First chapter status is 'pending_review'
- [x] First chapter has content

### Chapter Generation
- [x] Task record created
- [x] Celery task ID assigned
- [x] Chapter record created
- [x] Chapter has raw_content
- [x] Word count calculated
- [x] Status transitions correctly

### Publishing
- [x] Chapter status is 'published'
- [x] published_at timestamp set
- [x] tomato_chapter_id assigned
- [x] Chapter retrievable via API

### Task Monitoring
- [x] Tasks listed correctly
- [x] Filtering by status works
- [x] Filtering by type works
- [x] Pagination works
- [x] Task details accessible

## Performance Expectations

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Login | < 1s | JWT generation |
| List API | < 1s | With pagination |
| Start Project | 10-30s | Includes AI generation |
| Generate Chapter | 10-30s | Async via Celery |
| Edit Chapter | < 1s | Database update |
| Publish Chapter | < 1s | Status update |

## Mock vs Real Mode

### Mock Mode (FASTAPI_MOCK_GENERATION=True)
- Fast execution (< 1s per generation)
- No LLM API costs
- Predictable content
- Ideal for CI/CD

### Real Mode (FASTAPI_MOCK_GENERATION=False)
- Slower execution (10-30s per generation)
- Requires valid LLM API key
- Real AI-generated content
- Better for integration testing

## Troubleshooting

### Test Fails: "Connection refused"
**Cause**: Backend service not running
**Fix**: Start Django/FastAPI services

### Test Fails: "Authentication failed"
**Cause**: Test user doesn't exist or password mismatch
**Fix**: Delete test user and let script recreate it

### Test Fails: "Task timeout"
**Cause**: Celery worker not running or task stuck
**Fix**: Start Celery worker or check task queue

### Test Fails: "Chapter not generated"
**Cause**: FastAPI service error or mock mode disabled
**Fix**: Check FastAPI logs, ensure mock mode enabled

### Test Fails: "Database error"
**Cause**: Migrations not applied
**Fix**: Run `python manage.py migrate`

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Workflow Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: rootpassword
          MYSQL_DATABASE: fqxs
        ports:
          - 3306:3306
      
      redis:
        image: redis:7
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r fastapi_service/requirements.txt
      
      - name: Run migrations
        run: |
          cd backend
          python manage.py migrate
      
      - name: Start services
        run: |
          cd backend
          python manage.py runserver &
          cd ../fastapi_service
          uvicorn main:app --port 8001 &
          sleep 5
      
      - name: Run tests
        run: |
          cd backend
          python test_full_workflow.py
        env:
          FASTAPI_MOCK_GENERATION: true
```

## Manual Testing Checklist

- [ ] All services running (Django, FastAPI, Celery)
- [ ] Database migrated
- [ ] Environment variables configured
- [ ] Test user can login
- [ ] Inspirations can be created
- [ ] Projects can be started
- [ ] Chapters can be generated
- [ ] Chapters can be edited
- [ ] Chapters can be published
- [ ] Tasks are tracked correctly
- [ ] All APIs return correct status codes
- [ ] Database state is consistent
- [ ] No errors in service logs
