# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 工作模式

Claude 作为总控，使用 Claude Agent Team（子 Agent 并行）完成任务：

- 先理解需求，再拆分为可并行的子任务
- 使用 Agent 工具 + 子 Agent 分派工作，各 Agent 完成后汇总
- 跨模块决策由 Claude 统筹，避免冲突

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
