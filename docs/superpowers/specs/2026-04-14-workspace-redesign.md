# Workspace 工作台重设计

**日期：** 2026-04-14  
**状态：** 待实现

---

## 1. 目标

重构 WorkspacePage，实现：
- 左侧：当前书目章节列表（无书库检索）
- 中间：写作调度中心（手动触发 + WebSocket 流式输出 + 实时日志）
- 右侧：6 步设定内容 Tab + 知识图谱
- 顶栏：书目概览数据
- 去掉所有人工审核逻辑，只保留人工发布
- 去掉定时任务，改为手动触发写作

---

## 2. 布局

```
┌─────────────────────────────────────────────────────────────────┐
│  顶栏：书名 · 总字数 · 完成章节/目标 · 完成率 · 均字数 · 最近更新    │
├──────────────┬──────────────────────────┬───────────────────────┤
│  左侧 (240px)│   中间 (flex-1)           │   右侧 (320px)        │
│              │                           │                       │
│  章节列表     │  写作调度中心              │  [世界观][角色][地图]  │
│  - 序号       │  ┌─────────────────────┐  │  [故事线][情节弧][开篇]│
│  - 标题       │  │ 启动写作  [▶]  [■]  │  │  ─────────────────   │
│  - 状态标签   │  │ 正在写第 N 章...     │  │  当前 tab 内容        │
│  - 字数       │  │ 流式文字输出区       │  │  (从向导设定渲染)     │
│              │  └─────────────────────┘  │  ═════════════════   │
│              │  实时日志面板             │  知识图谱              │
│              │  [21:10] 开始生成第N章    │  (ECharts 关系图)     │
│              │  [21:10] 调用 LLM...     │                       │
└──────────────┴──────────────────────────┴───────────────────────┘
```

---

## 3. 章节状态简化

去掉 `pending_review` 和 `approved`，只保留：

| 状态 | 含义 |
|------|------|
| `generating` | AI 正在写 |
| `draft` | 草稿，待人工发布 |
| `published` | 已发布 |
| `failed` | 生成失败 |

Django `generate_chapter_async` 任务完成后写 `draft`（原来是 `pending_review`）。

---

## 4. WebSocket 协议

**端点：** `ws://fastapi:8001/ws/generate-chapter`

### Client → Server
```json
{ "action": "start", "token": "<jwt>", "project_id": 123 }
{ "action": "stop" }
```

### Server → Client
```json
{"type": "status",  "message": "正在生成第 42 章..."}
{"type": "chunk",   "content": "文字片段"}
{"type": "log",     "message": "调用 LLM 完成", "timestamp": "21:10:05"}
{"type": "done",    "chapter_id": 99, "chapter_number": 42, "word_count": 2048}
{"type": "error",   "message": "..."}
```

---

## 5. 后端改动

### 5.1 FastAPI：新增 `routers/ws_chapter.py`
- 接收 `start` 消息，调用 `llm_client` 流式生成章节内容
- 每个 chunk 推 `{"type": "chunk", "content": "..."}` 给前端
- 关键节点推 `{"type": "log", ...}`
- 完成后调 Django REST API `POST /chapters/` 存库（status=`draft`）
- 推 `{"type": "done", ...}`
- 接收 `stop` 消息时中断生成

### 5.2 Django：views.py 清理
- `start-auto-generation`：只设 `auto_generation_enabled=True`，不再计算 `next_generation_time`
- `stop-auto-generation`：只清 `auto_generation_enabled=False`
- `generate_chapter_async` Celery 任务：生成完成后 status 改为 `draft`（原 `pending_review`）
- 删除 Celery beat 中的定时章节生成 schedule（`celery_tasks/` 中的 periodic task 配置）

### 5.3 Django：model 不做 migration
- `generation_schedule`、`next_generation_time` 字段保留，只是停止写入
- 不破坏现有数据和已有 migration

---

## 6. 前端改动

### 6.1 新 Hook：`useChapterStream`
```ts
// src/hooks/useChapterStream.ts
interface StreamState {
  isRunning: boolean;
  streamText: string;
  logs: { time: string; message: string }[];
  currentChapter: number | null;
  error: string | null;
}

// 管理多本书并发
const streams = useRef<Map<number, { ws: WebSocket; state: StreamState }>>()

function start(projectId: number): void
function stop(projectId: number): void
function getState(projectId: number): StreamState
```

- 每个 projectId 维护独立 WebSocket 连接
- 切换书只切换显示，不断开其他连接
- 组件卸载时关闭所有连接

### 6.2 WorkspacePage 拆分为 3 个子组件

**`ChapterSidebar`**（新文件）
- props: `chapters`, `selectedChapterId`, `onSelect`, `onPublish`
- 渲染章节列表：序号、标题、状态标签（generating/draft/published/failed）、字数
- 状态 `draft` 显示"发布"按钮，点击调 `publishChapter` API
- 无书库检索

**`WritingCenter`**（新文件）
- props: `novel`, `streamState`, `onStart`, `onStop`
- 顶部：启动/停止按钮，当前状态（空闲/运行中）
- 中间：流式文字输出区（`pre-wrap`，自动滚到底部）
- 底部：实时日志面板（最近 20 条，时间戳 + 消息）

**`SettingsPanel`**（新文件）
- props: `settings`, `knowledgeGraph`
- 上半部分：Tab 切换 6 步设定（世界观/角色/地图/故事线/情节弧/开篇），只读展示 `MDEditor.Markdown`
- 下半部分：知识图谱，ECharts 关系图（复用现有 `InsightGraph` 组件）

### 6.3 WorkspacePage 顶栏
- 展示：书名、总字数、`当前章节/目标章节`、完成率、平均字数、最近更新时间
- 从现有 `aggregatedStats` 和 `selectedNovel` 取数

### 6.4 删除逻辑
- 删除 `handleSaveChapter` 中 `approved` 状态的保存逻辑
- 删除 stageItems 中"人工审核"步骤
- `chapterStatusTag` 常量中去掉 `pending_review` 和 `approved`

---

## 7. 文件变动清单

| 操作 | 文件 |
|------|------|
| 新增 | `fastapi_service/routers/ws_chapter.py` |
| 修改 | `fastapi_service/main.py`（注册新 router） |
| 修改 | `backend/celery_tasks/ai_tasks.py`（status 改 draft） |
| 修改 | `backend/apps/novels/views.py`（清理调度逻辑） |
| 修改 | `backend/celery_tasks/` 删除 beat schedule |
| 新增 | `frontend/src/hooks/useChapterStream.ts` |
| 新增 | `frontend/src/pages/Dashboard/ChapterSidebar.tsx` |
| 新增 | `frontend/src/pages/Dashboard/WritingCenter.tsx` |
| 新增 | `frontend/src/pages/Dashboard/SettingsPanel.tsx` |
| 修改 | `frontend/src/pages/Dashboard/WorkspacePage.tsx`（大幅简化） |
| 修改 | `frontend/src/pages/Dashboard/constants.ts`（状态标签） |

---

## 8. 不在本次范围内

- 发布到番茄小说平台（已有 `publishChapter` API，只调用即可）
- 章节内容编辑（本次只读 + 发布）
- 写作历史/回滚
