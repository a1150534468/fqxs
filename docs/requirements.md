# 需求与设计文档

> 本文档整合了项目系统设计文档和设计规范，所有需求以此为基准。

## 一、项目总览

### 1.1 目标
构建单用户番茄小说自动化创作平台，实现**创意采集 → 多书并行写作 → 人工审核发布**的全流程自动化。

### 1.2 核心约束
- 单用户使用，功能完整性优先
- 多书并行更新（3-5 本书同时维护）
- 自动生成内容，仅发布环节人工确认
- LLM 服务可配置多 Provider（创意生成 vs 章节写作）

### 1.3 技术栈
- **前端**: React 18 + TypeScript + Vite + Zustand + Ant Design + ECharts
- **后端**: Django 4.2 + DRF + Celery + Redis
- **生成服务**: FastAPI + 多 LLM Provider 适配层
- **数据库**: MySQL（主库）+ Redis（缓存/队列）
- **部署**: Docker Compose

### 1.4 里程碑
- **MVP**: 创意采集 + 手动触发生成 + 人工审核
- **Beta**: 自动化循环 + 数据统计看板
- **上线优化**: 半自动发布 + 稳定性优化

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

## 三、数据模型

### 3.1 核心表结构

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| User | 用户表 | username, email, password, is_staff |
| LLMProvider | LLM 服务配置 | user_id, name, provider_type, api_url, api_key, task_type, priority |
| Inspiration | 创意表 | source_url, title, synopsis, tags, hot_score, rank_type, is_used |
| NovelProject | 小说项目表 | user_id, inspiration_id, title, genre, synopsis, outline, status, target_chapters, current_chapter |
| Chapter | 章节表 | project_id, chapter_number, title, raw_content, final_content, word_count, status, published_at |
| Task | 任务表 | task_type, related_type, related_id, status, celery_task_id, params, result, error_message |
| Stats | 统计表 | date, metric_type, metric_data |

### 3.2 状态流转

```
Inspiration: collected → used
NovelProject: active ←→ paused → completed/abandoned
Chapter: generating → pending_review → approved → published
         ↓ (失败)
       failed → (可重新生成)
Task: pending → running → success/failed
```

---

## 四、API 接口

### 4.1 认证
- `POST /api/users/login/` - 登录
- `POST /api/users/refresh/` - 刷新 Token
- `GET /api/users/me/stats/` - 用户统计

### 4.2 创意管理
- `GET /api/inspirations/` - 创意列表（分页）
- `POST /api/inspirations/` - 创建创意
- `GET/PATCH/DELETE /api/inspirations/<id>/`
- `POST /api/inspirations/bulk-mark-used/` - 批量标记

### 4.3 项目管理
- `GET /api/novels/` - 项目列表（支持 status/genre/search/时间范围过滤）
- `POST /api/novels/` - 创建项目
- `GET/PATCH/DELETE /api/novels/<id>/`

### 4.4 章节管理
- `GET /api/chapters/` - 章节列表（支持 project_id/publish_status/search 过滤）
- `POST /api/chapters/` - 创建章节
- `GET/PATCH/DELETE /api/chapters/<id>/`
- `POST /api/chapters/generate-async/` - Celery 异步生成章节

### 4.5 任务管理
- `GET /api/tasks/<task_id>/status/` - 查询 Celery 任务状态及关联后端任务元数据

### 4.6 AI 生成（FastAPI）
- `POST /api/ai/generate/outline` - 生成大纲
- `POST /api/ai/generate/chapter` - 生成章节
- `POST /api/ai/continue` - 内容续写

### 4.7 错误码
| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 202 | 已接受（异步任务） |
| 204 | 删除成功 |
| 400 | 参数错误 |
| 401 | 未认证 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

---

## 五、前端设计

### 5.1 页面路由

```
/login                    - 登录页
/dashboard                - 数据看板（首页）
/inspirations             - 创意库
/novels                   - 小说项目列表
/novels/:id               - 单个小说详情
/novels/:id/chapters      - 章节列表
/novels/:id/chapters/create     - 创建章节
/novels/:id/chapters/:id/edit   - 编辑章节
/novels/:id/chapters/:id/preview - 预览章节
/tasks                    - 任务监控
/stats                    - 数据统计报表
/settings                 - 系统设置
```

### 5.2 核心页面设计

**Dashboard**: 统计卡片（项目数、章节数、总字数、今日新增）+ ECharts 趋势图
**章节编辑**: Markdown 编辑器 + 实时字数统计 + 人工审核提示（>15% 修改率）

### 5.3 状态管理
- Zustand: 全局状态
- React state: 局部状态
- Axios: HTTP 客户端（统一请求拦截器）

---

## 六、自动化流程

### 6.1 Celery Beat 定时任务

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

### 6.2 风控策略

- **爬虫风控**: 代理 IP 池、User-Agent 轮换、频率控制 <1次/秒、随机延迟 2-5 秒
- **内容风控**: 人工审核强制要求（>15% 修改率）
- **发布风控**: 发布频率限制、动态参数处理

---

## 七、部署架构

### 7.1 Docker Compose 服务

| 服务 | 端口 | 说明 |
|------|------|------|
| MySQL | 3306 | 数据库 |
| Redis | 6379 | 缓存/队列 |
| Django | 8000 | REST API |
| FastAPI | 8001 | AI 生成服务 |
| Celery Worker | - | 异步任务 |
| Celery Beat | - | 定时调度 |
| Flower | 5555 | Celery 监控 |
| Frontend | 5173 | React 开发服务 |

---

## 八、里程碑与验收标准

### MVP 阶段
- ✅ 手动触发爬虫并看到创意列表
- ✅ 能创建小说项目并生成大纲
- ✅ 能自动生成章节并在前端审核编辑
- ✅ 审核通过的章节能标记为待发布

### Beta 阶段
- ✅ 系统每天自动为多本书生成章节
- ✅ Dashboard 能看到生成趋势、成本、任务状态
- ✅ 能查看每本书的阅读量数据

### 上线优化阶段（待完成）
- ⏳ 番茄小说发布集成
- ⏳ 系统连续运行 7 天无崩溃
- ⏳ 完整的日志和监控
- ⏳ 备份恢复方案

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
