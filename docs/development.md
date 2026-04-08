# 开发过程文档

> 本文档记录了项目的完整开发历程，包含每个阶段完成的任务、技术决策和遇到的问题。

---

## 阶段概览

| 阶段 | 内容 | 时间 | 状态 |
|------|------|------|------|
| Phase 1 | 基础架构与数据层 | 2026-04-03 | 完成 |
| Phase 2 | JWT 认证与核心 API | 2026-04-03 ~ 04-04 | 完成 |
| Phase 3 | 前端页面与联调 | 2026-04-04 | 完成 |
| Phase 4 | 爬虫 + Celery + FastAPI | 2026-04-04 夜间 | 完成 |
| Phase 5 | CCB 清理 + Agent Team 迁移 | 2026-04-07 | 完成 |
| Phase 6 | 日志监控 + 备份恢复 | 2026-04-08 | 完成 |

---

## Phase 1: 基础架构与数据层

### Task 1: Docker Compose 环境
- 编写 `docker-compose.yml`，启动 MySQL 8.0 和 Redis 7
- 创建 `.env.example` 环境变量模板
- 创建 `.gitignore`，排除 venv、__pycache__、.env 等
- **验证**: `docker-compose up -d` 成功，MySQL 和 Redis 健康检查通过

### Task 2: Django 项目初始化
- 创建 Django 4.2 项目 (`config/`)
- 编写 `backend/requirements.txt`：DRF、SimpleJWT、mysqlclient、Celery、redis、pytest
- 编写 `backend/Dockerfile`，安装系统依赖和 Python 依赖
- 配置 pytest (`pytest.ini`)

### Task 3: Django Settings 配置
- MySQL 数据库连接配置
- Redis 连接配置
- DRF + JWT 认证配置
- 中文语言环境 + 上海时区
- 分页配置（PageNumberPagination，PAGE_SIZE=20）

### Task 4-9: 数据模型（7 个 apps）

| App | Model | 文件数 | 说明 |
|-----|-------|--------|------|
| users | User | models.py | 自定义 User 继承 AbstractUser，email 唯一 |
| llm_providers | LLMProvider | models.py | 多 LLM 提供商配置，按 task_type 分类 |
| inspirations | Inspiration | models.py | 创意数据，hot_score 排序，is_used 标记 |
| novels | NovelProject | models.py | 小说项目，软删除，状态管理 |
| chapters | Chapter | models.py | 章节，raw_content/final_content 分离 |
| tasks | Task | models.py | 异步任务追踪，关联 Celery task_id |
| stats | Stats | models.py | 每日统计快照，JSON 存储指标数据 |

- **每个 Model 都包含测试用例**（create + __str__ + 特殊约束验证）
- 所有 Model 的 `db_table` 与设计文档一致

### Task 10: 数据库迁移
- `makemigrations` 为 7 个 app 生成初始迁移
- `migrate` 成功应用所有迁移到 MySQL
- 验证 7 张表创建成功

### Task 11: JWT 认证 API
- `POST /api/users/login/` - 返回 access_token + refresh_token + 用户信息
- `POST /api/users/refresh/` - 刷新 access_token
- LoginSerializer + UserSerializer + login_view + refresh_view
- 3 个测试：成功登录、密码错误、刷新 Token

### Task 12: 管理员用户
- `manage.py create_admin` 管理命令
- 默认用户名 `admin`，密码 `admin123`
- 幂等：已存在时不重复创建

### Task 13: 前端 React 项目初始化
- Vite + TypeScript + React 18
- package.json 配置：react-router-dom、zustand、antd、echarts、axios、tailwindcss
- 路由守卫（登录验证）
- 布局组件（Sidebar + Header）

---

## Phase 2: 核心 API 与前端功能

### 创意管理 API
- `apps/inspirations/` 完整 CRUD + 批量标记已使用
- serializer、view、url 补齐
- DRF 分页 + 过滤（is_used, hot_score, rank_type）

### 项目管理 API
- `apps/novels/` 完整 CRUD（软删除）
- 多条件过滤：status、type/genre、search、created_after/before
- 权限控制（仅操作自己的项目）

### 章节管理 API
- `apps/chapters/` 完整 CRUD（软删除）
- 过滤：project_id、publish_status、标题搜索、时间范围
- 自动 word_count 计算（基于 final_content）
- 异步生成端点 `generate-async/`

### 前端页面开发
- **Dashboard**: 统计卡片 + ECharts 图表
- **创意库**: 列表表格 + 筛选 + 批量操作
- **项目管理**: 列表 + CRUD + 状态过滤
- **章节管理**: Markdown 编辑器（@uiw/react-md-editor）、实时字数统计、人工审核提示

### API 对接
- 移除所有 mock 数据
- 统一 axios 拦截器处理 JWT Token
- 完善错误处理和 loading 状态

---

## Phase 3: 爬虫 + Celery + FastAPI（夜间开发）

### Scrapy 爬虫系统
- `backend/scrapy_spiders/` 完整爬虫项目
- `tomato_spider` 番茄小说榜单爬取
- **反爬策略**: 代理 IP 池、User-Agent 轮换、请求头伪装、3 秒延迟、AutoThrottle
- **数据处理**: MySQL 存储、按 source_url 自动去重、数据清洗
- **Django 管理命令**: `python manage.py run_spider --limit 50 --rank-types hot,new,rising`

### Celery 异步任务系统
- `backend/celery_tasks/` 任务模块
  - `ai_tasks.py` - AI 生成异步任务
  - `crawl_tasks.py` - 爬虫定时任务
  - `stats_tasks.py` - 统计更新任务
