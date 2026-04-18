# fqxs 创作平台迭代任务板

> 配套总计划：
> - `docs/superpowers/plans/2026-04-15-fqxs-creative-platform-iteration-plan.md`

## 说明

这份任务板不是重新写一遍方案，而是把总计划拆成可直接执行和分派的任务单。

拆分原则：

- 先收口接口和状态，再并行开发
- 先打通主链路，再补数据资产
- 先规则型上下文，再考虑检索增强
- 所有新能力都不能绕过人工发布

## 当前基线判断

从仓库现状看，以下内容已经有第一版，不应按从零开始排：

- `frontend/src/pages/Dashboard/WorkspacePage.tsx` 已有三栏框架
- `frontend/src/hooks/useChapterStream.ts` 已支持项目级流式连接
- `fastapi_service/routers/ws_chapter.py` 已有章节流式协议第一版
- `backend/apps/chapters/models.py` 已收口到 4 个章节状态
- `backend/apps/chapters/views.py` 已有 `generate-from-ws`
- `backend/celery_tasks/ai_tasks.py` 已把章节落库状态写成 `draft`

所以接下来任务重点不是“搭骨架”，而是“统一契约、补齐上下游、沉淀资产”。

## 里程碑拆分

### M1：主工作台跑通

目标：

- 工作台聚合接口可用
- `ws/generate-chapter` 稳定
- 生成章节默认 `draft`
- 人工发布链路保持可用

### M2：创作资产和上下文引擎跑通

目标：

- 建书完成后有结构化创作资产
- 章节生成默认使用上下文包
- 可记录上下文快照和生成元数据

### M3：质量闭环跑通

目标：

- 章节摘要、事实、伏笔、风格、一致性结果可见
- 右侧面板能展示创作资产和风险提示

## Wave 0：冻结契约

这一波必须先做，做完后其他线才允许并行推进。

### ARCH-01 工作台聚合接口契约

- 责任线：Django + 前端
- 目标：定义 `GET /api/workbench/<project_id>/context/` 返回结构
- 产出：
  - `project`
  - `stats`
  - `chapters`
  - `settings`
  - `knowledge_graph`
  - 预留 `storylines`、`chapter_summary`、`foreshadow_items`
- 依赖：无
- 完成标准：前端进入工作台时只依赖这一类聚合数据，不再散打十几个接口

### ARCH-02 WebSocket 事件协议冻结

- 责任线：FastAPI + 前端
- 目标：固定 `status` / `chunk` / `log` / `done` / `error` 的字段
- 产出：
  - `done` 必须包含 `chapter_id`、`chapter_number`、`word_count`
  - `error` 必须包含机器可读 message
  - `log` 必须包含时间戳
- 依赖：无
- 完成标准：`useChapterStream` 和 `ws_chapter.py` 对协议理解完全一致

### ARCH-03 Chapter 元数据最小 schema

- 责任线：数据库 + Django + FastAPI
- 目标：定义 `generation_meta`、`context_snapshot`、`summary`、`open_threads` 的最小字段结构
- 建议 schema：
  - `generation_meta`: `task_type` / `model` / `provider` / `latency_ms` / `input_tokens` / `output_tokens`
  - `context_snapshot`: `chapter_goal` / `recent_summaries` / `selected_settings` / `storyline_refs` / `foreshadow_refs`
- 依赖：无
- 完成标准：字段命名冻结，后续服务和前端按同一结构实现

## M1 任务板

### 前端线

#### FE-01 Workspace 数据源收口

- 文件：
  - `frontend/src/pages/Dashboard/WorkspacePage.tsx`
  - `frontend/src/api/novels.ts`
  - `frontend/src/pages/Dashboard/types.ts`
- 动作：
  - 改为优先消费 `workbench context` 聚合响应
  - 去掉工作台初始化的散接口拼装
  - 让 `selectedNovel`、`aggregatedStats`、`settings`、`knowledgeGraph` 从统一数据结构进入页面
- 依赖：ARCH-01
- 完成标准：工作台首屏只围绕聚合响应渲染

#### FE-02 WorkspaceTopBar 组件化

- 文件：
  - `frontend/src/pages/Dashboard/WorkspacePage.tsx`
  - 建议新增 `frontend/src/pages/Dashboard/WorkspaceTopBar.tsx`
