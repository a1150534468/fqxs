---
name: 番茄小说自动写作平台设计
description: 单用户自动化创作平台，实现创意采集、多书并行写作、人工审核发布的全流程
type: system-design
date: 2026-04-03
---

# 番茄小说自动写作平台 - 系统设计文档

## 一、项目总览

### 1.1 目标
构建单用户番茄小说自动化创作平台，实现创意采集 → 多书并行写作 → 人工审核发布的全流程自动化。

### 1.2 核心约束
- 单用户使用，功能完整性优先
- 多书并行更新（3-5 本书同时维护）
- 自动生成内容，仅发布环节人工确认
- 合规、可审计、可人工审核
- LLM 服务可配置多 Provider（创意生成 vs 章节写作）

### 1.3 技术栈
- **前端**: React 18 + TypeScript + Vite + Zustand + Ant Design + ECharts
- **后端**: Django 4.2 + DRF + Celery + Redis
- **生成服务**: FastAPI + 多 LLM Provider 适配层
- **数据库**: MySQL（主库）+ Redis（缓存/队列）
- **部署**: Docker Compose

### 1.4 里程碑
- **MVP**（2-3 周）：创意采集 + 手动触发生成 + 人工审核
- **Beta**（1-2 周）：自动化循环 + 数据统计看板
- **上线优化**（1-2 周）：半自动发布 + 稳定性优化

---

## 二、系统架构

### 2.1 分层架构

