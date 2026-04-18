# fqxs 创作平台迭代执行计划

> 基于以下文档整理：
> - `docs/superpowers/specs/2026-04-14-fqxs-creative-platform-plan.md`
> - `docs/superpowers/specs/2026-04-14-workspace-redesign.md`
> - `docs/requirements.md`
> - `docs/llm_integration.md`

## 概览

**目标**

把 `fqxs` 从“自动化生产平台”推进到“创作平台 + 生产平台”的双核心形态，但不复制 `PlotPilot` 的代码结构，而是吸收三个核心能力：

- 创作对象领域化
- 写作上下文系统化
- 生成结果资产化

**当前判断**

现有仓库已经具备第一阶段落地的基础：

- 前端已有 `HomePage`、`WorkspacePage`、`ChapterSidebar`、`WritingCenter`、`SettingsPanel`
- Django 已有 `novels`、`chapters`、`tasks`、`publishing`、`stats` 基础模块
- FastAPI 已有 `ws_chapter.py`、`llm_client.py`、`prompt_builder.py`、`llm_provider_manager.py`
- 现有 6 步建书向导和 WebSocket 流式设定生成能力已经可复用

因此这次迭代不应从“重写系统”开始，而应按依赖顺序做增量演进。

## 需求摘要

### 要解决的问题

- 现有系统更像“任务 + 生成接口 + 发布链路”的自动化平台，不足以支撑长篇创作
- 章节生成仍偏临时拼 prompt，缺少统一上下文包
- 生成结果大多停留在正文文本，缺少摘要、事实、伏笔、风格等可复用资产
- 工作台主流程尚未彻底统一，前后端职责边界还不够清晰

### 本轮范围

- 统一工作台主流程
- 统一章节状态与 WebSocket 写作协议
- 补齐创作资产模型和初始化链路
- 建立规则型上下文引擎 V1
- 引入章节后处理与质量分析骨架

### 明确不做

- 不先做向量数据库和语义检索
- 不做 DDD 式大规模架构重写
- 不一次性删除所有旧页面
- 不恢复“自动定时写作”作为主流程
- 不把人工发布替换为自动发布

### 成功标准

- 用户可在统一工作台完成建书、写作、查看设定、查看知识、发布章节
- 新生成章节默认进入 `draft`，不再依赖人工审核状态流
- 章节生成默认走上下文引擎
- 每章生成后可沉淀摘要、事实、伏笔和生成元数据
- 登录、Provider 管理、统计、任务、发布等现有平台能力不回退

### 关键约束

- 兼容优先，迁移以新增字段和新增表为主
- 发布前仍保留人工干预
- 限频与合规策略不能被新工作流绕过
- 外部模型调用继续复用现有 Provider 管理和 fallback 逻辑

### 关键假设

- `WorkspacePage` 继续作为唯一创作页
- Django 继续作为创作资产主库，FastAPI 不持久化业务主数据
- 第一版上下文引擎采用规则检索，不引入新基础设施
- 现有 `NovelDraft -> complete -> NovelProject` 流程可以作为建书初始化入口

## 架构方向

### 总体方法

采用“契约先行 + 主链路优先 + 资产逐步补齐”的迭代方式：

1. 先稳定工作台主链路与接口契约
2. 再沉淀创作资产和后处理链路
3. 然后把上下文引擎接入生成入口
4. 最后补齐分析能力和高级自动化

### 模块职责

**Frontend**

- 只保留一个创作主页面：`frontend/src/pages/Dashboard/WorkspacePage.tsx`
- 将工作台状态与首页书库状态彻底拆分
- 流式文本、日志、当前运行状态独立维护并支持恢复

**Django**

- 作为项目、设定、章节、创作资产、发布记录的主存储层
- 提供工作台聚合接口和资产 CRUD
- 负责初始化、持久化、统计、权限、审计

**FastAPI**

- 作为统一写作入口和流式输出入口
- 负责 prompt 组装、上下文拼装、后处理分析任务触发
- 负责与 LLM Provider 的任务类型路由

**Celery**

- 处理章节生成后的摘要、事实、伏笔、风格、一致性等后处理任务
- 保留发布相关任务
- 不再把“定时自动生成章节”作为主工作流

