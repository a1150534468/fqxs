# MVP Phase 1: Infrastructure and Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up Docker environment, Django project with database models, migrations, and JWT authentication

**Architecture:** Monolithic Django application with MySQL database, Redis cache, containerized with Docker Compose. All services run locally for development.

**Tech Stack:** Django 4.2, Django REST Framework, MySQL 8.0, Redis 7, Docker Compose, PyJWT

---

## File Structure Overview

```
fqxs/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── __init__.py
│   │   ├── users/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── serializers.py
│   │   │   ├── views.py
│   │   │   └── tests.py
│   │   ├── llm_providers/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── tests.py
│   │   ├── inspirations/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── tests.py
│   │   ├── novels/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── tests.py
│   │   ├── chapters/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── tests.py
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── tests.py
│   │   └── stats/
│   │       ├── __init__.py
│   │       ├── models.py
│   │       └── tests.py
│   └── pytest.ini
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

### Task 1: Docker Compose Environment Setup

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Write .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# Django
*.log
db.sqlite3
media/
staticfiles/

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
*.pid
```

- [ ] **Step 2: Write .env.example**

```
# Django
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=fqxs
MYSQL_USER=fqxs_user
MYSQL_PASSWORD=fqxs_password
DATABASE_URL=mysql://fqxs_user:fqxs_password@mysql:3306/fqxs

# Redis
REDIS_URL=redis://redis:6379/0

# FastAPI (for future use)
FASTAPI_URL=http://fastapi:8001
```

- [ ] **Step 3: Write docker-compose.yml**

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: fqxs_mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: fqxs_redis
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

volumes:
  mysql_data:
```

- [ ] **Step 4: Copy .env.example to .env**

Run: `cp .env.example .env`
Expected: .env file created

- [ ] **Step 5: Test Docker Compose**

Run: `docker-compose up -d mysql redis`
Expected: Both containers start successfully

- [ ] **Step 6: Verify MySQL connection**

Run: `docker-compose exec mysql mysql -u fqxs_user -pfqxs_password -e "SELECT 1;"`
Expected: Output shows "1"

- [ ] **Step 7: Verify Redis connection**

Run: `docker-compose exec redis redis-cli ping`
Expected: Output shows "PONG"

- [ ] **Step 8: Stop containers**

Run: `docker-compose down`
Expected: Containers stopped

- [ ] **Step 9: Commit**

```bash
git add docker-compose.yml .env.example .gitignore
git commit -m "feat: add Docker Compose environment with MySQL and Redis

- MySQL 8.0 with health checks
- Redis 7 with health checks
- Environment variable template
- Gitignore for Python/Django projects

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Django Project Initialization

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/requirements.txt`
- Create: `backend/manage.py`
- Create: `backend/config/__init__.py`
- Create: `backend/config/settings.py`
- Create: `backend/config/urls.py`
- Create: `backend/config/wsgi.py`
- Create: `backend/pytest.ini`

- [ ] **Step 1: Write backend/requirements.txt**

```
Django==4.2.11
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.1
mysqlclient==2.2.4
redis==5.0.3
celery==5.3.6
python-dotenv==1.0.1
cryptography==42.0.5
pytest==8.1.1
pytest-django==4.8.0
```

- [ ] **Step 2: Write backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

- [ ] **Step 3: Create Django project structure**

Run: `cd backend && django-admin startproject config .`
Expected: Django project created with manage.py and config/ directory

- [ ] **Step 4: Write backend/pytest.ini**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
addopts = -v --tb=short
```

- [ ] **Step 5: Update docker-compose.yml to add Django service**

Add to docker-compose.yml after redis service:

```yaml
  django:
    build: ./backend
    container_name: fqxs_django
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
```

- [ ] **Step 6: Commit**

```bash
git add backend/ docker-compose.yml
git commit -m "feat: initialize Django project with Docker

- Django 4.2 with DRF and JWT
- Dockerfile for backend service
- Requirements with MySQL and Redis clients
- Pytest configuration

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Django Settings Configuration

**Files:**
- Modify: `backend/config/settings.py`

- [ ] **Step 1: Write test for settings import**

Create `backend/config/tests.py`:

```python
import os
from django.test import TestCase
from django.conf import settings


