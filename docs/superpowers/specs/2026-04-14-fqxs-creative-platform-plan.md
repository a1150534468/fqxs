# fqxs 创作平台演进总计划

**日期：** 2026-04-14  
**状态：** 待实施  
**适用项目：** `fqxs`  
**关联文档：**
- `docs/requirements.md`
- `docs/llm_integration.md`
- `docs/superpowers/specs/2026-04-14-workspace-redesign.md`

---

## 1. 计划目标

把 `fqxs` 从“番茄小说自动化生产平台”升级为“创作平台 + 生产平台”双核心系统。

目标不是照搬 `PlotPilot` 的技术实现，而是吸收它最有价值的能力：
- 把小说创作过程拆成明确的领域对象，而不是只围绕 CRUD 和生成接口组织代码
- 把“写作上下文构建”做成系统能力，而不是每次生成时临时拼 prompt
- 把“设定、一致性、伏笔、知识、风格”做成长期积累资产，而不是一次性生成结果
- 保留 `fqxs` 现有的业务工程优势：Django、任务系统、Provider 管理、发布链路、监控、账号体系

最终目标系统应同时满足两类诉求：
- 创作侧：更稳定地产出长篇内容，降低设定漂移、人物失真、剧情跑偏
- 平台侧：保留多书管理、任务调度、发布集成、统计与运维能力

---

## 2. 产品定位重定义

### 2.1 新定位

`fqxs` 的目标产品定义调整为：

> 一个面向单作者或小团队的 AI 长篇小说创作工作台，覆盖灵感采集、建书设定、结构规划、章节生成、知识沉淀、质量审查、人工发布和后续运营。

### 2.2 不再以此为主的定位

以下方向降级，不再作为架构主轴：
- 以“定时自动发文”为核心的流水线
- 以“创意采集和榜单爬虫”为主要卖点
- 以“章节生成接口数量”作为系统成熟度标准

### 2.3 应强化的卖点

- 写长篇时上下文不丢
- 角色、地点、设定、伏笔可持续追踪
- AI 写作可流式、可中断、可回放、可审计
- 写作和发布解耦，允许人工在最后一公里把关

---

## 3. 总体策略

### 3.1 保留的东西

- Django 作为主业务系统和主数据入口
- MySQL、Redis、Celery 作为基础设施
- 独立 FastAPI 服务承担 LLM 调用、流式生成、推理型接口
- React 前端工作台
- Provider 管理、JWT、发布链路、基础统计、监控能力

### 3.2 要新增的核心能力

- 创作领域模型：故事线、情节弧、设定资产、章节摘要、知识事实、伏笔账本、风格指纹
- 上下文引擎：章节生成前的结构化上下文组装
- 创作分析：一致性检查、人物状态漂移检测、风格漂移检测
- 工作台 BFF 载荷：一次请求拉齐写作所需全量侧边信息
- 生成后处理流水线：摘要提取、事实提取、知识更新、索引更新、质量扫描

### 3.3 要削弱或下线的能力

- 复杂定时自动生成调度
- 重度依赖人工审核状态机的写作主流程
- 与创作无关的过深页面分散

---

## 4. 目标架构

## 4.1 分层职责

### React 前端
- 提供统一书稿工作台
- 管理流式写作体验、设定浏览、知识图谱、章节列表、统计视图
- 不承担创作规则，只负责展示和交互

### Django
- 持有业务实体和主数据库模型
- 提供认证、权限、CRUD、发布、任务编排、工作台聚合接口
- 负责“创作资产”的长期存储

### FastAPI
- 负责 LLM 调用适配、流式 WebSocket、生成型接口、分析型接口
- 负责统一 Prompt 构建、Provider fallback、模型能力分流
- 负责把生成前后流程标准化

### Celery
- 只保留必要的异步任务：索引更新、摘要提取、知识抽取、统计刷新、采集任务
- 不再把“定时自动写作”作为主架构中心

### MySQL / Redis / 可选向量库
- MySQL 持久化主业务和创作资产
- Redis 承担任务队列、短期缓存、流式状态缓存
- 向量检索先设计为可插拔能力，可先用本地轻量实现，后续再接 Qdrant

---

## 5. 目标能力图谱

## 5.1 保留并升级

### 创意管理
- 保留现有灵感采集和项目转化链路
- 增加“灵感 -> 草稿 -> 正式项目”的资产映射

