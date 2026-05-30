# FQXS 写作工作台

基于当前代码实现的小说创作工作台。项目由 React 前端、Django API、FastAPI 生成服务、Celery 任务队列和 MySQL/Redis 组成，核心流程是：

`首页建档 -> 设定向导 -> 进入工作台 -> 章节生成/续写/重写 -> 审阅定稿 -> 发布`

## 当前产品形态

当前前端主路由只有两类：

- `/login`：登录页
- `/`：首页，负责书目总览、灵感建档入口、统计概览
- `/workspace/:novelId`：工作台，负责章节推进、正文编辑、右侧情报面板

首页的核心组件：

- `HomePage`：书目卡片、统计概览、建档入口
- `NewBookWizard`：建档向导弹窗
- `LLMConfigModal`：模型配置弹窗

工作台的核心组件：

- `ChapterSidebar`：左侧章节轨
- `WritingCenter`：中间正文与实时流
- `SettingsPanel`：右侧情报区

右侧情报区当前收敛为 6 个标签：

- `作品设定`
- `世界观`
- `知识库`
- `手稿道具`
- `质量守护`
- `故事演进`

其中旧版重复区域已经被合并：

- `审阅定稿` 合并进 `质量守护`
- `知识图谱` 合并进 `知识库`

## 建档向导

当前代码中的向导是“1 个建草稿入口 + 7 个步骤页 + 进入工作台”的实现，不是旧文档里的 12 步平台。

常量定义见 `frontend/src/pages/Dashboard/constants.ts`：

- `书名`
- `世界观`
- `人物`
- `地图`
- `故事线`
- `情节弧`
- `开始`
- `进入工作台`

草稿数据存储在 Django 的：

- `NovelDraft`
- `DraftSetting`

完成向导后会转换为：

- `NovelProject`
- `NovelSetting`

## 工作台能力

### 1. 章节流式写作

`WritingCenter` 支持三种动作：

- 单章生成
- 续写当前章
- 重写当前章

以及一种运行模式：

- 持续迭代到目标章节

前端通过 `useChapterStream` 连接 `ws://.../ws/generate-chapter`，可以显示：

- 实时流式正文
- 流程日志
- 连续生成进度
- 最近保存章节

### 2. 人工正文编辑

工作台支持：

- 自动把生成结果落为章节草稿
- 编辑 `final_content`
- 3 秒静默自动保存
- 上一章/下一章切换

### 3. 审阅与质量闸门

章节审阅记录存储在 `ChapterReview`，支持：

- `pending`
- `approved`
- `revise`

当前流程里有两个重要约束：

- 已定稿前需要先有审阅记录
- 发布前人工改稿率必须至少达到 `15%`

阈值定义在 `backend/apps/chapters/services/workflow.py` 的 `MIN_MANUAL_MODIFICATION_RATE = 15`

### 4. 章节资产与情报

`build_workbench_context()` 会把工作台所需的聚合数据一次性返回给前端，包括：

- `chapters`
- `settings`
- `chapter_summaries`
- `chapter_reviews`
- `storylines`
- `plot_arc_points`
- `knowledge_facts`
- `foreshadow_items`
- `chapter_asset_index`
- `style_profiles`
- `workbench_highlights`
- `knowledge_graph`

这些数据驱动右侧情报区的摘要、事实、伏笔、风格风险、故事线推进等内容。

## 技术架构

### 前端

- React 18
- TypeScript
- Vite
- React Router
- Ant Design
- `@uiw/react-md-editor`
- ECharts
- Zustand
- `react-resizable-panels`

### Django

职责：

- JWT 登录鉴权
- 草稿与小说项目 CRUD
- 工作台聚合接口
- 章节 CRUD、审阅、发布
- 统计与任务查询
- LLM Provider 配置

主要 URL 前缀：

- `/api/users/`
- `/api/inspirations/`
- `/api/workbench/`
- `/api/novels/`
- `/api/drafts/`
- `/api/chapters/`
- `/api/tasks/`
- `/api/stats/`
- `/api/llm-providers/`
- `/api/health/`

### FastAPI

职责：

- 设定生成
- 章节生成
- 章节续写
- 章节分析
- WebSocket 流式设定生成
- WebSocket 流式章节生成

主要入口：

- `POST /api/ai/generate/setting`
- `POST /api/ai/generate/chapter`
- `POST /api/ai/continue`
- `POST /api/ai/generate/book-titles`
- `POST /api/ai/analyze/*`
- `GET /health`
- `WS /ws/generate-setting`
- `WS /ws/generate-chapter`

### Celery

当前 Celery 入口文件是 `backend/celery_app.py`。

已配置导入：

- `celery_tasks.ai_tasks`
- `celery_tasks.crawl_tasks`
- `celery_tasks.stats_tasks`
- `celery_tasks.publish_tasks`

当前 Beat 计划：

- 每天 `02:00` 执行灵感抓取
- 每小时整点执行统计更新

### 数据库与缓存

- MySQL 8：默认数据库
- SQLite：`USE_SQLITE=True` 时可切到本地轻量模式
- Redis：Celery broker/result backend 与健康检查依赖

