# 番茄小说自动化平台 - 部署和使用指南

## 系统架构

```
前端 (React) → Django API → FastAPI (AI生成) + Celery (异步任务)
                    ↓
              MySQL + Redis
```

## 一、环境准备

### 1. 启动基础服务

```bash
# 启动 MySQL 和 Redis (Docker)
docker-compose up -d mysql redis
```

### 2. 后端服务启动

```bash
cd /Users/z/code/fqxs/backend

# 激活虚拟环境
source .venv/bin/activate

# 应用数据库迁移
python manage.py migrate

# 创建管理员用户（如果还没有）
python manage.py create_admin

# 启动 Django 服务 (终端1)
python manage.py runserver

# 启动 Celery Worker (终端2)
celery -A config worker --loglevel=info

# 启动 Celery Beat 定时任务 (终端3)
celery -A config beat --loglevel=info
```

### 3. FastAPI 服务启动

```bash
cd /Users/z/code/fqxs/fastapi_service

# 激活虚拟环境
source .venv/bin/activate

# 启动 FastAPI (终端4)
uvicorn main:app --reload --port 8001
```

### 4. 前端服务启动

```bash
cd /Users/z/code/fqxs/frontend

# 启动开发服务器 (终端5)
npm run dev
```

## 二、配置 LLM Provider

1. 访问 http://localhost:5173/llm-providers
2. 点击"添加 Provider"
3. 填写配置：
   - 名称：通义千问
   - Provider 类型：tongyi
   - API URL：https://dashscope.aliyuncs.com/compatible-mode/v1
   - API Key：你的密钥
   - 模型名称：qwen-turbo（或 qwen-plus、qwen-max）
   - 任务类型：章节生成
   - 优先级：50
4. 点击"测试连接"，成功后保存

## 三、完整工作流程

### 流程 1：从热门书生成创意

1. **采集热门书数据**（可选，如果数据库为空）
   ```bash
   cd /Users/z/code/fqxs/backend
   python manage.py run_spider --limit 20 --rank-types hot --allow-no-proxy
   ```

2. **生成创意**
   - 访问 http://localhost:5173/inspirations
   - 点击"生成创意"按钮
   - 系统会分析热门书，用 AI 生成新创意
   - 生成的创意会自动保存到创意库

### 流程 2：自定义创意生成

1. 访问创意库页面
2. 点击"自定义生成"按钮
3. 输入提示词，例如：
   ```
   生成一个都市修仙题材的小说创意，主角是程序员，
   在加班时意外获得修仙系统，开始在都市中修炼。
   要求：爽文风格，快节奏，有金手指。
   ```
4. 选择生成数量（1-5）
5. 点击生成

### 流程 3：启动项目（全自动）

1. 在创意库中选择一个创意
2. 点击"启动项目"按钮
3. 系统自动执行：
   - 创建小说项目
   - 生成大纲（100章规划）
   - 生成第一章（状态：pending_review）
4. 自动跳转到章节列表

### 流程 4：配置自动生成

1. 访问项目管理页面
2. 点击项目进入详情页
3. 在"自动生成配置"区域：
   - 开启"启用自动生成"开关
   - 选择生成频率：每天/每2天/每周
   - 查看下次生成时间
4. 或者点击"立即生成下一章"手动触发

### 流程 5：章节审核和编辑

1. 在项目详情页的章节列表中
2. 点击"编辑"按钮
3. 使用 Markdown 编辑器修改内容
4. 修改完成后保存
5. 将状态改为"approved"（待发布）

### 流程 6：发布到番茄小说

1. 确保章节状态为"approved"
2. 点击"发布到番茄小说"按钮
3. 确认发布信息
4. 系统使用浏览器自动化发布
5. 发布成功后状态变为"published"

## 四、定时任务说明

系统配置了以下定时任务（Celery Beat）：

| 任务 | 时间 | 说明 |
|------|------|------|
| 爬取创意 | 每天凌晨2点 | 自动爬取番茄小说热门榜单 |
| 自动生成章节 | 每天早上8点 | 为所有启用自动生成的项目生成新章节 |
| 同步统计数据 | 每小时 | 同步阅读量、收益等数据 |

## 五、任务监控

访问 http://localhost:5173/tasks 查看：
- 所有异步任务状态
- 任务执行时间
- 错误信息
- 支持按类型和状态筛选

## 六、API 端点

### 创意管理
- `GET /api/inspirations/` - 列表
- `POST /api/inspirations/generate-from-trends/` - 从热门书生成
- `POST /api/inspirations/generate-custom/` - 自定义生成
- `POST /api/inspirations/{id}/start-project/` - 启动项目

### 项目管理
- `GET /api/novels/` - 列表
- `GET /api/novels/{id}/` - 详情
- `GET /api/novels/{id}/generation-status/` - 生成进度
- `POST /api/novels/{id}/start-auto-generation/` - 启动自动生成
- `POST /api/novels/{id}/stop-auto-generation/` - 停止自动生成
- `POST /api/novels/{id}/generate-next-chapter/` - 手动生成下一章

### 章节管理
- `GET /api/chapters/` - 列表
- `GET /api/chapters/{id}/` - 详情
- `PATCH /api/chapters/{id}/` - 编辑
- `POST /api/chapters/{id}/publish/` - 发布

### 任务监控
- `GET /api/tasks/` - 任务列表
- `GET /api/tasks/{id}/` - 任务详情

## 七、常见问题

### 1. Celery 任务不执行

确保 Celery Worker 和 Beat 都在运行：
```bash
# 检查进程
ps aux | grep celery

# 重启 Worker
celery -A config worker --loglevel=info

# 重启 Beat
celery -A config beat --loglevel=info
```

### 2. LLM 调用失败

- 检查 API Key 是否正确
- 检查模型名称是否匹配
- 查看 FastAPI 日志：http://localhost:8001/docs

### 3. 浏览器自动化失败

- 确保已安装 Playwright：`playwright install chromium`
- 检查番茄小说是否已登录
- 查看日志文件：`backend/logs/django.log`

### 4. 前端页面空白

- 检查浏览器控制台错误
- 确认后端服务正常运行
- 检查 JWT Token 是否过期

## 八、测试

运行完整工作流测试：
```bash
cd /Users/z/code/fqxs/backend
source .venv/bin/activate
python test_full_workflow.py
```

## 九、服务地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:5173 | React 应用 |
| Django API | http://localhost:8000 | REST API |
| FastAPI | http://localhost:8001 | AI 生成服务 |
| FastAPI 文档 | http://localhost:8001/docs | Swagger UI |
| Django Admin | http://localhost:8000/admin | 后台管理 |

## 十、默认账号

- 用户名：admin
- 密码：admin123

## 十一、数据备份

```bash
# 备份数据库
cd /Users/z/code/fqxs/backend/scripts
./backup_db.sh

# 恢复数据库
./restore_db.sh backup_20260408.sql.gz
```
