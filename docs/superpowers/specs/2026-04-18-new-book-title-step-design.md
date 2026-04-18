# 新书向导书名首步设计

## 背景
当前新书设置向导从世界观开始，缺少一个独立的“先生成书名候选并让用户选择”的起始步骤。用户希望把它放到创建流程的第一步，并要求前后端一起实现，同时兼容已经在旧流程中迭代的草稿，不要强行打断旧用户流程。

## 目标
- 在现有新书向导前新增“书名”第一步。
- 后端基于灵感文本、题材、风格偏好生成 3-5 个书名候选。
- 用户可以换一批并从候选中选择 1 个作为正式书名。
- 选中的书名保存到 `NovelDraft.title`，后续设定生成统一优先使用它。
- 兼容旧草稿：没有书名时提示去补，但不强制。

## 当前实现约束
- 前端向导组件位于 `frontend/src/pages/Dashboard/NewBookWizard.tsx`，当前通过 `wizardSteps` 与 `WIZARD_STEP_TYPES` 驱动 6 个业务步骤加最终确认页。
- 草稿数据模型位于 `backend/apps/novels/models.py` 的 `NovelDraft` / `DraftSetting`。
- 草稿接口位于 `backend/apps/novels/views.py` 的 `DraftViewSet`。
- 前端创建草稿入口当前只传 `inspiration`，见 `frontend/src/pages/Dashboard/index.tsx`。
- DraftSetting 只覆盖世界观、人物、地图、故事线、情节弧、开始，不适合承载书名选择状态。

## 方案对比
### 方案 A（采用）
把“书名”作为向导首步，但不写入 `DraftSetting`，而是单独写回 `NovelDraft.title`。新增后端书名候选生成接口；前端在书名步拉取候选、换一批、选择后进入后续 6 步。

优点：
- 与当前 `NovelDraft -> DraftSetting -> complete` 结构兼容最好。
- 书名属于草稿元信息，不污染设定表。
- 对已有 6 步生成逻辑改动集中，边界清晰。

缺点：
- 需要补充草稿风格偏好字段和一条新接口。

### 方案 B（未采用）
在向导打开前弹出独立书名选择弹窗。

不采用原因：流程割裂，旧草稿恢复时体验不一致。

### 方案 C（未采用）
把书名候选塞进世界观页顶部。

不采用原因：语义错误，会把书名选择与世界观生成耦合，后续维护更脏。

## 最终设计

### 1. 数据模型
在 `NovelDraft` 增加字段：
- `style_preference: CharField(max_length=100, blank=True, default='')`

说明：
- 仅保存用于生成书名的风格偏好。
- 不新增 `title_confirmed` 等状态字段。
- 不新增候选书名落库表。

### 2. 后端接口
#### 2.1 扩展草稿读写
- `NovelDraftSerializer` 暴露 `style_preference`。
- 创建草稿时支持传 `style_preference`。
- 继续复用 `PATCH /drafts/<id>/` 保存用户选中的 `title`。

#### 2.2 新增书名候选接口
新增：`POST /drafts/<id>/generate-titles/`

请求：
```json
{
  "count": 5
}
```

后端从 draft 读取：
- `inspiration`
- `genre`
- `style_preference`

再调用 FastAPI：`POST /api/ai/generate/titles`

响应：
```json
{
  "titles": ["标题1", "标题2", "标题3", "标题4", "标题5"],
  "style_preference": "爽文逆袭"
}
```

规则：
- 默认 5 个，允许 3-5。
- 去除空值、首尾空格、重复值。
- 若 draft `is_completed=True`，返回 400。
- 只允许草稿 owner 调用。
- 候选不落库。

#### 2.3 FastAPI 侧
新增 AI 入口：`POST /api/ai/generate/titles`

输入：
```json
{
  "inspiration": "...",
  "genre": "...",
  "style_preference": "...",
  "count": 5
}
```