### 项目管理
- 保留 `NovelDraft`、`NovelProject`、`NovelSetting`
- 把“项目”从纯业务对象升级为“创作容器”

### 章节管理
- 保留 `Chapter` 的人工发布能力
- 强化生成前上下文、生成后分析、版本审计

### LLM Provider 管理
- 保留多 Provider、多 task type、优先级、连接测试
- 扩展到更多创作任务类型

## 5.2 新增

### 创作结构资产
- Storyline：主线、副线、角色线
- Plot Arc：关键转折、张力点、阶段目标
- Chapter Summary：章节摘要、开放线程、关键事件
- Narrative Fact：章节中稳定事实的结构化记录

### 创作质量资产
- Foreshadow Ledger：伏笔、线索、回收状态
- Style Profile：作品风格基线、角色声音锚点
- Consistency Report：冲突、风险、建议

### 工作台聚合能力
- 单次接口返回：
  - 章节列表
  - 当前书设定
  - 知识图谱
  - 章节摘要
  - 故事线/情节弧
  - 伏笔状态
  - 最近生成状态

### 上下文引擎
- 生成前自动抽取：
  - 本章目标
  - 相关角色
  - 相关地点
  - 近期剧情
  - 长期设定
  - 风格约束

---

## 6. 执行总原则

### 6.1 兼容优先

- 尽量复用现有 `NovelProject`、`NovelSetting`、`Chapter` 等表
- 对新增能力使用增量表和增量 API，不先大拆现有接口
- 允许旧页面和新工作台并存一个过渡期

### 6.2 先把写作闭环跑通，再做高级自动化

优先级顺序：
1. 统一工作台
2. 统一流式写作
3. 统一上下文构建
4. 统一生成后处理
5. 统一知识和质量分析
6. 再考虑自动续写和更复杂的调度

### 6.3 生成结果必须可沉淀

每次 AI 调用不只产生正文，还必须尽量留下：
- prompt 元信息
- provider/model 信息
- 摘要
- 结构化事实
- 风险报告

---

## 7. 详细工作流设计

## 7.1 建书工作流

### 目标

把“创建一本书”改造成真正的创作初始化流程，而不是单次表单提交。

### 执行方案

- 继续使用 `NovelDraft` 作为建书草稿容器
- 保留现有 6 步设定向导：
  - 世界观
  - 人物
  - 地图
  - 故事线
  - 情节弧
  - 开篇
- 每一步都同时产出两类数据：
  - 可读 Markdown 内容
  - 结构化 `structured_data`
- 在 `complete` 时，不只是复制设定，还要初始化：
  - 项目基础统计
  - 初始故事线记录
  - 初始情节弧记录
  - 初始知识图谱节点

### 验收标准

- 用户完成向导后，进入工作台时右侧设定、知识图谱、故事线不为空
- 任一步骤重新生成不会覆盖其他步骤的人工编辑结果

## 7.2 写作工作流

### 目标

将写作主流程统一成：

`选择项目 -> 进入工作台 -> 触发写作 -> 流式生成 -> 自动后处理 -> 草稿入库 -> 人工发布`

### 执行方案

- 工作台中部统一为 `WritingCenter`
- 写作入口仅保留：
  - 生成下一章
  - 重新生成当前章
  - 续写当前章
  - 停止生成
- 流式生成只走 FastAPI WebSocket
- Django 不直接生成正文，只负责：
  - 下发上下文所需项目元数据
  - 接收生成完成后的存储请求

### 生成状态标准化

章节状态统一为：
- `generating`
- `draft`
- `published`
- `failed`

取消：
- `pending_review`
- `approved`

### 验收标准

- 用户在工作台可实时看到文本流和日志流
- 生成结束后章节直接进入 `draft`
- 发布动作与生成动作完全解耦

---

## 8. 数据模型演进计划

## 8.1 保留并扩展现有模型

### `NovelProject`

保留现有字段，新增或扩展以下语义：
- `outline` 不再只是大纲文本，可作为项目级结构摘要
- `wizard_completed` 作为“建书完成”标记继续保留
- `auto_generation_enabled` 降级为可选能力，不作为主流程核心

### `NovelSetting`

继续作为“六步设定”的核心表，要求所有设定都具备：
- `setting_type`
- `title`
- `content`
- `structured_data`
- `ai_generated`
- `order`

