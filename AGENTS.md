# AGENTS.md — 项目 Agent 团队配置

This file defines specialized agents for the TomatoFiction Auto-Platform project.

## Team Structure (Claude Agent Team)

- **Claude**: 总控 / 计划者 / 审阅者 / 最终验收
- **子 Agent**: 由 Claude 使用 Agent 工具并行派发的专项 Agent（前端、后端、数据库、DevOps）

---

## Agent 职责定义

### 前端 Agent
**职责范围**: React 18 + TypeScript、Vite、Zustand、Tailwind CSS、Ant Design、ECharts
- 使用 TypeScript strict mode，函数式组件 + hooks
- Zustand 管理全局状态，React state 管理局部状态
- 确保响应式设计，重点打造管理台/创意库/项目管理/人工审核区

### 后端 Agent
**职责范围**: Django + DRF、FastAPI、Celery + Redis、Scrapy
- 遵循 Django 最佳实践（apps 结构、models、serializers）
- FastAPI 使用 Pydantic 做数据验证
- 遵循 PEP 8，所有函数写文档字符串

### 数据库 Agent
**职责范围**: MySQL、MongoDB、Redis、Django ORM
- 核心表：User、Inspiration、NovelProject、Chapter、TaskLog
- 遵循数据库规范化，合理建索引，关键操作使用事务

### DevOps Agent
**职责范围**: Docker、Docker Compose、Nginx、Supervisor
- 多阶段构建，分离 dev/prod 配置
- .env 管理配置，健康检查，文档齐全

## 协作规则

1. Claude 分派任务给专项 Agent，各 Agent 并行工作
2. 每个 Agent 专注自己的领域
3. 跨域问题由 Claude 协调

## 项目约束

- **安全**: API Keys 加密存储，外部请求须经代理 IP 池
- **合规**: 遵循番茄小说平台规则，强制人工审核（修改率 >15%）
- **限频**: 每日 ≤1 本新书，每书每日 ≤1 章
- **人工干预**: 所有 AI 生成内容发布前必须经过人工编辑
