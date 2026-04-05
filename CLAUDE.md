# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 多模型协作模式（默认）

本仓库默认采用三模型协作：

- **Claude**：总控 / 计划者 / 审阅者
- **Codex**：后端负责人
- **Gemini**：前端负责人

### 通信方式（CCB）

本仓库按教程采用 CCB 做本地通信桥接，不是模型彼此直连：

- Claude 作为唯一总控，在自己的会话里用 `/ask codex` 和 `/ask gemini` 下发任务
- Codex 与 Gemini 异步处理后，Claude 用 `/pend codex` 和 `/pend gemini` 收取结果
- 联通性检查使用 `/cping codex` 和 `/cping gemini`
- Codex 与 Gemini 不直接对话，跨域冲突统一回到 Claude 裁决
- 项目级默认启动配置位于 `.ccb/ccb.config`，默认启动 `codex + gemini + claude`

### 启动方式

- 在仓库根目录运行 `./start-role-team.sh`
- 需要恢复上次上下文时运行 `./start-role-team.sh -r`
- 启动后让 Claude 先读 `CLAUDE.md`、`AGENTS.md`，再按 `/ask -> /pend -> 汇总` 的节奏推进

### Claude 的职责

- 先理解需求，再拆分成前后端两个可并行子任务
- 先给计划，再给命令；不要一上来自己把全部实现做完
- 给 Codex 下发后端任务时，明确接口、数据结构、边界条件、验收标准
- 给 Gemini 下发前端任务时，明确页面目标、组件边界、状态流、交互要求
- 汇总两侧结果，做最后的冲突协调、验收与下一步安排

### Codex 的职责

- 专注后端：Django、FastAPI、Celery、Redis、Scrapy、数据库、鉴权、任务系统
- 当前端细节不明确时，先给接口契约、mock 数据结构、错误码和状态定义
- 非必要不改视觉层和页面布局

### Gemini 的职责

- 专注前端：React、TypeScript、Vite、Zustand、Tailwind、Ant Design、ECharts
- 当前后端尚未完成时，先基于接口契约推进页面骨架、状态建模和 mock 联调
- 非必要不改后端实现、数据库和部署逻辑
- Gemini 默认应使用工具能力直接完成前端实现
- Claude 给 Gemini 下发任务时，可明确要求使用 `gemini-3-pro-preview`

### 协作约束

- Claude 输出任务时，优先使用短指令 + 明确文件范围 + 明确完成标准
- Codex 与 Gemini 都只汇报自己负责的领域；跨域问题交给 Claude 裁决
- 如果任务横跨前后端，先由 Claude 切成两条并行任务，再安排联调检查点
- 若缺少 Gemini key 或某侧暂时不可用，Claude 需要先保证另一侧继续推进，不要整轮阻塞
- 如果 Gemini 出现工具调用异常，先确认模型是否为 `gemini-3-pro-preview`，再决定是否切回 `gemini-3.1-pro-preview`

## 项目概述

番茄小说自动化创作与管理平台 (TomatoFiction Auto-Platform) - 基于 React + Python 的全栈系统，集成 AI 内容生成、榜单数据分析、自动化发布与可视化管理。

**核心原则**: 遵循番茄小说平台规则，强制人工干预，使用代理 IP 池，避免高频操作。

## 技术栈

### 前端
- React 18 + TypeScript
- 构建工具: Vite
- 状态管理: Zustand
- UI 组件: Tailwind CSS / Ant Design
- 数据可视化: ECharts

### 后端
- Python 3.11+
- Django (可视化后台管理 API)
- FastAPI (AI 生成服务与高并发任务)
- Celery + Redis (异步任务)
- Scrapy (数据采集)

### 数据库
- MySQL (结构化数据)
- MongoDB (创意/日志)
- Redis (缓存/队列)

### 部署
- Docker + Docker Compose
- Nginx
- Supervisor

## 系统架构

采用微服务架构，主要模块：

1. **Web 服务层**: React 前端 + Django REST Framework
2. **AI 生成服务层**: FastAPI + 大模型 SDK
3. **数据采集层**: Scrapy 爬虫
4. **第三方服务**: 番茄小说 API 适配层

## 核心模块

### 可视化后台 (React + Django)
- Dashboard: 阅读量、收益趋势、AI 生成成功率
- 创意库: 热门榜单创意管理
- 项目管理: 小说项目创建/编辑
- 人工审核区: AI 草稿编辑 (强制修改率 >15%)
- 日志与监控

### AI 生成服务 (FastAPI)
- Prompt 工程: 动态构建提示词
- 内容生成: 调用 OpenAI / 通义千问 API
- 内容预审: Moderation API 过滤敏感词
- 迭代优化: 根据读者数据调整生成风格

### 创意收集 (Scrapy)
- 反爬策略: 代理 IP 池，随机 User-Agent，频率控制 (<1次/秒)
- 数据清洗: 提取书名、简介、标签、评论
- 定时任务: 每日凌晨执行

### 番茄小说 API 适配层
- 登录鉴权: Cookie 和 Token 处理
- 发布章节: 处理动态参数 ab 和 msToken
- 风控策略: 代理 IP，随机延迟，模拟移动端指纹

## 数据库设计

### 核心表结构
- **User**: 用户表 (id, username, email, api_key)
- **Inspiration**: 创意表 (id, source_url, title, synopsis, tags, hot_score, collected_at)
- **NovelProject**: 小说项目表 (id, user_id, title, genre, ai_prompt, status)
- **Chapter**: 章节表 (id, project_id, title, raw_content, final_content, publish_status, publish_time)
- **TaskLog**: 任务日志表 (id, task_type, status, message, created_at)

## 开发优先级

1. **基础架构**: Django + React 环境，数据库模型，JWT 认证
2. **数据采集**: Scrapy 爬虫，代理 IP 池，创意库 API
3. **核心生成**: FastAPI 服务，大模型集成，前端编辑器
4. **发布集成**: 番茄接口逆向，Celery 异步任务
5. **测试部署**: Docker 容器化，压力测试，风控测试

## 风险控制与合规

- **人工干预**: 所有 AI 内容必须经过前端编辑器修改
- **IP 策略**: 所有对外请求必须经过动态代理池
- **频率限制**: 每日 ≤ 1 本新书，每书每日 ≤ 1 章
- **数据安全**: API Keys 加密存储

## 重要约束

- 严格遵循番茄小说平台规则
- 避免高频操作触发风控
- 所有自动化操作必须有人工审核环节