新增要求：
- `structured_data` 的 schema 要固定并文档化
- 支持记录版本来源，如 `source="wizard" | "manual" | "regenerated"`

### `Chapter`

保留：
- `raw_content`
- `final_content`
- `generation_prompt`
- `llm_provider`
- `status`

新增建议字段：
- `context_snapshot`：生成时使用的上下文摘要
- `summary`：本章摘要
- `open_threads`：开放线索 JSON
- `consistency_status`：质量状态
- `generation_meta`：JSON，记录 model、token、耗时、任务类型

## 8.2 新增表

### `Storyline`

用途：
- 表示主线、副线、角色线、世界线

建议字段：
- `project`
- `name`
- `storyline_type`
- `status`
- `description`
- `estimated_chapter_start`
- `estimated_chapter_end`
- `priority`

### `PlotArcPoint`

用途：
- 记录关键剧情点和张力节点

建议字段：
- `project`
- `chapter_number`
- `point_type`
- `tension_level`
- `description`
- `related_storyline`

### `ChapterSummary`

用途：
- 存章节级摘要和后续检索基础

建议字段：
- `project`
- `chapter`
- `summary`
- `key_events`
- `open_threads`
- `consistency_note`

### `KnowledgeFact`

用途：
- 持久化章节抽取出的稳定事实

建议字段：
- `project`
- `chapter`
- `subject`
- `predicate`
- `object`
- `source_excerpt`
- `confidence`
- `status`

### `ForeshadowItem`

用途：
- 管理伏笔、线索、回收状态

建议字段：
- `project`
- `title`
- `description`
- `introduced_in_chapter`
- `expected_payoff_chapter`
- `status`
- `related_character`

### `StyleProfile`

用途：
- 保存作品级风格基线和角色声音样本

建议字段：
- `project`
- `profile_type`
- `content`
- `structured_data`

## 8.3 迁移原则

- 先新增表，不强改旧表主结构
- 旧数据允许为空
- Django migration 必须按“可回滚、可空字段、默认兼容”原则设计

---

## 9. 后端服务计划

## 9.1 Django 侧计划

### 新职责

- 作为创作资产主库
- 提供工作台聚合接口
- 提供章节、设定、故事线、情节弧、知识事实、伏笔等 CRUD 与读接口
- 管理发布、统计、权限、管理端行为

### 需要新增的 app 或模块

建议新增：
- `apps/storylines`
- `apps/knowledge`
- `apps/foreshadowing`
- `apps/style_profiles`

如不想新增太多 app，可先放入：
- `apps/novels`
- `apps/chapters`

但不建议长期把所有创作逻辑继续堆在 `novels/views.py` 中。

### 需要新增的接口

- `GET /api/workbench/<project_id>/context/`
- `GET /api/novels/<id>/storylines/`
- `GET /api/novels/<id>/plot-arcs/`
- `GET /api/novels/<id>/knowledge-facts/`
- `GET /api/novels/<id>/foreshadow-items/`
- `GET /api/chapters/<id>/summary/`

### 需要重构的接口

- `apps/novels/views.py`
  - 把设定生成、向导保存、知识图谱、工作台相关逻辑拆出 service
- `apps/chapters/views.py`
  - 把异步生成和写作状态逻辑拆出 service

## 9.2 FastAPI 侧计划

### 新职责

- 统一接收写作请求
- 统一做流式输出
- 统一做生成后结构化分析

### 需要补齐的能力

- `ws/generate-chapter`
- `ws/continue-chapter`
- `POST /api/ai/analyze/chapter-summary`
- `POST /api/ai/analyze/facts`
- `POST /api/ai/analyze/style-drift`
- `POST /api/ai/analyze/consistency`

### 需要重构的模块

- `services/llm_client.py`
  - 从“按接口散写 prompt”升级为“任务模板 + 结构化输入”
- `services/prompt_builder.py`
  - 成为真正的 prompt 组装层
- `services/llm_provider_manager.py`
  - 支持更多 task type：
    - `setting`
    - `outline`
    - `chapter`
    - `continue`
    - `summary`
    - `fact_extraction`
    - `style_analysis`
    - `consistency_analysis`

---

## 10. 上下文引擎计划

## 10.1 目标