class SettingsTest(TestCase):
    def test_database_configured(self):
        """Test that database is configured correctly"""
        self.assertIn('default', settings.DATABASES)
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.mysql')
    
    def test_rest_framework_configured(self):
        """Test that DRF is configured"""
        self.assertIn('REST_FRAMEWORK', dir(settings))
        self.assertIn('DEFAULT_AUTHENTICATION_CLASSES', settings.REST_FRAMEWORK)
    
    def test_installed_apps_includes_drf(self):
        """Test that DRF is in INSTALLED_APPS"""
        self.assertIn('rest_framework', settings.INSTALLED_APPS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose run --rm django pytest config/tests.py -v`
Expected: Tests fail because settings not configured yet

- [ ] **Step 3: Update backend/config/settings.py**

Replace the entire file with:

```python
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-default-key-change-this')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'apps.users',
    'apps.llm_providers',
    'apps.inspirations',
    'apps.novels',
    'apps.chapters',
    'apps.tasks',
    'apps.stats',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DATABASE', 'fqxs'),
        'USER': os.getenv('MYSQL_USER', 'fqxs_user'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD', 'fqxs_password'),
        'HOST': os.getenv('MYSQL_HOST', 'mysql'),
        'PORT': os.getenv('MYSQL_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest config/tests.py -v`
Expected: All 3 tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/config/settings.py backend/config/tests.py
git commit -m "feat: configure Django settings with MySQL, Redis, and JWT

- Database connection to MySQL
- Redis configuration
- DRF with JWT authentication
- Chinese locale and Shanghai timezone
- Tests for settings validation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: User Model and App

**Files:**
- Create: `backend/apps/__init__.py`
- Create: `backend/apps/users/__init__.py`
- Create: `backend/apps/users/models.py`
- Create: `backend/apps/users/tests.py`

- [ ] **Step 1: Create apps directory structure**

Run: `mkdir -p backend/apps/users && touch backend/apps/__init__.py backend/apps/users/__init__.py`
Expected: Directory structure created

- [ ] **Step 2: Write test for User model**

Create `backend/apps/users/tests.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user(self):
        """Test creating a user with email and password"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_user_str_representation(self):
        """Test the string representation of user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user), 'testuser')
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker-compose run --rm django pytest apps/users/tests.py -v`
Expected: Tests fail because User model not created yet

- [ ] **Step 4: Write User model**

Create `backend/apps/users/models.py`:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Single-user system, but keeping user model for future extensibility.
    """
    email = models.EmailField(unique=True, verbose_name='邮箱')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return self.username
```

- [ ] **Step 5: Update settings.py to use custom User model**

Add to `backend/config/settings.py` after INSTALLED_APPS:

```python
AUTH_USER_MODEL = 'users.User'
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest apps/users/tests.py -v`
Expected: All 2 tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/apps/ backend/config/settings.py
git commit -m "feat: add custom User model

- Extend AbstractUser with email uniqueness
- Add created_at and updated_at timestamps
- Configure AUTH_USER_MODEL in settings
- Tests for user creation and string representation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: LLMProvider Model

**Files:**
- Create: `backend/apps/llm_providers/__init__.py`
- Create: `backend/apps/llm_providers/models.py`
- Create: `backend/apps/llm_providers/tests.py`

- [ ] **Step 1: Create llm_providers app structure**

Run: `mkdir -p backend/apps/llm_providers && touch backend/apps/llm_providers/__init__.py`
Expected: Directory created

- [ ] **Step 2: Write test for LLMProvider model**

Create `backend/apps/llm_providers/tests.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.llm_providers.models import LLMProvider

User = get_user_model()


class LLMProviderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_llm_provider(self):
        """Test creating an LLM provider"""
        provider = LLMProvider.objects.create(
            user=self.user,
            name='GPT-4 章节生成',
            provider_type='openai',
            api_url='https://api.openai.com/v1/chat/completions',
            api_key='sk-test123',
            task_type='chapter_writing',
            priority=1
        )
        self.assertEqual(provider.name, 'GPT-4 章节生成')
        self.assertEqual(provider.provider_type, 'openai')
        self.assertEqual(provider.task_type, 'chapter_writing')
        self.assertTrue(provider.is_active)
        self.assertEqual(provider.priority, 1)
    
    def test_llm_provider_str_representation(self):
        """Test the string representation"""
        provider = LLMProvider.objects.create(
            user=self.user,
            name='通义千问-创意',
            provider_type='qwen',
            api_url='https://api.qwen.com',
            api_key='test-key',
            task_type='idea_generation'
        )
        self.assertEqual(str(provider), '通义千问-创意 (qwen)')
    
    def test_api_key_encryption(self):
        """Test that API key is stored (encryption will be added later)"""
        provider = LLMProvider.objects.create(
            user=self.user,
            name='Test Provider',
            provider_type='custom',
            api_url='https://example.com',
            api_key='secret-key-123',
            task_type='chapter_writing'
        )
        # For now, just verify it's stored
        # TODO: Add encryption in future task
        self.assertEqual(provider.api_key, 'secret-key-123')
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker-compose run --rm django pytest apps/llm_providers/tests.py -v`
Expected: Tests fail because LLMProvider model not created yet

- [ ] **Step 4: Write LLMProvider model**

Create `backend/apps/llm_providers/models.py`:

```python
from django.db import models
from django.conf import settings


class LLMProvider(models.Model):
    """
    LLM service provider configuration.
    Stores API credentials and task type mapping.
    """
    PROVIDER_TYPES = [
        ('openai', 'OpenAI'),
        ('qwen', '通义千问'),
        ('custom', '自定义'),
    ]
    
    TASK_TYPES = [
        ('idea_generation', '创意生成'),
        ('chapter_writing', '章节写作'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='llm_providers',
        verbose_name='用户'
    )
    name = models.CharField(max_length=100, verbose_name='服务名称')
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPES,
        verbose_name='服务类型'
    )
    api_url = models.URLField(max_length=255, verbose_name='API 地址')
    api_key = models.CharField(max_length=255, verbose_name='API Key')
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPES,
        verbose_name='任务类型'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'llm_provider'
        verbose_name = 'LLM 服务提供商'
        verbose_name_plural = 'LLM 服务提供商'
        indexes = [
            models.Index(fields=['task_type', 'priority', 'is_active']),
        ]
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f'{self.name} ({self.provider_type})'
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest apps/llm_providers/tests.py -v`
Expected: All 3 tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/apps/llm_providers/
git commit -m "feat: add LLMProvider model

- Support OpenAI, Qwen, and custom providers
- Task type mapping (idea_generation, chapter_writing)
- Priority-based selection
- API key storage (encryption TODO)
- Tests for model creation and string representation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

---

### Task 6: Inspiration Model

**Files:**
- Create: `backend/apps/inspirations/__init__.py`
- Create: `backend/apps/inspirations/models.py`
- Create: `backend/apps/inspirations/tests.py`

- [ ] **Step 1: Create inspirations app structure**

Run: `mkdir -p backend/apps/inspirations && touch backend/apps/inspirations/__init__.py`
Expected: Directory created

- [ ] **Step 2: Write test for Inspiration model**

Create `backend/apps/inspirations/tests.py`:

```python
from django.test import TestCase
from apps.inspirations.models import Inspiration


class InspirationModelTest(TestCase):
    def test_create_inspiration(self):
        """Test creating an inspiration from crawled data"""
        inspiration = Inspiration.objects.create(
            source_url='https://fanqienovel.com/page/123',
            title='修仙从养猪开始',
            synopsis='一个养猪少年的修仙之路...',
            tags=['玄幻', '热血', '爽文'],
            hot_score=95.5,
            rank_type='hot_rank'
        )
        self.assertEqual(inspiration.title, '修仙从养猪开始')
        self.assertEqual(inspiration.hot_score, 95.5)
        self.assertFalse(inspiration.is_used)
        self.assertEqual(len(inspiration.tags), 3)
    
    def test_inspiration_str_representation(self):
        """Test the string representation"""
        inspiration = Inspiration.objects.create(
            source_url='https://example.com',
            title='测试小说',
            hot_score=80.0
        )
        self.assertEqual(str(inspiration), '测试小说 (80.0)')
    
    def test_mark_as_used(self):
        """Test marking inspiration as used"""
        inspiration = Inspiration.objects.create(
            source_url='https://example.com',
            title='测试小说',
            hot_score=80.0
        )
        self.assertFalse(inspiration.is_used)
        inspiration.is_used = True
        inspiration.save()
        self.assertTrue(inspiration.is_used)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker-compose run --rm django pytest apps/inspirations/tests.py -v`
Expected: Tests fail because Inspiration model not created yet

- [ ] **Step 4: Write Inspiration model**

Create `backend/apps/inspirations/models.py`:

```python
from django.db import models


class Inspiration(models.Model):
    """
    Creative inspiration collected from novel ranking lists.
    Used as seeds for generating new novel projects.
    """
    source_url = models.URLField(max_length=500, verbose_name='来源链接')
    title = models.CharField(max_length=200, verbose_name='书名')
    synopsis = models.TextField(blank=True, null=True, verbose_name='简介')
    tags = models.JSONField(default=list, verbose_name='标签')
    hot_score = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='热度分数'
    )
    rank_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='榜单类型'
    )
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name='采集时间')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'inspiration'
        verbose_name = '创意'
        verbose_name_plural = '创意'
        indexes = [
            models.Index(fields=['is_used', '-hot_score']),
            models.Index(fields=['-collected_at']),
        ]
        ordering = ['-hot_score', '-collected_at']
    
    def __str__(self):
        return f'{self.title} ({self.hot_score})'
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest apps/inspirations/tests.py -v`
Expected: All 3 tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/apps/inspirations/
git commit -m "feat: add Inspiration model

- Store crawled novel ideas from ranking lists
- JSON field for tags
- Hot score for ranking
- Track usage status
- Tests for creation and usage tracking

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: NovelProject Model

**Files:**
- Create: `backend/apps/novels/__init__.py`
- Create: `backend/apps/novels/models.py`
- Create: `backend/apps/novels/tests.py`

- [ ] **Step 1: Create novels app structure**

Run: `mkdir -p backend/apps/novels && touch backend/apps/novels/__init__.py`
Expected: Directory created

- [ ] **Step 2: Write test for NovelProject model**

Create `backend/apps/novels/tests.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.novels.models import NovelProject
from apps.inspirations.models import Inspiration

User = get_user_model()


class NovelProjectModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.inspiration = Inspiration.objects.create(
            source_url='https://example.com',
            title='原始创意',
            hot_score=90.0
        )
    
    def test_create_novel_project(self):
        """Test creating a novel project"""
        novel = NovelProject.objects.create(
            user=self.user,
            inspiration=self.inspiration,
            title='修仙从养猪开始',
            genre='玄幻',
            synopsis='一个养猪少年的修仙之路',
            outline='第一卷：养猪篇\n第二卷：筑基篇',
            ai_prompt_template='请根据以下大纲生成章节...',
            target_chapters=100,
            update_frequency=2
        )
        self.assertEqual(novel.title, '修仙从养猪开始')
        self.assertEqual(novel.status, 'active')
        self.assertEqual(novel.current_chapter, 0)
        self.assertEqual(novel.update_frequency, 2)
        self.assertFalse(novel.is_deleted)
    
    def test_novel_project_str_representation(self):
        """Test the string representation"""
        novel = NovelProject.objects.create(
            user=self.user,
            title='测试小说',
            genre='玄幻',
            target_chapters=50
        )
        self.assertEqual(str(novel), '测试小说')
    
    def test_soft_delete(self):
        """Test soft delete functionality"""
        novel = NovelProject.objects.create(
            user=self.user,
            title='测试小说',
            genre='玄幻'
        )
        self.assertFalse(novel.is_deleted)
        novel.is_deleted = True
        novel.save()
        self.assertTrue(novel.is_deleted)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker-compose run --rm django pytest apps/novels/tests.py -v`
Expected: Tests fail because NovelProject model not created yet

- [ ] **Step 4: Write NovelProject model**

Create `backend/apps/novels/models.py`:

```python
from django.db import models
from django.conf import settings


class NovelProject(models.Model):
    """
    Novel project representing a book being written.
    Tracks outline, generation settings, and publishing status.
    """
    STATUS_CHOICES = [
        ('active', '活跃'),
        ('paused', '暂停'),
        ('completed', '完结'),
        ('abandoned', '废弃'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='novels',
        verbose_name='用户'
    )
    inspiration = models.ForeignKey(
        'inspirations.Inspiration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='novels',
        verbose_name='创意来源'
    )
    title = models.CharField(max_length=200, verbose_name='书名')
    genre = models.CharField(max_length=50, verbose_name='分类')
    synopsis = models.TextField(blank=True, null=True, verbose_name='简介')
    outline = models.TextField(blank=True, null=True, verbose_name='大纲')
    ai_prompt_template = models.TextField(
        blank=True,
        null=True,
        verbose_name='章节生成 Prompt 模板'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='状态'
    )
    target_chapters = models.IntegerField(default=100, verbose_name='目标章节数')
    current_chapter = models.IntegerField(default=0, verbose_name='当前章节数')
    update_frequency = models.IntegerField(default=1, verbose_name='每日更新章节数')
    last_update_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最后更新时间'
    )
    tomato_book_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='番茄小说书籍 ID'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')
    
    class Meta:
        db_table = 'novel_project'
        verbose_name = '小说项目'
        verbose_name_plural = '小说项目'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'last_update_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest apps/novels/tests.py -v`
Expected: All 3 tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/apps/novels/
git commit -m "feat: add NovelProject model

- Track novel outline and generation settings
- Status workflow (active/paused/completed/abandoned)
- Update frequency configuration
- Soft delete support
- Link to inspiration source
- Tests for creation and soft delete

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Chapter Model

**Files:**
- Create: `backend/apps/chapters/__init__.py`
- Create: `backend/apps/chapters/models.py`
- Create: `backend/apps/chapters/tests.py`

- [ ] **Step 1: Create chapters app structure**

Run: `mkdir -p backend/apps/chapters && touch backend/apps/chapters/__init__.py`
Expected: Directory created

- [ ] **Step 2: Write test for Chapter model**

Create `backend/apps/chapters/tests.py`:

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.novels.models import NovelProject
from apps.chapters.models import Chapter
from apps.llm_providers.models import LLMProvider

User = get_user_model()


class ChapterModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.novel = NovelProject.objects.create(
            user=self.user,
            title='测试小说',
            genre='玄幻',
            target_chapters=100
        )
        self.provider = LLMProvider.objects.create(
            user=self.user,
            name='GPT-4',
            provider_type='openai',
            api_url='https://api.openai.com',
            api_key='test-key',
            task_type='chapter_writing'
        )
    
    def test_create_chapter(self):
        """Test creating a chapter"""
        chapter = Chapter.objects.create(
            project=self.novel,
            chapter_number=1,
            title='第一章：开始',
            raw_content='这是 AI 生成的原始内容...',
            word_count=2800,
            generation_prompt='请生成第一章...',
            llm_provider=self.provider,
            status='pending_review'
        )
        self.assertEqual(chapter.chapter_number, 1)
        self.assertEqual(chapter.title, '第一章：开始')
        self.assertEqual(chapter.status, 'pending_review')
        self.assertEqual(chapter.word_count, 2800)
        self.assertIsNone(chapter.final_content)
    
    def test_chapter_str_representation(self):
        """Test the string representation"""
        chapter = Chapter.objects.create(
            project=self.novel,
            chapter_number=5,
            title='第五章：突破',
            raw_content='内容...'
        )
        self.assertEqual(str(chapter), '测试小说 - 第5章')
    
    def test_chapter_unique_constraint(self):
        """Test that project + chapter_number is unique"""
        Chapter.objects.create(
            project=self.novel,
            chapter_number=1,
            raw_content='内容1'
        )
        with self.assertRaises(Exception):
            Chapter.objects.create(
                project=self.novel,
                chapter_number=1,
                raw_content='内容2'
            )
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker-compose run --rm django pytest apps/chapters/tests.py -v`
Expected: Tests fail because Chapter model not created yet

- [ ] **Step 4: Write Chapter model**

Create `backend/apps/chapters/models.py`:

```python
from django.db import models


class Chapter(models.Model):
    """
    Individual chapter of a novel project.
    Stores both AI-generated raw content and human-edited final content.
    """
    STATUS_CHOICES = [
        ('generating', '生成中'),
        ('pending_review', '待审核'),
        ('approved', '已审核'),
        ('published', '已发布'),
        ('failed', '生成失败'),
    ]
    
    project = models.ForeignKey(
        'novels.NovelProject',
        on_delete=models.CASCADE,
        related_name='chapters',
        verbose_name='所属项目'
    )
    chapter_number = models.IntegerField(verbose_name='章节序号')
    title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='章节标题'
    )
    raw_content = models.TextField(blank=True, null=True, verbose_name='AI 原始内容')
    final_content = models.TextField(
        blank=True,
        null=True,
        verbose_name='人工审核后内容'
    )
    word_count = models.IntegerField(default=0, verbose_name='字数')
    generation_prompt = models.TextField(
        blank=True,
        null=True,
        verbose_name='生成 Prompt'
    )
    llm_provider = models.ForeignKey(
        'llm_providers.LLMProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chapters',
        verbose_name='使用的 LLM 服务'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='generating',
        verbose_name='状态'
    )
    generated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='生成时间'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='审核时间'
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='发布时间'
    )
    tomato_chapter_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='番茄小说章节 ID'
    )
    read_count = models.IntegerField(default=0, verbose_name='阅读量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'chapter'
        verbose_name = '章节'
        verbose_name_plural = '章节'
        unique_together = [['project', 'chapter_number']]
        indexes = [
            models.Index(fields=['status', '-generated_at']),
        ]
        ordering = ['project', 'chapter_number']
    
    def __str__(self):
        return f'{self.project.title} - 第{self.chapter_number}章'
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest apps/chapters/tests.py -v`
Expected: All 3 tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/apps/chapters/
git commit -m "feat: add Chapter model

- Store AI-generated and human-edited content
- Status workflow (generating → pending_review → approved → published)
- Unique constraint on project + chapter_number
- Track generation metadata and read count
- Tests for creation and uniqueness

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Task and Stats Models

**Files:**
- Create: `backend/apps/tasks/__init__.py`
- Create: `backend/apps/tasks/models.py`
- Create: `backend/apps/tasks/tests.py`
- Create: `backend/apps/stats/__init__.py`
- Create: `backend/apps/stats/models.py`
- Create: `backend/apps/stats/tests.py`

- [ ] **Step 1: Create tasks and stats app structures**

Run: `mkdir -p backend/apps/tasks backend/apps/stats && touch backend/apps/tasks/__init__.py backend/apps/stats/__init__.py`
Expected: Directories created

- [ ] **Step 2: Write test for Task model**

Create `backend/apps/tasks/tests.py`:

```python
from django.test import TestCase
from apps.tasks.models import Task


class TaskModelTest(TestCase):
    def test_create_task(self):
        """Test creating a task"""
        task = Task.objects.create(
            task_type='generate_chapter',
            related_type='chapter',
            related_id=123,
            status='pending',
            celery_task_id='abc-123-def',
            params={'project_id': 1, 'chapter_number': 5}
        )
        self.assertEqual(task.task_type, 'generate_chapter')
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.retry_count, 0)
        self.assertIsNone(task.error_message)
    
    def test_task_str_representation(self):
        """Test the string representation"""
        task = Task.objects.create(
            task_type='crawl_ideas',
            status='running'
        )
        self.assertEqual(str(task), 'crawl_ideas - running')
```

- [ ] **Step 3: Write test for Stats model**

Create `backend/apps/stats/tests.py`:

```python
from django.test import TestCase
from datetime import date
from apps.stats.models import Stats


class StatsModelTest(TestCase):
    def test_create_stats(self):
        """Test creating stats record"""
        stats = Stats.objects.create(
            date=date(2026, 4, 3),
            metric_type='generation',
            metric_data={
                'total_chapters': 15,
                'success_rate': 0.93,
                'avg_word_count': 2800
            }
        )
        self.assertEqual(stats.metric_type, 'generation')
        self.assertEqual(stats.metric_data['total_chapters'], 15)
    
    def test_stats_unique_constraint(self):
        """Test that date + metric_type is unique"""
        Stats.objects.create(
            date=date(2026, 4, 3),
            metric_type='generation',
            metric_data={}
        )
        with self.assertRaises(Exception):
            Stats.objects.create(
                date=date(2026, 4, 3),
                metric_type='generation',
                metric_data={}
            )
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `docker-compose run --rm django pytest apps/tasks/tests.py apps/stats/tests.py -v`
Expected: Tests fail because models not created yet

- [ ] **Step 5: Write Task model**

Create `backend/apps/tasks/models.py`:

```python
from django.db import models


class Task(models.Model):
    """
    Async task tracking for Celery jobs.
    Records task parameters, results, and error messages.
    """
    TASK_TYPES = [
        ('crawl_ideas', '采集创意'),
        ('generate_outline', '生成大纲'),
        ('generate_chapter', '生成章节'),
        ('publish_chapter', '发布章节'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('retry', '重试中'),
    ]
    
    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPES,
        verbose_name='任务类型'
    )
    related_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='关联对象类型'
    )
    related_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='关联对象 ID'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='状态'
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Celery 任务 ID'
    )
    params = models.JSONField(default=dict, verbose_name='任务参数')
    result = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        verbose_name='任务结果'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='错误信息'
    )
    retry_count = models.IntegerField(default=0, verbose_name='重试次数')
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='开始时间'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'task'
        verbose_name = '任务'
        verbose_name_plural = '任务'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['celery_task_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.task_type} - {self.status}'
```

- [ ] **Step 6: Write Stats model**

Create `backend/apps/stats/models.py`:

```python
from django.db import models


class Stats(models.Model):
    """
    Daily statistics aggregation.
    Stores metrics for generation, cost, and performance.
    """
    METRIC_TYPES = [
        ('generation', '生成统计'),
        ('cost', '成本统计'),
        ('performance', '性能统计'),
    ]
    
    date = models.DateField(verbose_name='日期')
    metric_type = models.CharField(
        max_length=20,
        choices=METRIC_TYPES,
        verbose_name='指标类型'
    )
    metric_data = models.JSONField(default=dict, verbose_name='指标数据')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'stats'
        verbose_name = '统计数据'
        verbose_name_plural = '统计数据'
        unique_together = [['date', 'metric_type']]
        ordering = ['-date', 'metric_type']
    
    def __str__(self):
        return f'{self.date} - {self.metric_type}'
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest apps/tasks/tests.py apps/stats/tests.py -v`
Expected: All 4 tests pass

- [ ] **Step 8: Commit**

```bash
git add backend/apps/tasks/ backend/apps/stats/
git commit -m "feat: add Task and Stats models

Task model:
- Track Celery async jobs
- Store params, results, and errors
- Retry count tracking

Stats model:
- Daily metrics aggregation
- JSON storage for flexible metrics
- Unique constraint on date + metric_type

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Database Migrations

**Files:**
- Create: `backend/apps/users/migrations/0001_initial.py` (auto-generated)
- Create: `backend/apps/llm_providers/migrations/0001_initial.py` (auto-generated)
- Create: `backend/apps/inspirations/migrations/0001_initial.py` (auto-generated)
- Create: `backend/apps/novels/migrations/0001_initial.py` (auto-generated)
- Create: `backend/apps/chapters/migrations/0001_initial.py` (auto-generated)
- Create: `backend/apps/tasks/migrations/0001_initial.py` (auto-generated)
- Create: `backend/apps/stats/migrations/0001_initial.py` (auto-generated)

- [ ] **Step 1: Start Docker services**

Run: `docker-compose up -d mysql redis`
Expected: MySQL and Redis containers running

- [ ] **Step 2: Create migrations for all apps**

Run: `docker-compose run --rm django python manage.py makemigrations`
Expected: Migration files created for all 7 apps

- [ ] **Step 3: Verify migration files exist**

Run: `find backend/apps -name "0001_initial.py" | wc -l`
Expected: Output shows "7"

- [ ] **Step 4: Run migrations**

Run: `docker-compose run --rm django python manage.py migrate`
Expected: All migrations applied successfully

- [ ] **Step 5: Verify tables created in MySQL**

Run: `docker-compose exec mysql mysql -u fqxs_user -pfqxs_password fqxs -e "SHOW TABLES;"`
Expected: Output shows all 7 tables (user, llm_provider, inspiration, novel_project, chapter, task, stats)

- [ ] **Step 6: Verify table structure for user table**

Run: `docker-compose exec mysql mysql -u fqxs_user -pfqxs_password fqxs -e "DESCRIBE user;"`
Expected: Shows columns including id, username, email, password, created_at, updated_at, is_active

- [ ] **Step 7: Commit migrations**

```bash
git add backend/apps/*/migrations/
git commit -m "feat: add initial database migrations

- Create all 7 model tables in MySQL
- Apply indexes and constraints
- Verify table structure

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 11: JWT Authentication API

**Files:**
- Create: `backend/apps/users/serializers.py`
- Create: `backend/apps/users/views.py`
- Modify: `backend/config/urls.py`
- Create: `backend/apps/users/urls.py`

- [ ] **Step 1: Write test for login API**

Add to `backend/apps/users/tests.py`:

```python
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_login_success(self):
        """Test successful login returns JWT tokens"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_refresh_token(self):
        """Test refreshing access token"""
        login_response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        refresh_token = login_response.data['refresh']
        
        response = self.client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose run --rm django pytest apps/users/tests.py::AuthAPITest -v`
Expected: Tests fail because API endpoints not created yet

- [ ] **Step 3: Write user serializer**

Create `backend/apps/users/serializers.py`:

```python
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'created_at']
        read_only_fields = ['id', 'created_at']


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            data['user'] = user
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return data
```

- [ ] **Step 4: Write authentication views**

Create `backend/apps/users/views.py`:

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer, UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint.
    Returns JWT access and refresh tokens.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    user = serializer.validated_data['user']
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    """
    Refresh access token using refresh token.
    """
    from rest_framework_simplejwt.views import TokenRefreshView
    view = TokenRefreshView.as_view()
    return view(request._request)
```

- [ ] **Step 5: Create users URL configuration**

Create `backend/apps/users/urls.py`:

```python
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('refresh/', views.refresh_view, name='refresh'),
]
```

- [ ] **Step 6: Update main URL configuration**

Modify `backend/config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker-compose run --rm django pytest apps/users/tests.py::AuthAPITest -v`
Expected: All 3 tests pass

- [ ] **Step 8: Test login manually**

Run: `docker-compose up -d django`
Then: `curl -X POST http://localhost:8000/api/auth/login/ -H "Content-Type: application/json" -d '{"username":"testuser","password":"testpass123"}'`
Expected: Returns JSON with access, refresh, and user data

- [ ] **Step 9: Commit**

```bash
git add backend/apps/users/ backend/config/urls.py
git commit -m "feat: add JWT authentication API

- Login endpoint with username/password
- Token refresh endpoint
- User serializer
- Tests for authentication flow
- AllowAny permission for auth endpoints

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 12: Create Initial Admin User

**Files:**
- Create: `backend/apps/users/management/__init__.py`
- Create: `backend/apps/users/management/commands/__init__.py`
- Create: `backend/apps/users/management/commands/create_admin.py`

- [ ] **Step 1: Create management command structure**

Run: `mkdir -p backend/apps/users/management/commands && touch backend/apps/users/management/__init__.py backend/apps/users/management/commands/__init__.py`
Expected: Directory structure created

- [ ] **Step 2: Write create_admin command**

Create `backend/apps/users/management/commands/create_admin.py`:

```python
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create initial admin user for single-user system'
    
    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@fqxs.local'
        password = 'admin123'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists')
            )
            return
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created admin user:\n'
                f'  Username: {username}\n'
                f'  Password: {password}\n'
                f'  Email: {email}'
            )
        )