## 目录结构

```text
.
├── backend/
│   ├── apps/
│   │   ├── chapters/
│   │   ├── inspirations/
│   │   ├── llm_providers/
│   │   ├── monitoring/
│   │   ├── novels/
│   │   ├── publishing/
│   │   ├── stats/
│   │   ├── tasks/
│   │   └── users/
│   ├── config/
│   ├── celery_app.py
│   └── manage.py
├── fastapi_service/
│   ├── routers/
│   ├── services/
│   ├── models/
│   ├── prompts/
│   └── main.py
├── frontend/
│   ├── src/api/
│   ├── src/hooks/
│   ├── src/pages/Dashboard/
│   └── src/store/
├── docs/
└── docker-compose.yml
```

## Docker 启动

推荐直接使用 `docker compose`，当前编排服务包括：

- `mysql`
- `redis`
- `backend-init`
- `django`
- `fastapi`
- `celery-worker`
- `celery-beat`
- `frontend`

启动：

```bash
docker compose up -d --build
```

访问地址：

- 前端：`http://localhost:5173`
- Django：`http://localhost:8000`
- FastAPI：`http://localhost:8001`

默认管理员由 `create_admin` 命令自动创建：

- 用户名：`admin`
- 密码：`admin123`

## 本地开发

### 1. Django

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
USE_SQLITE=True python manage.py migrate
USE_SQLITE=True python manage.py create_admin
USE_SQLITE=True python manage.py runserver 0.0.0.0:8000
```

### 2. FastAPI

```bash
cd fastapi_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

### 4. Celery

```bash
cd backend
source .venv/bin/activate
celery -A celery_app worker -l info
celery -A celery_app beat -l info
```

## 环境变量

根目录 `.env.example` 已包含主要变量，当前最关键的是：

### Django / DB

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `USE_SQLITE`
- `MYSQL_*`
- `REDIS_URL`
- `FASTAPI_URL`

### FastAPI

- `FASTAPI_DEBUG`
- `FASTAPI_MOCK_GENERATION`
- `FASTAPI_LLM_API_URL`
- `FASTAPI_LLM_API_KEY`
- `FASTAPI_LLM_MODEL`
- `FASTAPI_DJANGO_API_URL`

### Frontend

- `VITE_API_BASE_URL`
- `VITE_FASTAPI_URL`
- `VITE_WS_URL`

## Mock 与真实生成

当前仓库默认更偏向“可跑起来”：

- `docker-compose.yml` 中 `FASTAPI_MOCK_GENERATION` 默认是 `True`
- FastAPI `/health` 会返回 `mock_generation`

这意味着：

- 没有可用 JWT 用户模型配置、也没有可用默认 API Key 时，系统会回落到 mock 生成
- 配好 `FASTAPI_LLM_API_KEY` 或给用户配置有效 `LLMProvider` 后，FastAPI 会优先走真实模型

## 已实现的关键接口

### 认证

- `POST /api/users/login/`
- `POST /api/users/refresh/`
- `GET /api/users/me/stats/`

### 小说与草稿

- `GET/POST /api/novels/`
- `GET/PATCH/DELETE /api/novels/:id/`
- `GET /api/workbench/:projectId/context/`
- `GET /api/workbench/:projectId/generation-context/`
- `POST /api/drafts/`
- `POST /api/drafts/:id/save-step/`
- `POST /api/drafts/:id/complete/`
- `POST /api/drafts/generate-book-titles/`

### 章节

- `GET/POST /api/chapters/`
- `PATCH /api/chapters/:id/`
- `POST /api/chapters/:id/review/`
- `POST /api/chapters/:id/publish/`
- `POST /api/chapters/generate-from-ws/`

### 统计与任务

- `GET /api/stats/overview/`
- `GET /api/stats/dashboard/`
- `GET /api/stats/trend/`
- `GET /api/stats/recent-generations/`
- `GET /api/stats/tasks-summary/`
- `GET /api/tasks/`
- `GET /api/tasks/:task_id/status/`

## 当前实现边界

以下内容在仓库里有模型、接口或雏形，但不应在对外文档中当成“完整成品”描述：

- 创意库、灵感采集、趋势生成相关能力存在后端接口，但不是当前前端主导航
- 自动生成开关与计划字段已存在，但当前工作台主路径仍以人工触发和 WebSocket 驱动为主
- 发布链路、异步任务、分析接口已经接好，但不同模块的 UI 完整度不一致
- 部分统计接口使用真实数据聚合，部分仍有 mock/fallback 行为

## 最近界面整理

本轮代码已经完成两类整理：

- 工作台中部正文、实时流、流程日志的滚动链修复
- 右侧情报区去重合并，统一为 6 个标签页

滚动修复主要通过以下方式实现：

- 父层级补齐 `flex` + `min-h-0`
- Tab 内容区使用独立 `overflow-y-auto`
- 中间与右栏都避免外层滚动吞掉内层滚动

## 验证

与这轮界面调整对应的代码验证状态：

- `frontend npm run build` 通过
- `frontend npm test -- WorkspacePage.test.tsx` 通过

文档补充本身不改变运行逻辑。