让章节生成不再只依赖：
- 书名
- 类型
- 大纲片段

而是依赖结构化上下文包。

## 10.2 上下文包组成

每次生成章节前，构建统一 payload：

- 项目元信息
- 当前章节编号
- 当前章节目标
- 最近 3-5 章摘要
- 相关设定摘要
- 相关角色与地点
- 当前故事线状态
- 当前张力目标
- 已埋伏笔中与本章相关的项
- 风格约束

## 10.3 实施位置

- Django 提供项目资产查询
- FastAPI 负责把资产拼成最终生成输入

## 10.4 最小可执行方案

第一版不做向量检索，先做规则检索：
- 最近章节摘要固定取最近 N 章
- 人物从设定和章节摘要里取高频角色
- 地点从地图设定和最近事实里取
- 伏笔按未回收状态和章节范围过滤

第二版再接入语义检索：
- 对章节摘要、设定块、知识事实做 embedding
- 按当前写作目标检索最相关片段

### 验收标准

- 相同项目连续生成 10 章后，设定漂移明显下降
- 章节生成 prompt 长度可控，且不依赖全文拼接

---

## 11. 知识与分析系统计划

## 11.1 章节摘要

### 目标

每次生成或发布后都自动形成章节摘要。

### 实施

- FastAPI 生成章节后调用摘要任务
- Django 存储到 `ChapterSummary`
- 前端工作台右侧可查看章节摘要和开放线程

## 11.2 知识事实

### 目标

提取可复用的世界知识和剧情事实。

### 实施

- 从章节内容抽取三元组
- 事实标记来源章节和置信度
- 用于后续上下文构建和知识图谱展示

## 11.3 伏笔账本

### 目标

管理“已埋未收”的剧情元素。

### 实施

- 从章节或人工输入生成伏笔项
- 标记状态：
  - `open`
  - `hinted`
  - `resolved`
  - `abandoned`
- 在生成下一章前把相关伏笔加入上下文

## 11.4 风格分析

### 目标

监控文本是否偏离目标文风。

### 实施

- 建立项目级风格样本
- 对新章节做风格对比评分
- 工作台展示风险，不自动阻断发布

## 11.5 一致性检查

### 目标

在发布前发现明显冲突。

### 实施

- 输入：章节文本 + 历史摘要 + 稳定事实 + 设定
- 输出：
  - 冲突项
  - 风险项
  - 建议修复点

---

## 12. 前端工作台计划

## 12.1 总体目标

统一成单一主工作台，而不是多个分散页面。

## 12.2 布局目标

采用你现有草案方向：
- 左侧：章节列表
- 中间：写作中心
- 右侧：设定 / 知识 / 图谱 / 风格 / 伏笔
- 顶部：项目概览

## 12.3 页面结构

### `HomePage`
- 负责建书入口、书目概览、统计卡片

### `WorkspacePage`
- 作为唯一创作页面

### `ChapterSidebar`
- 显示章节、状态、字数、选中项

### `WritingCenter`
- 显示流式输出、运行状态、实时日志、操作按钮

### `SettingsPanel`
- 展示 6 步设定
- 切换知识图谱、故事线、伏笔面板

### `WorkspaceTopBar`
- 显示书名、完成率、累计字数、最近更新时间、当前运行状态

## 12.4 前端状态管理调整

- 把“当前项目工作台状态”与“首页书库状态”分离
- 流式连接状态单独存储，不和页面 UI 状态混杂
- 生成日志、文本流、当前章节生成进度都要可恢复

## 12.5 前端 API 调整

新增聚合请求：
- `getWorkbenchContext(projectId)`

减少散请求：
- 不要在工作台初始加载时分别打十几个接口

---

## 13. 异步任务与调度计划

## 13.1 保留的异步任务

- 生成后摘要
- 生成后事实抽取
- 统计更新
- 创意采集
- 发布相关后台任务

## 13.2 降级的异步任务

- 定时自动写作
- 复杂 Beat 自动推进章节

## 13.3 新任务编排原则

章节写作完成后的任务链：
1. 保存章节草稿
2. 提取章节摘要
3. 提取知识事实
4. 扫描伏笔候选
5. 更新统计
6. 生成一致性报告

这些任务允许拆成独立 Celery 任务，但对前端应表现为同一个“生成后处理流程”。

---

## 14. 模块级实施清单