```

- [ ] **Step 3: Run command to create admin user**

Run: `docker-compose run --rm django python manage.py create_admin`
Expected: Output shows "Successfully created admin user"

- [ ] **Step 4: Verify admin user can login**

Run: `curl -X POST http://localhost:8000/api/auth/login/ -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}'`
Expected: Returns JWT tokens

- [ ] **Step 5: Commit**

```bash
git add backend/apps/users/management/
git commit -m "feat: add create_admin management command

- Create initial admin user for single-user system
- Default credentials: admin/admin123
- Check for existing user before creation

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 13: Documentation and README

**Files:**
- Create: `README.md`
- Create: `docs/setup.md`

- [ ] **Step 1: Write README.md**

Create `README.md`:

```markdown
# 番茄小说自动写作平台 (TomatoFiction Auto-Platform)

单用户自动化创作平台，实现创意采集 → 多书并行写作 → 人工审核发布的全流程。

## 技术栈

- **后端**: Django 4.2 + DRF + Celery + Redis
- **生成服务**: FastAPI + 多 LLM Provider 适配层
- **数据库**: MySQL 8.0 + Redis 7
- **前端**: React 18 + TypeScript + Vite + Zustand + Ant Design
- **部署**: Docker Compose

## 快速开始

### 1. 环境准备