- Worker + Beat 配置
- 任务状态查询 API（`GET /api/tasks/<task_id>/status/`）
- 定时任务：每天凌晨 2 点爬虫、每小时更新统计
- **测试**: 74/74 通过，代码覆盖率 99%

### FastAPI AI 生成服务
- `fastapi_service/` 独立服务（端口 8001）
- mock 生成器（中文内容，参数驱动长度）
- 3 个端点：outline、chapter、continue
- CORS 配置（允许 localhost:8000, localhost:5173）
- `/docs` Swagger UI 自动文档
- **验证**: compileall 通过，TestClient 所有端点返回 200

---

## Phase 4: CCB 清理（2026-04-07）

### 删除的文件/目录
| 路径 | 说明 |
|------|------|
| `.ccb/` | CCB 会话目录 |
| `start-role-team.sh` | CCB 启动脚本 |
| `.ai-team/` | CCB AI 团队 prompts |
| `CODEX.md` | Codex 角色配置 |
| `GEMINI.md` | Gemini 角色配置 |

### 重写的文件
| 文件 | 变更 |
|------|------|
| `CLAUDE.md` | 删除 CCB 通信说明，改为简洁的 Agent Team 模式 |
| `AGENTS.md` | 删除 Gemini/Codex/CCB 相关内容，改为通用 Agent 职责定义 |

### 移除的定时任务
- 删除每 10 分钟检查 Gemini/Codex 进度的 cron job

---

## Phase 6: 日志监控 + 备份恢复（2026-04-08）

### 日志系统
- 结构化日志配置（verbose、simple、json 格式）
- 日志文件轮转（10MB，保留 5 个备份）
- 分类日志：django.log、error.log、celery.log、app.json.log
- 请求日志中间件（记录请求时间、状态码、用户、IP）
- 性能监控装饰器（log_execution_time、log_celery_task）
- PerformanceMonitor 上下文管理器

### 监控系统
- 健康检查端点（`/api/health/`）
  - 数据库连接检查
  - Redis 连接检查
  - FastAPI 服务检查
- 系统监控脚本（`scripts/health_check.py`）
- Sentry 错误追踪集成（可选）

### LLM Provider 管理增强
- 连接测试端点（`POST /api/llm-providers/{id}/test_connection/`）
- 优先级设置端点（`POST /api/llm-providers/{id}/set_priority/`）
- 详细日志记录

### 备份恢复系统
- 数据库备份脚本（`scripts/backup_db.sh`）
  - 自动压缩（gzip）
  - 自动清理旧备份（默认保留 7 天）
  - 支持环境变量配置
- 数据库恢复脚本（`scripts/restore_db.sh`）
  - 交互式确认
  - 自动解压
- 备份恢复文档（`docs/backup_recovery.md`）

### 依赖更新
- python-json-logger==2.0.7（JSON 格式日志）
- sentry-sdk==2.0.0（错误追踪）

---

## 技术决策记录

### 1. 为什么 Django 不直接调用 LLM？
通过 HTTP 调用独立的 FastAPI 服务，实现关注点分离：
- FastAPI 可独立扩展、重启，不阻塞 Django
- 支持多 Provider 动态切换
- 重试、超时、熔断在 FastAPI 层统一处理

### 2. 为什么 raw_content 和 final_content 分开？
- raw_content 记录 AI 生成的原始内容，用于审计和质量分析
- final_content 是人工编辑后的最终内容
- 两个字段对比可计算修改率，确保人工审核合规

### 3. 为什么用 SQLite 做测试？
- pytest 测试使用 SQLite（pytest-django 默认），避免依赖外部 MySQL
- 生产环境使用 MySQL
- 测试速度快，CI/CD 友好

### 4. 为什么用 Celery 而不是 Django-Q？
- Celery 生态更成熟，Beats 定时任务稳定
- Flower 监控面板功能强大
- Redis broker 配置简单

---

## 测试结果

```
后端测试: 74/74 通过
前端构建: 无 TypeScript 错误
代码覆盖率: 99%（后端核心模块）
文件变更: 60+ 文件
```

---

## 服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:5173 | React 应用 |
| 后端 API | http://localhost:8000 | Django REST API |
| FastAPI | http://localhost:8001 | AI 生成服务 |
| FastAPI 文档 | http://localhost:8001/docs | Swagger UI |
| Django Admin | http://localhost:8000/admin | 后台管理 |
| Flower | http://localhost:5555 | Celery 监控 |

**测试账号**: admin / admin123

---

## 运行命令

### 后端
```bash
cd backend
source .venv/bin/activate
python manage.py runserver        # Django
celery -A config worker -l info   # Celery Worker
celery -A config beat -l info     # Celery Beat
celery -A config flower --port=5555  # Flower 监控
```

### 前端
```bash
cd frontend
npm run dev
```

### FastAPI
```bash
cd fastapi_service
source .venv/bin/activate
uvicorn main:app --reload --port 8001
```

### 爬虫
```bash
# 调试模式（无代理）
python manage.py run_spider --limit 5 --rank-types hot --allow-no-proxy

# 生产模式
export SCRAPY_PROXY_LIST="http://ip1:port,http://ip2:port"
python manage.py run_spider --limit 50 --rank-types hot,new,rising
```

### 测试
```bash
cd backend
.venv/bin/python -m pytest -v      # 全部测试
.venv/bin/python manage.py test    # Django 原生测试
```