```
┌─────────────────────────────────────────┐
│         React 前端管理后台               │
│  (Dashboard/创意库/项目管理/审核区)      │
└─────────────────┬───────────────────────┘
                  │ HTTP/WebSocket
┌─────────────────▼───────────────────────┐
│         Django REST API                  │
│  (认证/CRUD/任务触发/数据统计)           │
└─────┬───────────────────────┬───────────┘
      │                       │
      │ HTTP                  │ Celery Task
      ▼                       ▼
┌─────────────┐      ┌──────────────────┐
│  FastAPI    │      │  Celery Worker   │
│  LLM 服务   │      │  (爬虫/调度)     │
└─────────────┘      └──────────────────┘
      │                       │
      └───────────┬───────────┘
                  ▼
        ┌──────────────────┐
        │  MySQL + Redis   │
        └──────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 | 技术选型 |
|------|------|----------|
| Django 层 | 数据 CRUD、权限、API 网关、任务编排 | Django + DRF |
| FastAPI 层 | LLM 调用、Prompt 工程、内容生成 | FastAPI + httpx |
| Celery 层 | 定时任务、爬虫、异步任务队列 | Celery + Redis |
| React 层 | 可视化管理、人工审核、数据看板 | React + Zustand + Ant Design |

### 2.3 关键设计决策
- Django 不直接调用 LLM，通过 HTTP 调用 FastAPI（解耦 + 避免阻塞）
- 爬虫作为 Celery Beat 定时任务，不独立部署
- 所有自动化流程由 Celery 编排，Django 只负责触发和查询
- 前端通过 WebSocket 实时获取任务进度

---

## 三、数据模型设计

### 3.1 核心表结构

#### User（用户表）
```sql
CREATE TABLE user (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### LLMProvider（LLM 服务配置表）
```sql
CREATE TABLE llm_provider (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    provider_type ENUM('openai', 'qwen', 'custom') NOT NULL,
    api_url VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) NOT NULL,  -- 加密存储
    task_type ENUM('idea_generation', 'chapter_writing') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    priority INT DEFAULT 0,  -- 同类型多个 Provider 时的优先级
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    INDEX idx_task_type_priority (task_type, priority, is_active)
);
```

#### Inspiration（创意表）
```sql
CREATE TABLE inspiration (
    id INT PRIMARY KEY AUTO_INCREMENT,
    source_url VARCHAR(500) NOT NULL,
    title VARCHAR(200) NOT NULL,
    synopsis TEXT,
    tags JSON,  -- ["玄幻", "热血", "爽文"]
    hot_score DECIMAL(10, 2) DEFAULT 0,
    rank_type VARCHAR(50),  -- "hot_rank", "new_rank"
    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_is_used_hot_score (is_used, hot_score),
    INDEX idx_collected_at (collected_at)
);
```

#### NovelProject（小说项目表）
```sql
CREATE TABLE novel_project (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    inspiration_id INT,  -- 可选，记录创意来源
    title VARCHAR(200) NOT NULL,
    genre VARCHAR(50) NOT NULL,
    synopsis TEXT,
    outline TEXT,  -- 大纲
    ai_prompt_template TEXT,  -- 章节生成的 Prompt 模板
    status ENUM('active', 'paused', 'completed', 'abandoned') DEFAULT 'active',
    target_chapters INT DEFAULT 100,
    current_chapter INT DEFAULT 0,
    update_frequency INT DEFAULT 1,  -- 每天更新几章
    last_update_at DATETIME,
    tomato_book_id VARCHAR(100),  -- 番茄小说的书籍 ID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (inspiration_id) REFERENCES inspiration(id),
    INDEX idx_user_status (user_id, status),
    INDEX idx_status_last_update (status, last_update_at)
);
```

#### Chapter（章节表）
```sql
CREATE TABLE chapter (
    id INT PRIMARY KEY AUTO_INCREMENT,
    project_id INT NOT NULL,
    chapter_number INT NOT NULL,
    title VARCHAR(200),
    raw_content TEXT,  -- AI 原始生成内容
    final_content TEXT,  -- 人工审核后的最终内容
    word_count INT DEFAULT 0,
    generation_prompt TEXT,  -- 生成时使用的完整 Prompt
    llm_provider_id INT,  -- 使用的 LLM 服务
    status ENUM('generating', 'pending_review', 'approved', 'published', 'failed') DEFAULT 'generating',
    generated_at DATETIME,
    reviewed_at DATETIME,
    published_at DATETIME,
    tomato_chapter_id VARCHAR(100),
    read_count INT DEFAULT 0,  -- 阅读量
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES novel_project(id),
    FOREIGN KEY (llm_provider_id) REFERENCES llm_provider(id),
    UNIQUE KEY uk_project_chapter (project_id, chapter_number),
    INDEX idx_status_generated (status, generated_at)
);
```

#### Task（任务表）
```sql
CREATE TABLE task (
    id INT PRIMARY KEY AUTO_INCREMENT,
    task_type ENUM('crawl_ideas', 'generate_outline', 'generate_chapter', 'publish_chapter') NOT NULL,
    related_type VARCHAR(50),  -- 'novel', 'chapter'
    related_id INT,
    status ENUM('pending', 'running', 'success', 'failed', 'retry') DEFAULT 'pending',
    celery_task_id VARCHAR(255),
    params JSON,  -- 任务参数
    result JSON,  -- 任务结果
    error_message TEXT,
    retry_count INT DEFAULT 0,
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status_created (status, created_at),
    INDEX idx_celery_task_id (celery_task_id)
);
```

#### Stats（统计表）
```sql
CREATE TABLE stats (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL,
    metric_type ENUM('generation', 'cost', 'performance') NOT NULL,
    metric_data JSON,  -- 具体指标数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_metric (date, metric_type)
);
```

### 3.2 索引策略
- 高频查询字段：status, created_at, user_id
- 联合索引：(status, last_update_at), (is_used, hot_score)
- 唯一索引：(project_id, chapter_number) 防止重复生成

---

## 四、API 接口设计

### 4.1 认证接口

**POST /api/auth/login**
```json
Request: {"username": "admin", "password": "xxx"}
Response: {"token": "jwt_token", "user": {"id": 1, "username": "admin"}}
```

**POST /api/auth/refresh**
```json
Request: {"token": "old_token"}
Response: {"token": "new_token"}
```

### 4.2 LLM Provider 管理

**GET /api/llm-providers**
```json
Response: [
  {"id": 1, "name": "通义千问-创意", "provider_type": "qwen", "task_type": "idea_generation", "is_active": true, "priority": 1}
]
```

**POST /api/llm-providers**
```json
Request: {
  "name": "GPT-4-章节",
  "provider_type": "openai",
  "api_url": "https://api.openai.com/v1/chat/completions",
  "api_key": "sk-xxx",
  "task_type": "chapter_writing",
  "priority": 1
}
Response: {"id": 2, ...}
```

### 4.3 创意管理

**GET /api/inspirations**
```json
Query: ?is_used=false&sort=hot_score&page=1&limit=20
Response: {
  "items": [...],
  "total": 100,
  "page": 1,
  "limit": 20
}
```

**POST /api/inspirations/crawl**
```json
Request: {"rank_types": ["hot", "new"]}
Response: {"task_id": "abc123"}
```

### 4.4 小说项目管理

**GET /api/novels**
**POST /api/novels**
**PUT /api/novels/:id**
**DELETE /api/novels/:id**（软删除）

**POST /api/novels/:id/generate-outline**
```json
Request: {"llm_provider_id": 1}  // 可选
Response: {"task_id": "def456"}
```

**POST /api/novels/:id/start-auto-writing**
```json
Response: {"success": true}
```

### 4.5 章节管理

**GET /api/novels/:novel_id/chapters**
**GET /api/chapters/:id**
**PUT /api/chapters/:id**（人工编辑）
**POST /api/chapters/:id/approve**（审核通过）
**POST /api/chapters/:id/regenerate**（重新生成）
**POST /api/chapters/:id/publish**（发布到番茄）

### 4.6 任务管理

**GET /api/tasks**
**GET /api/tasks/:id**
**POST /api/tasks/:id/retry**

### 4.7 数据统计

**GET /api/stats/dashboard**
```json
Query: ?start_date=2026-04-01&end_date=2026-04-03
Response: {
  "generation": {"total_chapters": 15, "success_rate": 0.93, "avg_word_count": 2800},
  "cost": {"total_api_calls": 50, "total_tokens": 150000, "estimated_cost": 12.5},
  "performance": {"avg_generation_time": 25.3, "current_queue_length": 3},
  "novels": {"active_count": 5, "total_chapters_published": 120}
}
```

### 4.8 FastAPI LLM 服务接口

**POST /generate/outline**
```json
Request: {
  "provider_config": {"api_url": "...", "api_key": "...", "model": "gpt-4"},
  "title": "修仙从养猪开始",
  "genre": "玄幻",
  "synopsis": "...",
  "target_chapters": 100
}
Response: {"outline": "第一卷：...", "tokens_used": 1500}
```

**POST /generate/chapter**
```json
Request: {
  "provider_config": {...},
  "novel_context": {
    "title": "...",
    "genre": "...",
    "outline": "...",
    "previous_chapters_summary": "..."
  },
  "chapter_number": 5,
  "prompt_template": "..."
}
Response: {"title": "第五章：突破", "content": "...", "word_count": 2800, "tokens_used": 3500}
```

### 4.9 错误码
- 200: 成功
- 400: 参数错误
- 401: 未认证
- 403: 无权限
- 404: 资源不存在
- 500: 服务器错误
- 502: LLM 服务调用失败

---

## 五、自动化流程设计

### 5.1 Celery Beat 定时任务

```python
CELERYBEAT_SCHEDULE = {
    # 每天凌晨 2 点爬取创意
    'crawl-inspirations': {
        'task': 'tasks.crawl_inspirations',
        'schedule': crontab(hour=2, minute=0),
    },
    # 每天早上 8 点触发多书更新
    'daily-chapter-generation': {
        'task': 'tasks.generate_daily_chapters',
        'schedule': crontab(hour=8, minute=0),
    },
    # 每小时同步章节阅读数据
    'sync-chapter-stats': {
        'task': 'tasks.sync_chapter_stats',
        'schedule': crontab(minute=0),
    },
}
```

### 5.2 任务编排流程

#### 创意采集任务（crawl_inspirations）
```
输入：rank_types = ["hot", "new"]
流程：
  1. 使用 Scrapy 爬取番茄小说榜单
  2. 提取书名、简介、标签、热度
  3. 去重（基于 title + source_url）
  4. 计算热度分数（榜单排名 + 评论数）
  5. 批量插入 Inspiration 表
输出：{crawled_count: 50, new_count: 12}
风控：随机延迟 2-5 秒，使用代理 IP 池
```

#### 每日章节生成任务（generate_daily_chapters）
```
输入：无
流程：
  1. 查询 status=active 的所有 NovelProject
  2. 根据 update_frequency 和 last_update_at 筛选今天需要更新的项目
  3. 对每个项目：
     a. 检查是否有 pending_review 的章节（有则跳过）
     b. 计算下一章节号 = current_chapter + 1
     c. 调用 generate_chapter_task.delay(project_id, chapter_number)
  4. 更新 NovelProject.last_update_at
输出：{triggered_tasks: ["task_id_1", "task_id_2", ...]}
```

#### 单章节生成任务（generate_chapter_task）
```
输入：project_id, chapter_number
流程：
  1. 查询 NovelProject 获取 outline, ai_prompt_template
  2. 查询最近 3 章内容作为上下文
  3. 选择 task_type=chapter_writing 的 LLMProvider（按 priority）
  4. 构建完整 Prompt
  5. HTTP POST 到 FastAPI /generate/chapter
  6. 创建 Chapter 记录，status=pending_review
  7. 更新 NovelProject.current_chapter
  8. 记录 Task 结果
输出：{chapter_id: 123, word_count: 2800, tokens_used: 3500}
失败处理：重试 3 次，失败后标记 Chapter.status=failed
```

#### 章节统计同步任务（sync_chapter_stats）
```
输入：无
流程：
  1. 查询 status=published 且 tomato_chapter_id 不为空的章节
  2. 爬取番茄小说章节详情页获取阅读量
  3. 更新 Chapter.read_count
  4. 聚合数据写入 Stats 表
输出：{synced_count: 25}
风控：每次最多同步 50 章，随机延迟
```

### 5.3 状态流转

```
Inspiration: collected → used
NovelProject: active ⇄ paused → completed/abandoned
Chapter: generating → pending_review → approved → published
         ↓ (失败)
       failed → (可重新生成)
Task: pending → running → success/failed
```

---

## 六、前端设计

### 6.1 页面路由

```
/login                    - 登录页
/dashboard                - 数据看板（首页）
/inspirations             - 创意库
/novels                   - 小说项目列表
/novels/:id               - 单个小说详情
/novels/:id/chapters      - 章节列表
/chapters/:id/review      - 章节审核编辑器
/chapters/pending         - 待审核章节队列
/llm-providers            - LLM 服务配置
/tasks                    - 任务监控
/stats                    - 数据统计报表
/settings                 - 系统设置
```

### 6.2 核心页面

#### Dashboard（数据看板）
- 顶部 4 个卡片：今日生成章节数、待审核数、活跃项目数、总阅读量
- 中部左侧：最近 7 天生成趋势图（ECharts 折线图）
- 中部右侧：成本统计（API 调用次数、Token 消耗、预估费用）
- 底部：任务队列状态（运行中/待处理/失败）
- 右侧边栏：快捷操作（触发爬虫、查看待审核）

#### Chapter Review（章节审核编辑器）
- 左侧：章节信息（书名、章节号、生成时间、字数、使用的 LLM）
- 中部：富文本编辑器（显示 raw_content，可编辑保存到 final_content）
- 右侧：操作面板（保存草稿、审核通过、重新生成、查看上下文）
- 底部：上一章/下一章导航

### 6.3 状态管理（Zustand）

```typescript
// stores/authStore.ts
{user, token, login(), logout()}

// stores/novelStore.ts
{novels, fetchNovels(), createNovel(), updateNovel()}

// stores/chapterStore.ts
{chapters, pendingReviewCount, fetchChapters(), approveChapter()}

// stores/taskStore.ts
{tasks, runningTasks, fetchTasks(), subscribeTaskUpdates()}
```

### 6.4 组件拆分

- 页面级组件：`pages/Dashboard.tsx`
- 业务组件：`components/NovelCard.tsx`, `components/ChapterEditor.tsx`
- 通用组件：`components/common/DataTable.tsx`, `components/common/StatCard.tsx`
- 布局组件：`components/layout/Sidebar.tsx`, `components/layout/Header.tsx`

---

## 七、部署架构

### 7.1 Docker Compose 配置

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: xxx
      MYSQL_DATABASE: fqxs
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  django:
    build: ./backend
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      - mysql
      - redis

  fastapi:
    build: ./llm_service
    command: uvicorn main:app --host 0.0.0.0 --port 8001
    volumes:
      - ./llm_service:/app
    ports:
      - "8001:8001"

  celery_worker:
    build: ./backend
    command: celery -A config worker -l info
    volumes:
      - ./backend:/app
    depends_on:
      - redis
      - mysql

  celery_beat:
    build: ./backend
    command: celery -A config beat -l info
    volumes:
      - ./backend:/app
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
```

### 7.2 环境变量

```env
# Django
SECRET_KEY=xxx
DEBUG=False
DATABASE_URL=mysql://root:xxx@mysql:3306/fqxs
REDIS_URL=redis://redis:6379/0

# FastAPI
FASTAPI_URL=http://fastapi:8001

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

---

## 八、里程碑与验收标准

### MVP 阶段（2-3 周）

**必做任务**：
1. 基础架构搭建（Django + FastAPI + React + Docker）
2. 数据模型与迁移
3. 认证系统（JWT）
4. LLM Provider 管理
5. 创意采集（Scrapy + Celery）
6. 小说项目管理
7. 章节生成核心流程
8. 章节审核工作台

**完成判定**：
- ✅ 能手动触发爬虫并看到创意列表
- ✅ 能创建小说项目并生成大纲
- ✅ 能自动生成章节并在前端审核编辑
- ✅ 审核通过的章节能标记为待发布

### Beta 阶段（1-2 周）

**新增任务**：
9. 自动化循环（每日定时生成）
10. 数据统计模块（Dashboard + ECharts）
11. 任务监控（WebSocket 实时状态）
12. 章节阅读数据同步
13. 成本统计

**完成判定**：
- ✅ 系统能每天自动为 3-5 本书生成章节
- ✅ Dashboard 能看到生成趋势、成本、任务状态
- ✅ 能查看每本书的阅读量数据

### 上线优化阶段（1-2 周）

**新增任务**：
14. 番茄小说发布集成（Beta 版本）
15. 错误处理与日志
16. 性能优化
17. 备份与恢复
18. 部署文档

**完成判定**：
- ✅ 系统连续运行 7 天无崩溃
- ✅ 能通过后台触发发布到番茄小说
- ✅ 有完整的日志和监控
- ✅ 有备份恢复方案

---

## 九、风险控制

### 9.1 反爬策略
- 代理 IP 池（轮换使用）
- 随机 User-Agent
- 请求频率控制（< 1 次/秒）
- 随机延迟（2-5 秒）

### 9.2 成本控制
- LLM 调用失败重试上限（3 次）
- Token 消耗监控与告警
- 按 Provider 优先级降级

### 9.3 合规约束
- 所有 AI 内容必须人工审核
- 发布前二次确认
- 操作日志完整记录

---

## 十、后续扩展

### 10.1 可选功能（按需开发）
- 多用户支持（RBAC 权限）
- 内容质量评分（AI 自评）
- 数据反馈迭代（根据阅读量调整风格）
- 移动端适配
- 微信/邮件通知

### 10.2 技术债务
- MongoDB 集成（创意/日志存储）
- 分布式任务队列（Celery 集群）
- 前端性能优化（虚拟滚动、懒加载）
- 单元测试覆盖率（目标 80%）

---

**文档版本**: v1.0  
**最后更新**: 2026-04-03  
**负责人**: Claude (Planner)