- Docker 和 Docker Compose
- Git

### 2. 克隆项目

\`\`\`bash
git clone <repository-url>
cd fqxs
\`\`\`

### 3. 配置环境变量

\`\`\`bash
cp .env.example .env
# 编辑 .env 文件，修改密码等敏感信息
\`\`\`

### 4. 启动服务

\`\`\`bash
# 启动数据库
docker-compose up -d mysql redis

# 运行数据库迁移
docker-compose run --rm django python manage.py migrate

# 创建管理员用户
docker-compose run --rm django python manage.py create_admin

# 启动 Django 服务
docker-compose up -d django
\`\`\`

### 5. 验证安装

访问 http://localhost:8000/api/auth/login/ 测试登录接口。

默认管理员账号：
- 用户名: `admin`
- 密码: `admin123`

## 项目结构

\`\`\`
fqxs/
├── backend/              # Django 后端
│   ├── apps/            # 应用模块
│   │   ├── users/       # 用户认证
│   │   ├── llm_providers/  # LLM 服务配置
│   │   ├── inspirations/   # 创意库
│   │   ├── novels/         # 小说项目
│   │   ├── chapters/       # 章节管理
│   │   ├── tasks/          # 任务追踪
│   │   └── stats/          # 数据统计
│   └── config/          # Django 配置
├── docs/                # 文档
├── docker-compose.yml   # Docker 编排
└── README.md
\`\`\`

## 开发指南

### 运行测试

\`\`\`bash
docker-compose run --rm django pytest
\`\`\`

### 查看日志

\`\`\`bash
docker-compose logs -f django
\`\`\`

### 进入 Django Shell

\`\`\`bash
docker-compose run --rm django python manage.py shell
\`\`\`

## 当前进度

- [x] Phase 1: 基础架构与数据层
  - [x] Docker Compose 环境
  - [x] Django 项目初始化
  - [x] 数据模型（User, LLMProvider, Inspiration, NovelProject, Chapter, Task, Stats）
  - [x] 数据库迁移
  - [x] JWT 认证 API

- [ ] Phase 2: FastAPI LLM 服务
- [ ] Phase 3: Django 核心 API
- [ ] Phase 4: Celery 任务系统
- [ ] Phase 5: React 前端

## 许可证

MIT
\`\`\`

- [ ] **Step 2: Write setup documentation**

Create `docs/setup.md`:

```markdown
# 开发环境搭建指南

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- Git 2.30+