**Data**

- 在现有 `NovelProject`、`NovelSetting`、`Chapter` 上做兼容扩展
- 新增少量创作资产表，优先围绕工作台展示和上下文引擎需要的数据建模

### 目标数据流

`灵感建书 -> 6 步向导 -> complete 初始化项目资产 -> 进入 Workspace -> WebSocket 生成章节 -> 保存为 draft -> 触发后处理 -> 回写摘要/事实/伏笔/质量信息 -> 人工发布`

## 分阶段执行计划

### 阶段 0：接口契约与状态收口

**目标**

先统一枚举、接口、事件协议，避免前后端并行改造时反复返工。

**动作**

- 确认章节状态只保留 `generating` / `draft` / `published` / `failed`
- 确认 WebSocket 事件协议：`status` / `chunk` / `log` / `done` / `error`
- 定义工作台聚合接口 `GET /api/workbench/<project_id>/context/`
- 统一 LLM task type 命名：`setting`、`outline`、`chapter`、`continue`、`summary`、`fact_extraction`、`style_analysis`、`consistency_analysis`
- 定义 `Chapter.generation_meta` 和 `context_snapshot` 的最小 schema

**落点**

- `backend/apps/chapters/models.py`
- `backend/apps/chapters/views.py`
- `backend/apps/novels/views.py`
- `fastapi_service/routers/ws_chapter.py`
- `fastapi_service/services/llm_provider_manager.py`
- `frontend/src/pages/Dashboard/constants.ts`
- `frontend/src/api/chapters.ts`
- `frontend/src/api/novels.ts`

**交付物**

- 工作台接口契约文档
- 状态机和 WebSocket 协议文档
- 前后端统一状态枚举

**验收**

- 前后端不再出现 `pending_review` 和 `approved`
- WebSocket 事件名和字段固定
- 工作台初始化不需要十几个散请求

### 阶段 1：统一工作台主流程

**目标**

把 `WorkspacePage` 真正收敛成唯一创作页，并打通“生成 -> draft -> 发布”。

**动作**

- 以 `docs/superpowers/specs/2026-04-14-workspace-redesign.md` 为准完成三栏布局
- 拆分并稳定 `ChapterSidebar`、`WritingCenter`、`SettingsPanel`
- 完善 `useChapterStream`，让流式文本、日志、运行状态按项目维度隔离
- 增加 `WorkspaceTopBar` 所需聚合数据
- Django 提供工作台上下文聚合接口
- FastAPI `ws/generate-chapter` 统一成为章节生成入口
- 章节生成完成后直接保存为 `draft`
- 保留人工发布，不再引入人工审核状态流

**落点**

- `frontend/src/pages/Dashboard/WorkspacePage.tsx`
- `frontend/src/pages/Dashboard/ChapterSidebar.tsx`
- `frontend/src/pages/Dashboard/WritingCenter.tsx`
- `frontend/src/pages/Dashboard/SettingsPanel.tsx`
- `frontend/src/hooks/useChapterStream.ts`
- `backend/apps/novels/views.py`
- `backend/apps/chapters/views.py`
- `fastapi_service/routers/ws_chapter.py`
- `backend/celery_tasks/ai_tasks.py`
- `backend/celery_tasks/publish_tasks.py`

**交付物**

- 单一工作台主页面
- 工作台聚合接口
- 章节 WebSocket 写作链路
- 生成后入库 `draft`

**依赖**

- 阶段 0 完成接口契约

**验收**

- 用户从建书完成后可以直接进入工作台写作
- 工作台可实时看到文本流和日志流
- 新生成章节自动进入 `draft`
- `publishChapter` 流程保持可用

### 阶段 2：创作资产建模与初始化

**目标**

把建书和生成结果从“文本结果”升级为“结构化创作资产”。

**动作**

- 固化 `NovelSetting.structured_data` schema，并记录 `source`
- 扩展 `Chapter`：`context_snapshot`、`summary`、`open_threads`、`consistency_status`、`generation_meta`
- 新增 `Storyline`
- 新增 `PlotArcPoint`
- 新增 `ChapterSummary`
- 新增 `KnowledgeFact`
- 新增 `ForeshadowItem`
- 新增 `StyleProfile`
- 在 `Draft.complete` 或 `complete-wizard` 时初始化故事线、情节弧、知识节点
- 在章节写入后挂上后处理任务链入口