- 动作：
  - 把顶部统计条从页面中拆出
  - 增加运行状态显示位
  - 为后续“后台写作指示器”留扩展口
- 依赖：FE-01
- 完成标准：页面骨架清晰，顶栏不再和三栏逻辑混在一起

#### FE-03 useChapterStream 稳定化

- 文件：
  - `frontend/src/hooks/useChapterStream.ts`
- 动作：
  - 明确 `start`、`stop`、`done`、`error` 的状态流转
  - 修复 `streamText` 依赖闭包旧值的风险
  - 增加 request/session 级标识，避免切书后消息串线
  - 保证完成后自动刷新章节列表和工作台上下文
- 依赖：ARCH-02
- 完成标准：切换书籍、重复启动、停止生成都不出现状态错乱

#### FE-04 工作台右侧面板分区

- 文件：
  - `frontend/src/pages/Dashboard/SettingsPanel.tsx`
  - `frontend/src/components/charts/InsightGraph.tsx`
- 动作：
  - 先保留“六步设定 + 知识图谱”
  - 明确后续 `摘要 / 故事线 / 伏笔 / 风格风险` 的插槽
  - 不在 M1 塞入过多新视觉逻辑
- 依赖：FE-01
- 完成标准：右侧面板可继续扩展，不需要二次重构结构

#### FE-05 状态和发布入口回归

- 文件：
  - `frontend/src/pages/Dashboard/constants.ts`
  - `frontend/src/pages/Dashboard/ChapterSidebar.tsx`
  - `frontend/src/api/chapters.ts`
- 动作：
  - 彻底确认前端只识别 `generating` / `draft` / `published` / `failed`
  - `draft` 章节展示发布按钮
  - `published` 和 `failed` 展示与交互逻辑统一
- 依赖：无
- 完成标准：状态标签、按钮、列表筛选全部一致

### Django 线

#### DJ-01 工作台聚合接口

- 文件：
  - `backend/apps/novels/views.py`
  - `backend/apps/novels/urls.py`
  - 视情况新增 service 模块
- 动作：
  - 新增 `GET /api/workbench/<project_id>/context/`
  - 聚合项目、统计、章节、设定、知识图谱
  - 避免把聚合逻辑继续堆进大型 view 方法，可优先抽 `services/workbench.py`
- 依赖：ARCH-01
- 完成标准：前端能仅靠一个接口恢复工作台主要信息

#### DJ-02 generation-status 收口

- 文件：
  - `backend/apps/novels/views.py`
- 动作：
  - `generation-status` 只保留主链路实际还在用的数据
  - 不再把 `next_generation_time`、定时调度类字段作为主流程展示核心
- 依赖：无
- 完成标准：接口语义和“手动触发写作”模式一致

#### DJ-03 generate-from-ws 增强

- 文件：
  - `backend/apps/chapters/views.py`
  - `backend/apps/chapters/serializers.py`
- 动作：
  - 接收 `generation_meta`、`context_snapshot` 等新字段
  - 章节保存后触发最小后处理任务
  - 保存逻辑幂等化，避免 WebSocket 重发导致脏数据
- 依赖：ARCH-03
- 完成标准：章节可稳定保存，并能携带最小生成元数据

#### DJ-04 View 拆 service

- 文件：
  - `backend/apps/novels/views.py`
  - `backend/apps/chapters/views.py`
  - 建议新增 `backend/apps/novels/services/`
  - 建议新增 `backend/apps/chapters/services/`
- 动作：
  - 把工作台聚合、向导初始化、章节保存编排逻辑逐步抽到 service
  - view 仅负责权限、参数和响应
- 依赖：DJ-01、DJ-03
- 完成标准：后续扩展上下文引擎时不继续堆胖 view

### FastAPI 线

#### FA-01 ws_chapter 协议对齐

- 文件：
  - `fastapi_service/routers/ws_chapter.py`
- 动作：
  - 对齐冻结后的事件协议
  - 给每轮生成加 request/session 标识
  - 明确 stop 行为是“中断当前生成”，不是关闭整个连接对象
- 依赖：ARCH-02
- 完成标准：前端流式体验稳定，日志和完成事件顺序清晰

#### FA-02 章节保存回调增强

- 文件：
  - `fastapi_service/routers/ws_chapter.py`