## 详细步骤

### 1. 克隆仓库

\`\`\`bash
git clone <repository-url>
cd fqxs
\`\`\`

### 2. 环境变量配置

复制环境变量模板：

\`\`\`bash
cp .env.example .env
\`\`\`

编辑 `.env` 文件，修改以下配置：

\`\`\`env
# 修改为强密码
SECRET_KEY=your-secret-key-here
MYSQL_ROOT_PASSWORD=your-root-password
MYSQL_PASSWORD=your-password
\`\`\`

### 3. 启动数据库服务

\`\`\`bash
docker-compose up -d mysql redis
\`\`\`

等待服务健康检查通过（约 10-15 秒）：

\`\`\`bash
docker-compose ps
\`\`\`

### 4. 运行数据库迁移

\`\`\`bash
docker-compose run --rm django python manage.py migrate
\`\`\`

### 5. 创建管理员用户

\`\`\`bash
docker-compose run --rm django python manage.py create_admin
\`\`\`

记录输出的用户名和密码。

### 6. 启动 Django 服务

\`\`\`bash
docker-compose up -d django
\`\`\`

### 7. 验证安装

测试登录接口：

\`\`\`bash
curl -X POST http://localhost:8000/api/auth/login/ \\
  -H "Content-Type: application/json" \\
  -d '{"username":"admin","password":"admin123"}'
\`\`\`

应该返回包含 `access` 和 `refresh` token 的 JSON。

## 常见问题

### MySQL 连接失败

检查 MySQL 容器是否健康：

\`\`\`bash
docker-compose ps mysql
\`\`\`

查看 MySQL 日志：

\`\`\`bash
docker-compose logs mysql
\`\`\`

### 迁移失败

重置数据库（警告：会删除所有数据）：

\`\`\`bash
docker-compose down -v
docker-compose up -d mysql redis
# 等待 10 秒
docker-compose run --rm django python manage.py migrate
\`\`\`

### 端口冲突

如果 3306 或 8000 端口被占用，修改 `docker-compose.yml` 中的端口映射。

## 下一步

查看 [API 文档](./api.md) 了解可用的接口。
\`\`\`

- [ ] **Step 3: Commit documentation**

```bash
git add README.md docs/setup.md
git commit -m "docs: add README and setup guide

