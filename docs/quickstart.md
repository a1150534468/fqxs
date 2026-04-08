# 快速开始指南

## 🚀 5 分钟快速上手

### 1. 配置 LLM API（通义千问）

根据你提供的阿里云百炼文档，配置通义千问 API：

#### 方式一：前端界面配置（推荐）

1. 访问 http://localhost:5173/llm-providers
2. 点击"添加 Provider"
3. 填写配置：
   - **名称**: 通义千问
   - **Provider 类型**: tongyi
   - **API URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
   - **API Key**: 你的 DashScope API Key
   - **任务类型**: chapter（章节生成）
   - **优先级**: 100
   - **启用**: 开启
4. 点击"测试"验证连接
5. 保存

#### 方式二：环境变量配置

编辑 `.env` 文件：

```bash
# 关闭 Mock 模式
FASTAPI_MOCK_GENERATION=False

# 通义千问配置
FASTAPI_LLM_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
FASTAPI_LLM_API_KEY=sk-your-dashscope-api-key
FASTAPI_LLM_MODEL=qwen-turbo
```

重启 FastAPI 服务：

```bash
cd fastapi_service
pkill -f uvicorn
source .venv/bin/activate
uvicorn main:app --reload --port 8001
```

### 2. 测试 AI 生成

1. 访问 http://localhost:5173/novels
2. 创建一个新项目
3. 进入项目，点击"生成章节"
4. 填写章节信息，点击生成
5. 等待 AI 生成完成（使用真实 API）

### 3. 配置浏览器自动化发布

#### 安装浏览器驱动

```bash
cd backend
source .venv/bin/activate
playwright install chromium
```

#### 配置番茄小说选择器

1. 访问番茄小说创作者平台
2. 打开浏览器开发者工具（F12）
3. 找到以下元素的 CSS 选择器：
   - 登录页面：用户名、密码、登录按钮
   - 发布页面：标题、内容、发布按钮
4. 编辑 `backend/services/tomato_browser_publisher.py`
5. 更新 `TODO` 标记的选择器

#### 测试发布（调试模式）

```python
# 在 Django shell 中测试
python manage.py shell

from services.tomato_browser_publisher import TomatoBrowserPublisherSync

publisher = TomatoBrowserPublisherSync(
    headless=False,  # 显示浏览器窗口
    user_data_dir='/tmp/tomato_profile'
)

# 测试登录
result = publisher.login(
    username='your_username',
    password='your_password',
    login_url='https://fanqienovel.com/login'  # 实际登录页 URL
)
print(result)
```

## 📋 完整工作流程

### 1. 创意采集

```bash
# 手动触发爬虫
cd backend
source .venv/bin/activate
python manage.py run_spider --limit 10 --rank-types hot --allow-no-proxy
```

或等待定时任务（每天凌晨 2 点自动执行）

### 2. 创建项目

1. 访问 http://localhost:5173/inspirations
2. 浏览采集的创意
3. 选择一个创意，点击"创建项目"
4. 填写项目信息（标题、类型、大纲等）

### 3. 生成章节

1. 进入项目详情
2. 点击"生成章节"
3. AI 自动生成章节内容
4. 在编辑器中人工审核和修改（>15% 修改率）

### 4. 发布章节

1. 审核通过后，点击"发布"
2. 系统使用浏览器自动化发布到番茄小说
3. 查看发布记录和状态

## 🔐 安全配置

### API Key 加密

所有 API Key 和密码已自动加密存储：
- LLM Provider 的 API Key
- 番茄小说账号密码

加密基于 Django SECRET_KEY，确保 SECRET_KEY 安全：

```bash
# 生成新的 SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

更新 `.env` 文件：

```bash
SECRET_KEY=your-new-secret-key-here
```

### 备份数据

```bash
cd backend
./scripts/backup_db.sh
```

备份文件保存在 `backend/backups/`

## 📊 监控和日志

### 健康检查

```bash
# Django
curl http://localhost:8000/api/health/

# FastAPI
curl http://localhost:8001/health
```

### 查看日志

```bash
# Django 日志
tail -f backend/logs/django.log

# Celery 日志
tail -f backend/logs/celery.log

# 错误日志
tail -f backend/logs/error.log
```

### Celery 监控

访问 http://localhost:5555 查看 Flower 监控面板

## 🛠️ 常用命令

### 启动所有服务

```bash
# 1. 启动 Docker 服务（MySQL + Redis）
docker-compose up -d

# 2. 启动 Django
cd backend
source .venv/bin/activate
python manage.py runserver

# 3. 启动 FastAPI
cd fastapi_service
source .venv/bin/activate
uvicorn main:app --reload --port 8001

# 4. 启动 Celery Worker
cd backend
source .venv/bin/activate
celery -A config worker -l info

# 5. 启动 Celery Beat
cd backend
source .venv/bin/activate
celery -A config beat -l info

# 6. 启动前端
cd frontend
npm run dev
```

### 数据库操作

```bash
# 创建迁移
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 创建管理员
python manage.py create_admin
```

### 测试

```bash
# 运行所有测试
cd backend
source .venv/bin/activate
pytest -v

# 运行特定测试
pytest apps/chapters/tests.py -v
```

## 📚 文档索引

- **LLM 集成**: `docs/llm_integration.md`
- **浏览器自动化**: `docs/browser_automation.md`
- **备份恢复**: `docs/backup_recovery.md`
- **开发过程**: `docs/development.md`
- **需求设计**: `docs/requirements.md`
- **项目总结**: `docs/summary.md`

## ❓ 常见问题

### Q: LLM API 调用失败？

A: 
1. 检查 API Key 是否正确
2. 确认 Mock 模式已关闭（`FASTAPI_MOCK_GENERATION=False`）
3. 查看 FastAPI 日志：`tail -f /tmp/fastapi.log`
4. 测试 Provider 连接

### Q: 浏览器自动化不工作？

A:
1. 确认已安装浏览器：`playwright install chromium`
2. 检查选择器是否正确
3. 使用 `headless=False` 查看实际操作
4. 查看截图：`/tmp/chapter_*_before_submit.png`

### Q: Celery 任务不执行？

A:
1. 确认 Worker 和 Beat 都在运行
2. 检查 Redis 连接：`redis-cli ping`
3. 查看 Celery 日志：`tail -f backend/logs/celery.log`
4. 使用 Flower 监控：http://localhost:5555

## 🎯 下一步

1. ✅ 配置通义千问 API
2. ✅ 测试 AI 内容生成
3. ⏳ 配置番茄小说选择器
4. ⏳ 测试浏览器自动化发布
5. ⏳ 设置定时任务
6. ⏳ 监控系统运行状态

祝使用愉快！🎉