**落点**

- `backend/apps/novels/models.py`
- `backend/apps/chapters/models.py`
- `backend/apps/novels/views.py`
- `backend/apps/novels/serializers.py`
- `backend/apps/chapters/serializers.py`
- `backend/celery_tasks/ai_tasks.py`
- 新增 app 或在现有 app 内新增模块：
  - `backend/apps/storylines/`
  - `backend/apps/knowledge/`
  - `backend/apps/foreshadowing/`
  - `backend/apps/style_profiles/`

**交付物**

- 一组兼容式 migration
- 建书完成后的资产初始化逻辑
- 章节生成后的后处理任务入口

**依赖**

- 阶段 1 工作台链路可用

**验收**

- 用户建书完成后，工作台右侧设定、故事线、基础知识视图不为空
- 任一步骤重新生成不覆盖其他人工编辑结果
- 每章至少可看到摘要和开放线索字段

### 阶段 3：上下文引擎 V1

**目标**

让章节生成默认依赖结构化上下文包，而不是临时拼提示词。

**动作**

- Django 提供项目级资产查询服务，而不是把查询逻辑散落在 view 中
- FastAPI `prompt_builder` 升级为真正的上下文组装层
- 规则型上下文包至少包含：
  - 项目元信息
  - 当前章节目标
  - 最近 3 到 5 章摘要
  - 相关设定摘要
  - 相关角色与地点
  - 当前故事线状态
  - 当前张力目标
  - 相关伏笔项
  - 风格约束
- `ws/generate-chapter`、`continue-chapter` 全部改走上下文引擎
- 将最终上下文快照写入 `Chapter.context_snapshot`

**落点**

- `backend/apps/novels/views.py`
- `backend/apps/chapters/views.py`
- `fastapi_service/services/prompt_builder.py`
- `fastapi_service/services/llm_client.py`
- `fastapi_service/services/llm_provider_manager.py`
- `fastapi_service/routers/ws_chapter.py`

**交付物**

- `getWorkbenchContext(projectId)` 所需资产查询能力
- 可复用的上下文包 builder
- 章节生成默认上下文快照

**依赖**

- 阶段 2 产出的摘要、事实、伏笔等资产可查询

**验收**

- 所有章节生成入口均不再直接拼散 prompt
- 可在数据库中看到生成时上下文快照
- 最近章节摘要和关键设定能稳定进入生成输入

### 阶段 4：分析与质量能力

**目标**

让每一章生成后都有“可检查、可追踪、可提示”的质量层。

**动作**

- 增加章节摘要分析接口
- 增加事实抽取接口
- 增加风格偏移分析接口
- 增加一致性检查接口
- 将结果写回 Django 资产表
- 在右侧面板逐步展示：
  - 章节摘要
  - 开放线程
  - 知识事实
  - 伏笔账本
  - 风格风险
  - 一致性风险

**落点**

- `fastapi_service/routers/ai_generate.py`
- `fastapi_service/services/llm_client.py`
- `backend/apps/chapters/views.py`
- `backend/apps/stats/views.py`
- `backend/celery_tasks/ai_tasks.py`
- `frontend/src/pages/Dashboard/SettingsPanel.tsx`
- `frontend/src/components/charts/InsightGraph.tsx`

**交付物**

- 摘要、事实、风格、一致性分析接口
- 后处理任务链
- 工作台分析面板

**依赖**

- 阶段 3 的上下文引擎和数据资产已可用

**验收**

- 生成一章后可看到摘要、事实和风险提示
- 一致性检查结果可在发布前查看
- 风格分析只提示，不自动阻断发布

### 阶段 5：高级自动化与优化

**目标**

在主链路稳定后，再逐步恢复更强的自动化能力。

**动作**

- 增加 `continue-chapter`
- 引入半自动续写模式
- 评估多书并发写作调度
- 评估章节摘要、设定块、知识事实的语义检索
- 引入成本、质量、耗时的闭环指标

