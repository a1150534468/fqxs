# LLM API 集成指南

## 概述

系统支持多 LLM Provider 配置，可以根据任务类型和优先级自动选择合适的 Provider。支持 OpenAI、通义千问等 OpenAI 兼容的 API。

## 配置方式

### 方式一：环境变量（默认 Provider）

编辑 `.env` 文件：

```bash
# 关闭 Mock 模式
FASTAPI_MOCK_GENERATION=False

# OpenAI 配置
FASTAPI_LLM_API_URL=https://api.openai.com/v1
FASTAPI_LLM_API_KEY=sk-your-openai-api-key-here
FASTAPI_LLM_MODEL=gpt-3.5-turbo

# 或使用通义千问
# FASTAPI_LLM_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# FASTAPI_LLM_API_KEY=sk-your-dashscope-api-key-here
# FASTAPI_LLM_MODEL=qwen-turbo
```

重启 FastAPI 服务：

```bash
cd fastapi_service
source .venv/bin/activate
pkill -f uvicorn
uvicorn main:app --reload --port 8001
```

### 方式二：数据库配置（推荐）

通过前端界面管理多个 LLM Provider，支持优先级和任务类型分配。

1. 访问 http://localhost:5173/llm-providers
2. 点击"添加 Provider"
3. 填写配置信息：
   - **名称**: 例如 "OpenAI GPT-4"
   - **Provider 类型**: openai / tongyi / custom
   - **API URL**: https://api.openai.com/v1
   - **API Key**: 你的 API Key
   - **任务类型**: outline（大纲）/ chapter（章节）/ continue（续写）
   - **优先级**: 0-100，数值越大优先级越高
   - **启用**: 开关

4. 点击"测试"按钮验证连接

## Provider 选择逻辑

系统按以下顺序选择 Provider：

1. 从数据库获取用户配置的 Provider（按优先级降序）
2. 尝试调用第一个 Provider
3. 如果失败，自动切换到下一个 Provider
4. 如果所有 Provider 都失败，返回错误

### 任务类型回退

设定生成（wizard）使用 `task_type='setting'` 查询 Provider。如果用户没有配置 `setting` 类型的 Provider，系统自动回退到 `chapter` 类型。这样只配一个 `chapter` Provider 即可同时支持章节生成和向导设定生成。

### 内部接口 `for-generation`

FastAPI 通过 `GET /api/llm-providers/for-generation/?task_type=setting` 获取 Provider 列表（含完整 api_key）。该接口：
- 仅返回当前用户的 `is_active=True` 的 Provider
- 返回扁平 JSON 列表（绕过 DRF 分页）
- 由 JWT 保护，仅供 FastAPI 服务间调用
- 支持 task_type 过滤，无匹配时回退到所有活跃 Provider

## 支持的 LLM Provider

### OpenAI

```
API URL: https://api.openai.com/v1
模型: gpt-3.5-turbo, gpt-4, gpt-4-turbo
```

### 通义千问（阿里云）

```
API URL: https://dashscope.aliyuncs.com/compatible-mode/v1
模型: qwen-turbo, qwen-plus, qwen-max
```

### 其他 OpenAI 兼容 API

任何支持 OpenAI Chat Completions API 格式的服务都可以使用，例如：
- Azure OpenAI
- 本地部署的 LLaMA / Mistral（通过 vLLM / Ollama）
- 其他云服务商的 LLM API

## 任务类型说明

- **outline**: 大纲生成 - 根据创意生成小说大纲
- **chapter**: 章节生成 - 根据大纲生成章节内容
- **continue**: 内容续写 - 续写现有内容
- **setting**: 设定生成 - 生成 11 种小说设定（世界观/人物/地图等）

可以为不同任务类型配置不同的 Provider，例如：
- 大纲生成使用 GPT-4（更强的规划能力）
- 章节生成使用 GPT-3.5（性价比高）

## 流式生成（WebSocket）

12 步向导使用 WebSocket 流式生成设定内容，端点为 `ws://localhost:8001/ws/generate-setting`。

### 架构

```
前端 (browser)
  │ WebSocket
  ▼
FastAPI (uvicorn) ─── stream=True ──→ LLM Provider API
  │                                        │
  │ ◄──── SSE delta chunks ────────────────┘
  │
  │  逐 chunk 发给前端 via ws.send_json()
  ▼
前端逐字渲染 (useSettingStream hook)
```

### 调用方式

前端 hook: `useSettingStream()` → `generate({ setting_type, book_title, genre, context, prior_settings })`

LLM 调用: `llm_provider_manager.call_llm_stream()` 使用 `httpx.AsyncClient.stream()` 解析 SSE delta 并逐 chunk yield。

Mock 模式: `mock_generation=true` 时逐字符 yield 预设内容（~30ms/字），模拟流式效果。

### 世界观 8 维度

世界观步骤使用 `WorldviewSchema`，包含 8 个字符串字段：
`time_setting` / `place_setting` / `social_structure` / `cultural_background` / `tech_level` / `power_system` / `history` / `natural_laws`

LLM 被要求同时输出 Markdown 正文和 JSON 结构化数据，后端用正则提取 JSON 块并通过 Pydantic 校验。

## 成本控制

### Token 限制

当前配置：
- 温度: 0.8（创意性）
- 最大 Token: 4096

### 重试策略

- 单个 Provider 失败后自动切换
- 最多尝试所有配置的 Provider
- 失败后记录详细日志

### 监控

查看日志：

```bash
# FastAPI 日志
tail -f /tmp/fastapi.log

# Django 日志
tail -f backend/logs/django.log
```

## 测试

### 测试 Provider 连接

前端界面点击"测试"按钮，或使用 API：

```bash
curl -X POST http://localhost:8000/api/llm-providers/1/test_connection/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 测试内容生成

```bash
curl -X POST http://localhost:8001/api/ai/generate/chapter \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "project_id": 1,
    "chapter_number": 1,
    "chapter_title": "序章",
    "outline_context": "故事开始于一个平凡的早晨"
  }'
```

## 故障排查

### Provider 连接失败

1. 检查 API Key 是否正确
2. 检查 API URL 是否可访问
3. 检查网络代理设置
4. 查看 FastAPI 日志

### 生成内容为空

1. 检查 Mock 模式是否关闭（`FASTAPI_MOCK_GENERATION=False`）
2. 检查 Provider 是否启用
3. 检查 API Key 余额

### 响应超时

1. 增加超时时间（当前 120 秒）
2. 减少 max_tokens 参数
3. 使用更快的模型（如 gpt-3.5-turbo）

## 安全建议

1. **不要提交 API Key 到 Git**
   - 使用 `.env` 文件（已在 .gitignore 中）
   - 或使用数据库存储（已加密）

2. **定期轮换 API Key**

3. **设置 API 使用限额**
   - 在 Provider 平台设置每日/每月限额

4. **监控异常调用**
   - 查看日志中的错误和重试记录