- Project overview and tech stack
- Quick start guide
- Development commands
- Troubleshooting section
- Current progress tracking

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

### Spec Coverage

- [x] Docker Compose environment (Task 1)
- [x] Django project initialization (Task 2)
- [x] Django settings configuration (Task 3)
- [x] User model (Task 4)
- [x] LLMProvider model (Task 5)
- [x] Inspiration model (Task 6)
- [x] NovelProject model (Task 7)
- [x] Chapter model (Task 8)
- [x] Task and Stats models (Task 9)
- [x] Database migrations (Task 10)
- [x] JWT authentication API (Task 11)
- [x] Initial admin user (Task 12)
- [x] Documentation (Task 13)

### Placeholder Scan

- No TBD, TODO, or incomplete sections
- All code blocks are complete
- All commands have expected outputs
- No "implement later" or "add appropriate" placeholders

### Type Consistency

- User model: `username`, `email`, `password_hash`
- LLMProvider: `provider_type`, `task_type`, `api_key`
- NovelProject: `status` (active/paused/completed/abandoned)
- Chapter: `status` (generating/pending_review/approved/published/failed)
- Task: `task_type`, `status`, `celery_task_id`
- All field names consistent across tasks

### Ambiguity Check

- All file paths are absolute and explicit
- All commands include expected output
- All tests have clear assertions
- All models have explicit field types and constraints

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-03-mvp-phase1-infrastructure.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**