**落点**

- `fastapi_service/routers/ws_chapter.py`
- `fastapi_service/services/llm_provider_manager.py`
- `backend/apps/tasks/`
- `backend/apps/stats/`
- `backend/celery_tasks/`

**交付物**

- 半自动续写能力
- 多书并发运行策略
- 检索增强和成本质量报表

**依赖**

- 前 4 个阶段完成并稳定

**验收**

- 自动化能力是对创作主流程的增强，不会反客为主
- 新增自动化不会绕过人工发布和合规约束

## 推荐实施节奏

### 里程碑 M1：主工作台跑通

建议先只做：

- 阶段 0
- 阶段 1
- 阶段 2 中最小建模集：`Storyline`、`ChapterSummary`、`KnowledgeFact`

**结果**

先让用户可稳定地在一个工作台内完成建书、写作、查看设定、发布。

### 里程碑 M2：上下文驱动写作

建议在 M1 稳定后做：

- 阶段 2 剩余建模
- 阶段 3

**结果**

生成质量开始明显提升，上下文能力成为默认入口。

### 里程碑 M3：质量闭环

最后做：

- 阶段 4
- 阶段 5 中非基础设施重依赖部分

**结果**

平台从“能写”升级为“能持续稳定地写”。

## 首个 Sprint 建议

如果你现在就要开始做，我建议第一周只做这 8 件事：

1. 整理章节状态枚举，彻底删掉前端对 `pending_review` / `approved` 的依赖
2. 定义 `GET /api/workbench/<project_id>/context/` 返回结构
3. 清理 `WorkspacePage`，只保留章节列表、写作中心、右侧设定面板
4. 稳定 `useChapterStream` 的项目级连接管理
5. 固化 `ws/generate-chapter` 的消息协议
6. 让章节生成完成后统一落为 `draft`
7. 为 `Chapter` 增加 `generation_meta` 和 `context_snapshot`
8. 为章节生成后挂一个最小后处理任务，只先产出 `ChapterSummary`

这 8 件事做完，后面所有创作资产和上下文引擎都有稳定落点。

## 风险与应对

| 风险 | 影响 | 概率 | 应对 |
|------|------|------|------|
| 前后端同时改工作台导致返工 | 高 | 高 | 先冻结接口契约和状态枚举，再并行开发 |
| `novels/views.py` 和 `chapters/views.py` 继续膨胀 | 高 | 高 | 新逻辑先抽 service，再让 view 只负责编排 |
| 新资产表过多导致建模过重 | 中 | 中 | 先上最小资产集，后续按工作台展示需要逐步加表 |
| 流式生成与入库状态不一致 | 高 | 中 | 使用任务日志 ID 或 request ID 贯穿写作链路，保存逻辑幂等化 |
| Provider 成本和时延不可控 | 中 | 中 | 继续复用 task type 路由、fallback、超时和日志 |
| 合规和人工发布链路被新流程绕开 | 高 | 低 | 明确所有生成结果默认 `draft`，发布动作单独保留 |

## 测试与验收建议

### Django

- 新增模型 migration 测试
- 工作台聚合接口集成测试
- 建书完成后的资产初始化测试
- 发布前一致性数据读取测试

### FastAPI

- WebSocket 章节生成协议测试
- prompt builder 上下文包组装测试
- 摘要/事实/一致性分析接口测试
- Provider fallback 与超时测试

### Frontend

- `WorkspacePage` 交互测试
- `useChapterStream` Hook 状态恢复测试
- 工作台聚合接口加载测试
- 章节状态标签与发布入口回归测试

### 回归重点

- 草稿建书流程不退化
- 发布功能不退化
- Provider 管理不退化
- 统计页面和任务页面不退化

## 结论

这次迭代不该被理解为“把 `fqxs` 改得更复杂”，而应理解为：

- 用统一工作台把创作主链路收口
- 用结构化资产把长期写作能力沉淀下来
- 用上下文引擎把生成质量稳定下来

真正的执行顺序应该是：

`先主流程，后资产；先规则引擎，后检索增强；先人工可控，后高级自动化。`