输出：
```json
{
  "titles": ["...", "...", "..."]
}
```

生成约束：
- 书名风格接近中文网文标题。
- 避免重复、空字符串、说明文字。
- 只返回数组，便于前端直接展示。

### 3. 前端交互
#### 3.1 步骤结构
向导展示步骤改为：
1. 书名
2. 世界观
3. 人物
4. 地图
5. 故事线
6. 情节弧
7. 开始
8. 进入工作台

注意：
- 只有第 2-7 步对应 `WIZARD_STEP_TYPES`。
- 书名步不写 `DraftSetting`。

#### 3.2 新增状态
在 `NewBookWizard` 中新增：
- `draftTitle`
- `titleOptions`
- `titleLoading`
- `selectedTitle`
- `titlePromptVisible`（旧草稿无书名时提示）
- `draftMeta`（至少包含 `title`、`style_preference`、`current_step`，若不想单独拉详情，可直接扩展 props 或草稿初始化结果）

#### 3.3 起始步逻辑
- 新草稿：无 `DraftSetting` 且无 `title` → 从书名步开始。
- 旧草稿已有任意 `DraftSetting` → 从其现有进度继续，不强制回书名步。
- 旧草稿有 `title` 但无设定 → 视为书名已就绪，从世界观开始。
- 旧草稿有设定但无 `title` → 正常进入当前步骤，同时显示“建议补选书名”的提示，允许用户点击回到书名步。

#### 3.4 书名步行为
- 进入书名步时自动请求候选书名。
- 点击“换一批”再次请求生成。
- 点击候选卡片选中书名。
- “下一步”仅在选中后可用。
- 点击“下一步”时调用 `updateDraft(draftId, { title: selectedTitle })`，成功后进入世界观。

#### 3.5 旧草稿提示
如果草稿已有设定但没有 `title`：
- 页面顶部显示非阻塞提示：
  - “当前尚未确认书名，补选后可让后续 AI 设定生成更稳定。”
- 提供按钮：
  - “去补书名” → 跳转到书名步
  - “继续当前步骤” → 关闭提示继续编辑

### 4. 上下文兼容策略
后续 AI 设定生成统一使用：
1. `draft.title`
2. `pendingTitle`
3. `'新书'`

这条规则同时用于：
- `book_title`
- 构建 `context` 时的书名提示

这样既支持新流程，也兼容旧草稿与旧入口。

### 5. 兼容旧数据
- 不做历史数据迁移回填。
- 不批量补生成书名。
- 不为旧草稿新增状态标记。
- 旧草稿只要已有设定，就允许继续原流程，不强制先补书名。
- 没有书名时仅提示，不阻塞。

### 6. 错误处理
- 书名生成失败：停留在书名步，前端提示“书名生成失败，请重试”。
- 候选数不足：展示已有候选，只要至少 1 个就允许选择。
- 旧草稿补书名失败：只影响补书名操作，不影响继续编辑既有设定。

### 7. 测试要求
#### Django / FastAPI
- 创建 draft 可保存 `style_preference`。
- `generate-titles` 仅 owner 可调用。
- `generate-titles` 正确透传 `inspiration` / `genre` / `style_preference`。
- `generate-titles` 会清洗空值与重复值。
- 完成状态 draft 禁止继续生成候选。
- `PATCH draft.title` 可保存选中书名。

#### 前端
- 新草稿默认进入书名步。
- 未选书名无法进入下一步。
- 书名步可换一批。
- 选择书名后会写回 draft.title。
- 旧草稿有设定时跳过强制书名步。
- 旧草稿无书名时显示提示。
- 后续生成优先使用 `draft.title`。

### 8. 实现边界
本次仅实现：
- 书名首步
- 候选生成
- 选择并保存书名
- 旧草稿提示与兼容
- 后续生成上下文切换

不实现：
- 候选书名历史
- 候选落库
- 书名评分排序解释
- 额外的确认状态字段
