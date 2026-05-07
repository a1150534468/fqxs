# 番茄小说自动化平台

> 基于 AI 的小说创作辅助系统，实现从创意生成到自动发布的全流程自动化

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20.svg)](https://www.djangoproject.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📖 项目简介

番茄小说自动化平台是一个完整的 AI 驱动的小说创作系统，支持：

- 🤖 **AI 创意生成**：自动分析热门书籍，生成创意灵感
- 📝 **12 步新书向导**：引导式创作流程，从灵感到完整设定
- ✍️ **智能章节生成**：AI 自动生成章节内容，支持流式输出
- 👁️ **人工审核编辑**：Markdown 编辑器，实时字数统计
- 🚀 **自动化发布**：浏览器自动化，一键发布到番茄小说
- 📊 **数据可视化**：完整的数据看板和统计分析
- 🔄 **多书并行**：同时维护 3-5 本小说

## ✨ 核心特性

### 1. AI 驱动的创作流程

```
创意生成 → 新书向导 → 章节生成 → 人工审核 → 自动发布
```

- **多 LLM Provider 支持**：OpenAI、通义千问、自定义接口
- **WebSocket 流式生成**：实时显示 AI 生成过程
- **智能上下文管理**：前序步骤作为后续生成的上下文

### 2. 12 步新书向导

1. 输入灵感创建草稿
2. AI 生成书名（多选项）
3. AI 生成世界观（8 维度）
4. AI 生成人物设定
5. AI 生成地图场景
6. AI 生成故事线
7. AI 生成情节弧
8. AI 生成开篇场景
9-12. 预留扩展步骤

### 3. 自动化程度

- ✅ **85% 自动化**：除人工审核外，其他环节全自动
- ✅ **定时任务**：每天早上 8 点自动生成章节
- ✅ **任务监控**：实时追踪任务状态
- ✅ **错误处理**：自动重试和降级机制

## 🏗️ 技术架构

### 技术栈

**前端**
- React 18 + TypeScript
- Vite（构建工具）
- Zustand（状态管理）
- Ant Design（UI 组件）
- ECharts（数据可视化）

**后端**
- Django 4.2 + DRF（REST API）
- FastAPI（AI 生成服务）
- Celery + Redis（异步任务）
- MySQL（数据存储）
- Playwright（浏览器自动化）

**部署**
- Docker + Docker Compose
- Nginx（反向代理）

### 系统架构

```
┌─────────────────────────────────────────┐
│         React 前端管理后台               │
│  (Dashboard/创意库/项目管理/审核区)      │
└─────────────────┬───────────────────────┘
                  │ HTTP/WebSocket
┌─────────────────▼───────────────────────┐
│         Django REST API                  │
│  (认证/CRUD/任务触发/数据统计)           │
└─────┬───────────────────────┬───────────┘
      │                       │
      │ HTTP                  │ Celery Task
      ▼                       ▼
┌─────────────┐      ┌──────────────────┐
│  FastAPI    │      │  Celery Worker   │
│  LLM 服务   │      │  (定时任务)      │
└─────────────┘      └──────────────────┘
      │                       │
      └───────────┬───────────┘
                  ▼
        ┌──────────────────┐
        │  MySQL + Redis   │
        └──────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0
- Redis 7.0
- Docker & Docker Compose

### 一键启动（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/fqxs.git
cd fqxs

# 2. 启动所有服务
docker compose up -d

# 3. 运行数据库迁移
docker compose exec django python manage.py migrate

# 4. 创建管理员账号
docker compose exec django python manage.py create_admin

# 5. 访问系统
# 前端：http://localhost:5173
# 后端：http://localhost:8000
# FastAPI：http://localhost:8001
```

### 手动启动

#### 1. 后端服务

```bash
# 启动数据库
docker compose up -d mysql redis

# 安装依赖
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 运行迁移
python manage.py migrate

# 创建管理员
python manage.py create_admin

# 启动 Django
python manage.py runserver 0.0.0.0:8000
```

#### 2. FastAPI 服务

```bash
cd fastapi_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动 FastAPI
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

#### 3. Celery 任务队列

```bash
cd backend

# 启动 Worker
celery -A config worker -l info

# 启动 Beat（定时任务）
celery -A config beat -l info

# 启动 Flower（监控面板）
celery -A config flower
```

#### 4. 前端服务

```bash
cd frontend
npm install

# 配置环境变量
cp .env.example .env

# 启动开发服务器
npm run dev
```

## 📚 文档

- [项目需求](docs/项目需求.md) - 完整的需求文档和功能说明
- [开发过程](docs/开发过程.md) - 详细的开发指南和技术实现
- [项目总结](docs/项目总结.md) - 项目总结和经验分享

## 🎯 使用指南

### 1. 配置 LLM Provider

登录系统后，进入设置页面配置 LLM Provider：

```
设置 → LLM Provider → 添加 Provider
```

支持的 Provider：
- OpenAI（gpt-3.5-turbo, gpt-4）
- 通义千问（qwen-turbo, qwen-plus, qwen-max）
- 自定义 OpenAI 兼容接口

### 2. 创建新书

```
Dashboard → 新建书目 → 输入灵感 → 12 步向导
```

系统会引导你完成：
- 书名生成
- 世界观设定
- 人物设定
- 地图场景
- 故事线
- 情节弧
- 开篇场景

### 3. 自动生成章节

```
项目详情 → 自动生成配置 → 开启自动生成
```

系统会每天早上 8 点自动生成章节。

### 4. 审核编辑

```
章节列表 → 选择章节 → 编辑
```

使用 Markdown 编辑器修改 AI 生成的内容。

### 5. 发布章节

```
章节详情 → 发布
```

系统会自动使用浏览器自动化发布到番茄小说。

## 📊 功能截图

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### 新书向导
![Wizard](docs/screenshots/wizard.png)

### 章节编辑
![Editor](docs/screenshots/editor.png)

### 数据分析
![Analytics](docs/screenshots/analytics.png)

## 🔧 配置说明

### 环境变量

**后端（backend/.env）**
```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库
DATABASE_URL=mysql://user:password@localhost:3306/fqxs

# Redis
REDIS_URL=redis://localhost:6379/0

# FastAPI
FASTAPI_URL=http://localhost:8001

# 加密密钥
ENCRYPTION_KEY=your-encryption-key
```

**FastAPI（fastapi_service/.env）**
```bash
# Django API
DJANGO_API_URL=http://localhost:8000

# LLM（可选，也可以在后台配置）
LLM_API_URL=https://api.openai.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-3.5-turbo

# Mock 模式
MOCK_GENERATION=False
```

**前端（frontend/.env）**
```bash
# API 地址
VITE_API_BASE_URL=http://localhost:8000/api
VITE_FASTAPI_URL=http://localhost:8001
```

## 🧪 测试

```bash
# 后端测试
cd backend
python manage.py test

# 前端测试
cd frontend
npm run test

# E2E 测试
npm run test:e2e
```

## 📈 性能指标

| 指标 | 数值 |
|------|------|
| 章节生成速度 | 2-5 分钟 |
| 并发支持 | 3-5 本书 |
| API 响应时间 | < 200ms |
| 任务成功率 | > 95% |
| 自动化率 | 85% |

## 🛣️ 路线图

### 已完成 ✅
- [x] 用户认证系统
- [x] LLM Provider 管理
- [x] 创意生成系统
- [x] 12 步新书向导
- [x] 章节自动生成
- [x] 章节编辑系统
- [x] 浏览器自动化发布
- [x] 任务监控系统
- [x] 数据统计系统

### 进行中 ⏳
- [ ] 性能优化（缓存、查询优化）
- [ ] 监控告警（Sentry、任务失败告警）
- [ ] 安全加固（API 限流、审计日志）

### 计划中 📋
- [ ] 支持更多 LLM Provider（Claude、Gemini）
- [ ] 微调模型（针对小说创作）
- [ ] RAG 检索增强生成
- [ ] 多模态生成（插图、封面）
- [ ] 支持更多小说平台（起点、晋江）
- [ ] SaaS 化（多租户）

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本项目
2. 创建特性分支（`git checkout -b feature/AmazingFeature`）
3. 提交更改（`git commit -m 'Add some AmazingFeature'`）
4. 推送到分支（`git push origin feature/AmazingFeature`）
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Claude AI](https://www.anthropic.com/) - 提供强大的 AI 能力支持
- [OpenAI](https://openai.com/) - 提供 GPT 系列模型
- [通义千问](https://tongyi.aliyun.com/) - 提供国产 LLM 支持
- 所有开源社区的贡献者

## 📧 联系方式

- 项目主页：https://github.com/yourusername/fqxs
- 问题反馈：https://github.com/yourusername/fqxs/issues
- 邮箱：your.email@example.com

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**