- 动作：
  - 回调 Django `generate-from-ws` 时带上 `generation_meta`
  - 统一错误处理和重试策略
  - 生成完成但保存失败时返回明确错误
- 依赖：ARCH-03、DJ-03
- 完成标准：生成链路结束时落库结果明确，不存在“前端看起来成功但数据库没写进去”

#### FA-03 llm_client 与 prompt_builder 边界收口

- 文件：
  - `fastapi_service/services/llm_client.py`
  - `fastapi_service/services/prompt_builder.py`
- 动作：
  - 在 M1 阶段先完成职责切分
  - `llm_client` 只负责调用和流式解析
  - `prompt_builder` 负责章节输入拼装
- 依赖：无
- 完成标准：M2 接上下文引擎时不需要再大改调用层

### 数据库线

#### DB-01 Chapter 兼容扩展 migration

- 文件：
  - `backend/apps/chapters/models.py`
  - `backend/apps/chapters/migrations/`
- 动作：
  - 新增 `generation_meta`
  - 新增 `context_snapshot`
  - 视需要新增 `summary`
  - 视需要新增 `open_threads`
- 依赖：ARCH-03
- 完成标准：字段可用且对老数据兼容

#### DB-02 ChapterSummary 最小表

- 文件：
  - 建议新增 `backend/apps/chapters` 子模型或单独 app
- 动作：
  - 先只建最小 `ChapterSummary`
  - 字段至少包含 `project`、`chapter`、`summary`、`key_events`、`open_threads`
- 依赖：无
- 完成标准：章节生成后可写入最小摘要资产

### 测试与验收线

#### QA-01 工作台集成回归

- 范围：
  - 登录 -> 选书 -> 进入工作台 -> 启动写作 -> 流式完成 -> 列表刷新 -> 发布
- 依赖：FE-01、DJ-01、FA-01、DJ-03
- 完成标准：主流程可以连通演示

#### QA-02 WebSocket 协议测试

- 范围：
  - 正常启动
  - 中途停止
  - 保存失败
  - token 失效
- 依赖：FA-01、FA-02
- 完成标准：异常路径都有稳定反馈

#### QA-03 Chapter migration 回归

- 范围：
  - 老章节数据可读
  - 新字段可空
  - 新生成章节能写 meta 和 snapshot
- 依赖：DB-01
- 完成标准：兼容迁移不破坏现有章节页

## M2 任务板

### 前端线

#### FE-11 工作台资产面板扩展

- 文件：
  - `frontend/src/pages/Dashboard/SettingsPanel.tsx`
- 动作：
  - 新增 `章节摘要`
  - 新增 `故事线`
  - 新增 `伏笔`
  - 新增 `知识事实`
- 依赖：DJ-11、DJ-12
- 完成标准：右侧面板能消费结构化创作资产

### Django 线

#### DJ-11 建书初始化链路

- 文件：
  - `backend/apps/novels/views.py`
  - `backend/apps/novels/models.py`
  - `backend/apps/novels/serializers.py`
- 动作：
  - 在 `Draft.complete` 或 `complete-wizard` 时初始化创作资产
  - 固定 `NovelSetting.structured_data` schema 和 `source`
- 依赖：DB-11、DB-12
- 完成标准：用户建书后进入工作台不再是空资产状态

#### DJ-12 工作台资产读接口

- 文件：
  - `backend/apps/novels/views.py`
  - 新增 storylines/knowledge/foreshadowing 读接口
- 动作：
  - 提供 `storylines`
  - 提供 `plot arcs`
  - 提供 `knowledge facts`
  - 提供 `foreshadow items`
- 依赖：DB-11、DB-12、DB-13
- 完成标准：工作台右侧新面板有稳定数据源

### FastAPI 线

#### FA-11 上下文包 builder V1

- 文件：
  - `fastapi_service/services/prompt_builder.py`
- 动作：
  - 把项目元信息、最近摘要、相关设定、故事线、伏笔拼成统一 payload
  - 先走规则检索，不接 embedding
- 依赖：DJ-12
- 完成标准：章节生成不再直接依赖零散 prompt 片段

#### FA-12 章节生成切换到上下文引擎

- 文件：
  - `fastapi_service/services/llm_client.py`
  - `fastapi_service/routers/ws_chapter.py`
- 动作：
  - `generate_chapter_stream` 接收完整上下文包
  - 生成完成后把快照写回 Django
