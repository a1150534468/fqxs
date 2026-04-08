# 浏览器自动化发布指南

## 概述

使用 Playwright 浏览器自动化技术实现番茄小说章节发布，无需逆向 API，更稳定可靠。

## 优势

✅ **无需逆向工程** - 直接模拟真实用户操作
✅ **更稳定** - 不受 API 变化影响
✅ **更安全** - 行为模式与真实用户一致
✅ **易于调试** - 可以看到浏览器实际操作过程

## 安装浏览器

首次使用需要安装浏览器驱动：

```bash
cd backend
source .venv/bin/activate
playwright install chromium
```

## 配置选择器

在使用前，需要根据番茄小说实际页面更新 CSS 选择器。

### 1. 打开番茄小说网站

访问番茄小说创作者平台，使用浏览器开发者工具（F12）查看页面元素。

### 2. 找到关键元素

需要找到以下元素的选择器：

**登录页面**
- 用户名输入框: `input[name="username"]`
- 密码输入框: `input[name="password"]`
- 登录按钮: `button[type="submit"]`
- 登录成功标识: `.user-profile` 或其他

**章节发布页面**
- 章节标题输入框: `input[name="title"]`
- 章节内容编辑器: `textarea[name="content"]` 或富文本编辑器
- 发布按钮: `button.publish-btn`
- 成功提示: `.success-message`
- 错误提示: `.error-message`

**统计页面**
- 阅读量: `.views-count`
- 点赞数: `.likes-count`
- 评论数: `.comments-count`

### 3. 更新代码中的选择器

编辑 `backend/services/tomato_browser_publisher.py`，将 `TODO` 标记的选择器替换为实际值。

## 使用方式

### 基础用法

```python
from services.tomato_browser_publisher import TomatoBrowserPublisher

async def publish_example():
    # 创建发布器实例
    publisher = TomatoBrowserPublisher(
        headless=False,  # 显示浏览器窗口（调试时使用）
        proxy='http://proxy:port',  # 可选：使用代理
        user_data_dir='/path/to/profile',  # 可选：保存登录状态
    )

    async with publisher:
        # 登录
        success = await publisher.login(
            username='your_username',
            password='your_password',
            login_url='https://fanqienovel.com/login'
        )

        if success:
            # 发布章节
            result = await publisher.publish_chapter(
                novel_id='123456',
                chapter_number=1,
                chapter_title='第一章 开始',
                content='章节内容...',
                publish_url='https://fanqienovel.com/novel/123456/chapter/new'
            )
            print(result)
```

### 同步用法（Django 视图中）

```python
from services.tomato_browser_publisher import TomatoBrowserPublisherSync

def publish_chapter_view(request):
    publisher = TomatoBrowserPublisherSync(headless=True)

    result = publisher.publish_chapter(
        novel_id='123456',
        chapter_number=1,
        chapter_title='第一章',
        content='内容...',
        publish_url='https://...'
    )

    return JsonResponse(result)
```

## 配置参数

### headless (bool)
- `True`: 无头模式，后台运行（生产环境）
- `False`: 显示浏览器窗口（调试时使用）

### proxy (str, optional)
代理服务器地址，格式：`http://ip:port`

### user_data_dir (str, optional)
浏览器配置文件目录，用于保存登录状态和 Cookie。

**建议配置**：
```python
user_data_dir='/Users/z/code/fqxs/backend/.browser_profiles/tomato'
```

这样登录一次后，后续无需重复登录。

## 反检测策略

已实现的反检测措施：

1. **隐藏自动化特征**
   - 移除 `navigator.webdriver` 标识
   - 禁用自动化控制特征

2. **模拟人类行为**
   - 随机延迟（1-3秒）
   - 逐字输入（模拟打字）
   - 随机鼠标移动

3. **真实浏览器环境**
   - 使用 Chromium 真实浏览器
   - 完整的 JavaScript 执行环境
   - 真实的浏览器指纹

## 调试技巧

### 1. 显示浏览器窗口