## 14.1 Django

### 结构整理

- 拆分 `backend/apps/novels/views.py`
- 为工作台增加 service 层，而不是在 view 中串逻辑
- 给新增创作资产单独 serializer / service / viewset

### 建议新增目录

```text
backend/apps/creative/
  services/
  selectors/
  builders/
backend/apps/workbench/
  views.py
  services.py
  serializers.py
```

## 14.2 FastAPI

### 结构整理

- `routers/` 按任务类型拆清楚：生成、流式、分析
- `services/` 中分出：
  - `generation_service.py`
  - `analysis_service.py`
  - `context_builder.py`
  - `prompt_templates.py`

## 14.3 Frontend

### 结构整理

- `pages/Dashboard/` 下继续拆组件
- 把工作台组件和首页组件彻底分开
- 增加 `hooks/useWorkbenchContext.ts`
- 增加 `store/workbenchStore.ts`

---

## 15. 测试计划

## 15.1 Django 测试

必须补齐：
- 工作台聚合接口测试
- Storyline / PlotArc / KnowledgeFact / ForeshadowItem 模型与接口测试
- 章节生成后处理入库测试

## 15.2 FastAPI 测试

必须补齐：
- WebSocket 章节流式生成测试
- Provider fallback 测试
- 结构化输出解析测试
- 摘要 / 事实 / 一致性分析接口测试

## 15.3 Frontend 测试

必须补齐：
- `NewBookWizard` 之外的工作台组件测试
- `useChapterStream` hook 测试
- `WorkspacePage` 集成测试

## 15.4 回归重点

- 发布链路不能被新工作台破坏
- 现有 JWT 登录和 Provider 管理不能回退
- 旧项目数据在新工作台可读取

---

## 16. 监控与审计计划

## 16.1 必须记录

每次生成要记录：
- project_id
- chapter_id / chapter_number
- task_type
- provider
- model
- 耗时
- 输入大小
- 输出字数
- 是否命中 fallback

## 16.2 建议新增日志维度

- 工作台进入耗时
- 聚合接口耗时
- 后处理任务链耗时
- 一致性检测失败率
- 设定重新生成频率

---

## 17. 实施顺序

本计划不按时间排，但按依赖顺序执行。

### 阶段 A：统一工作台主流程

- 完成 `WorkspacePage` 重设计
- 统一章节状态机
- 完成 `ws/generate-chapter`
- 打通“生成 -> draft -> 发布”

### 阶段 B：补齐创作资产

- 新增 Storyline / PlotArc / ChapterSummary / KnowledgeFact / ForeshadowItem
- 建立建书完成后的初始化逻辑
- 建立章节生成后的后处理链路

### 阶段 C：引入上下文引擎

- 完成规则型上下文包构建
- 接入最近章节摘要、设定、角色、地点、伏笔
- 让章节生成接口全部改走上下文引擎

### 阶段 D：补齐分析能力

- 风格基线
- 一致性检查
- 伏笔追踪
- 知识图谱可视化

### 阶段 E：再考虑高级自动化

- 半自动续写
- 多书并发写作调度
- 语义检索增强
- 成本与质量评分闭环

---

## 18. 明确不做的事

在前几轮实施中，不建议同时做以下内容：
- 重构为 DDD 四层大架构
- 一次性引入过多新微服务
- 把所有旧页面立即删除
- 先上向量数据库再考虑工作台
- 先做复杂自动驾驶再解决上下文问题

---

## 19. 完成标准

满足以下条件时，可认为 `fqxs` 已完成从“自动化平台”向“创作平台”的关键升级：

- 用户能在统一工作台完成建书、写作、查看设定、查看知识、发布章节
- 新生成章节不再只是一段文本，而是伴随摘要、事实、日志和质量信息
- 上下文引擎已成为章节生成的默认入口
- 设定漂移、人物错乱、剧情遗忘问题有可观测改善
- 平台能力未丢失：登录、Provider 管理、统计、任务、发布仍可用

---

## 20. 结论

`fqxs` 不需要复制 `PlotPilot` 的代码组织方式，但必须吸收它的三个核心思想：
- 创作问题要领域化
- 上下文能力要系统化
- 生成结果要资产化

执行本计划后，`fqxs` 会保持你现有工程底座的优势，同时补上“长篇创作智能”这一块最关键的短板。
