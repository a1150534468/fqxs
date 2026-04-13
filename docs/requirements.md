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
| NovelProject | 小说项目表 | user_id, inspiration_id, title, genre, synopsis, outline, status, target_chapters, current_chapter, **wizard_completed**, **wizard_step** |
| NovelSetting | 小说设定表 | project_id, setting_type(worldview/characters/map/storyline/plot_arc/opening/dimension_framework/main_characters/map_system/main_sub_plots/plot_extraction), title, content, structured_data(JSON), ai_generated, order |
| Chapter | 章节表 | project_id, chapter_number, title, raw_content, final_content, word_count, status, published_at |
| Task | 任务表 | task_type, related_type, related_id, status, celery_task_id, params, result, error_message |
| Stats | 统计表 | date, metric_type, metric_data |

### 3.2 状态流转

```
Inspiration: collected → used
NovelProject: active ←→ paused → completed/abandoned
              wizard_completed: false → true (向导完成后)
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
- `POST /api/ai/generate/setting` - 生成小说设定（世界观/人物/地图/故事线/情节弧）

### 4.7 向导式建书
- `POST /api/novels/<id>/generate-setting/` - AI 生成指定类型的设定
- `POST /api/novels/<id>/wizard-step/` - 保存向导单步数据到 NovelSetting
- `GET /api/novels/<id>/settings/` - 获取项目所有设定
- `POST /api/novels/<id>/complete-wizard/` - 完成向导，标记 wizard_completed

### 4.8 数据分析
- `GET /api/stats/overview/` - 首页概览（总书数、总章节、总字数、各状态书数、今日新增）
- `GET /api/stats/chapter-analytics/` - 章节级分析（支持 project_id 筛选）
- `GET /api/stats/character-graph/` - 角色关系图数据（nodes/links，从 NovelSetting 提取）
- `GET /api/stats/trend/` - 趋势数据（支持 metric_type 和 days 参数）
- `GET /api/stats/recent-generations/` - 最近 AI 生成记录
- `GET /api/stats/tasks-summary/` - 任务队列汇总

### 4.9 错误码
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
/                         - 书稿工作台（首页，独立全屏，双模式：home/workspace）
/inspirations             - 创意库
/novels                   - 小说项目列表
/novels/:id               - 单个小说详情
/novels/:id/chapters      - 章节列表
/novels/:id/chapters/create     - 创建章节
/novels/:id/chapters/:id/edit   - 编辑章节
/novels/:id/chapters/:id/preview - 预览章节
/tasks                    - 任务监控
/analytics                - 数据分析（统计面板 + 章节表 + 角色关系图）
/stats                    - 数据统计报表
/settings                 - 系统设置
```

### 5.2 核心页面设计

**书稿工作台 (Dashboard)**: 双模式全屏页面
- **Home 模式**: 渐变 Banner + 左侧数据概览（总书数/章节/字数）+ 新建书目（灵感输入 → 建档 → 12步向导）+ 我的书目（3列网格卡片）
- **Workspace 模式**: 三栏布局（左侧书库树 + 中央写作控制台 + 右侧知识图谱）

**新书设置向导**: 12步 AI 流水线 Modal 向导
- 步骤: 世界观 → 人物 → 地图 → 故事线 → 情节弧 → 开始 → 维度框架 → 主要角色 → 地图系统 → 主线支线 → 剧情抽离 → 进入工作台
- 前 11 步：进入每步时**自动触发 AI 生成**（调用 FastAPI），生成中显示 loading
- 用户审核/编辑 AI 输出，可从快速预设替换内容
- 点"下一步"保存当前步骤到 NovelSetting 并触发下一步生成
- 前序步骤已保存的内容作为上下文传递给后续步骤的 AI 生成
- 第 12 步"进入工作台"：展示所有 11 步设定总览，确认后调用 complete-wizard 进入 Workspace

**数据分析 (Analytics)**: 统计面板
- 顶部 Banner: 总字数、章节数、发布率、今日新增
- 章节数据表格（支持按项目筛选）
- 角色关系力导向图（ECharts graph）
- 7日趋势折线图

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