```python
publisher = TomatoBrowserPublisher(headless=False)
```

### 2. 截图保存

代码中已自动保存发布前截图到 `/tmp/chapter_N_before_submit.png`

### 3. 慢速执行

增加延迟时间：

```python
await self._random_delay(5, 10)  # 延长到 5-10 秒
```

### 4. 查看浏览器日志

```python
page.on('console', lambda msg: print(f'Browser: {msg.text}'))
```

## 常见问题

### Q: 登录失败怎么办？

A: 
1. 检查选择器是否正确
2. 使用 `headless=False` 查看实际页面
3. 检查是否有验证码（需要手动处理或使用验证码识别服务）
4. 确认账号密码正确

### Q: 发布失败怎么办？

A:
1. 检查是否已登录
2. 确认发布页面 URL 正确
3. 检查内容是否符合平台规范
4. 查看截图确认页面状态

### Q: 如何处理验证码？

A:
1. **图片验证码**: 使用 OCR 识别或第三方验证码识别服务
2. **滑块验证码**: 使用图像识别 + 鼠标轨迹模拟
3. **人工介入**: 在需要验证码时暂停，等待人工完成

### Q: 会被检测为机器人吗？

A: 
Playwright 使用真实浏览器，检测难度较高。但仍需注意：
- 不要频繁操作（每次间隔 > 5 分钟）
- 使用代理 IP 轮换
- 保存登录状态，避免频繁登录
- 模拟真实用户行为（浏览、停留、随机操作）

## 性能优化

### 1. 复用浏览器实例

```python
# 不推荐：每次都创建新实例
for chapter in chapters:
    async with TomatoBrowserPublisher() as pub:
        await pub.publish_chapter(...)

# 推荐：复用实例
async with TomatoBrowserPublisher() as pub:
    await pub.login(...)
    for chapter in chapters:
        await pub.publish_chapter(...)
        await asyncio.sleep(300)  # 间隔 5 分钟
```

### 2. 使用持久化配置

```python
publisher = TomatoBrowserPublisher(
    user_data_dir='/path/to/profile'  # 保存登录状态
)
```

### 3. 并发控制

不建议并发发布，容易触发风控。建议串行 + 随机延迟。

## 集成到 Celery 任务

```python
from celery import shared_task
from services.tomato_browser_publisher import TomatoBrowserPublisherSync

@shared_task
def publish_chapter_task(chapter_id):
    from apps.chapters.models import Chapter
    from apps.publishing.models import PublishConfig

    chapter = Chapter.objects.get(id=chapter_id)
    config = PublishConfig.objects.get(project=chapter.project)

    publisher = TomatoBrowserPublisherSync(
        headless=True,
        user_data_dir=f'/tmp/browser_profile_{config.user_id}'
    )

    # 登录（如果需要）
    publisher.login(
        username=config.platform_username,
        password=config.platform_password,
        login_url='https://fanqienovel.com/login'
    )

    # 发布
    result = publisher.publish_chapter(
        novel_id=config.novel_id,
        chapter_number=chapter.chapter_number,
        chapter_title=chapter.title,
        content=chapter.final_content,
        publish_url=f'https://fanqienovel.com/novel/{config.novel_id}/chapter/new'
    )

    return result
```

## 安全建议

1. **密码加密存储** - 已实现，使用 Django 加密工具
2. **限制发布频率** - 每日 ≤ 1 章
3. **使用代理 IP** - 避免 IP 被封
4. **保存操作日志** - 便于追踪问题
5. **定期更新选择器** - 平台页面可能变化

## 下一步

1. 访问番茄小说创作者平台
2. 使用开发者工具找到实际的 CSS 选择器
3. 更新 `tomato_browser_publisher.py` 中的选择器
4. 测试登录和发布流程
5. 集成到前端界面

## 参考资源

- [Playwright 官方文档](https://playwright.dev/python/)
- [CSS 选择器教程](https://www.w3schools.com/cssref/css_selectors.asp)
- [浏览器自动化最佳实践](https://playwright.dev/python/docs/best-practices)