- 依赖：FA-11、DJ-03
- 完成标准：数据库中能看到生成时使用的上下文快照

### 数据库线

#### DB-11 Storyline 与 PlotArcPoint

- 动作：
  - 新增 `Storyline`
  - 新增 `PlotArcPoint`
- 依赖：无
- 完成标准：建书初始化能落地故事线和情节弧

#### DB-12 KnowledgeFact 与 ForeshadowItem

- 动作：
  - 新增 `KnowledgeFact`
  - 新增 `ForeshadowItem`
- 依赖：无
- 完成标准：后处理和上下文引擎有可用数据表

#### DB-13 StyleProfile

- 动作：
  - 新增 `StyleProfile`
- 依赖：无
- 完成标准：为风格分析预留项目级基线

## M3 任务板

### 前端线

#### FE-21 风险可视化与质量提示

- 文件：
  - `frontend/src/pages/Dashboard/SettingsPanel.tsx`
  - `frontend/src/components/charts/InsightGraph.tsx`
- 动作：
  - 展示一致性冲突
  - 展示风格偏移风险
  - 展示伏笔状态和知识图谱增强视图
- 依赖：DJ-21、FA-21
- 完成标准：右侧面板从“只展示设定”升级到“辅助创作判断”

### Django 线

#### DJ-21 分析结果回写与读接口

- 文件：
  - `backend/apps/chapters/views.py`
  - `backend/apps/stats/views.py`
- 动作：
  - 提供章节摘要详情
  - 提供一致性检查结果读取
  - 提供风格分析结果读取
- 依赖：FA-21
- 完成标准：前端能读取分析结果，不必直接依赖 FastAPI

### FastAPI 线

#### FA-21 章节分析接口组

- 文件：
  - `fastapi_service/routers/ai_generate.py`
  - `fastapi_service/services/llm_client.py`
- 动作：
  - 新增 `chapter-summary`
  - 新增 `facts`
  - 新增 `style-drift`
  - 新增 `consistency`
- 依赖：M2 完成
- 完成标准：后处理任务链具备完整分析能力

### 数据库线

#### DB-21 质量分析结果字段补齐

- 文件：
  - `backend/apps/chapters/models.py`
  - 相关资产表
- 动作：
  - 增加 `consistency_status`
  - 视需要增加风险明细 JSON
- 依赖：FA-21
- 完成标准：分析结果可长期保存并用于统计

## 推荐并行方式

### 并行组 A

- ARCH-01
- ARCH-02
- ARCH-03

说明：这三项冻结后，其他开发线再开工。

### 并行组 B

- FE-01
- DJ-01
- FA-01
- DB-01

说明：这是 M1 的主体，彼此强相关，但可以并行推进。

### 并行组 C

- FE-03
- DJ-03
- FA-02
- QA-02

说明：这是“流式生成 + 入库 + 错误处理”的主风险区，建议作为一组联调。

### 并行组 D

- DB-11
- DB-12
- DB-13
- DJ-11
- DJ-12
- FA-11

说明：这是 M2 的上下文引擎准备阶段，可按“先建表，再补接口，再接 builder”推进。

## 推荐实际开工顺序

如果你现在准备直接开做，我建议严格按这个顺序：

1. `ARCH-01`、`ARCH-02`、`ARCH-03`
2. `DB-01`
3. `DJ-01`
4. `FE-01`
5. `FA-01`
6. `DJ-03`
7. `FA-02`
8. `FE-03`
9. `QA-01`、`QA-02`、`QA-03`
10. 然后再进入 M2

这样排的原因很简单：

- 不先冻结契约，前后端一定返工
- 不先扩 `Chapter` 字段，后面 meta 和 snapshot 没地方落
- 不先出 Django 聚合接口，前端工作台就还会继续拼装旧数据
- 不先把 WebSocket 到落库链路打稳，后面上下文引擎接进去只会放大问题

## 一句话分工建议

- 前端：收口工作台 UI、流式状态、右侧资产面板
- Django：提供聚合接口、落库编排、初始化逻辑、资产读取接口
- FastAPI：统一生成入口、上下文包拼装、分析接口
- 数据库：兼容扩展 `Chapter`，逐步增加创作资产表
- 测试：围绕“建书 -> 写作 -> draft -> 发布”做主链路回归
