# 番茄小说发布集成指南

## 当前状态

**⚠️ 发布功能处于 Mock 模式**

由于番茄小说平台的 API 需要逆向工程，当前实现为框架代码，包含：
- 发布配置管理（数据模型）
- 发布记录追踪
- TomatoPublisher 客户端（Mock 模式）
- 代理 IP 池支持
- 反爬虫策略（随机延迟、User-Agent 轮换）

## 架构设计

### 数据模型

#### PublishConfig（发布配置）
- 平台账号信息（用户名/密码）
- 小说 ID 映射（本地项目 → 平台小说）
- 代理 IP 列表
- 启用状态

#### PublishRecord（发布记录）
- 章节发布状态（pending/publishing/success/failed）
- 平台章节 ID
- 错误信息
- 发布时间

### 服务层

#### TomatoPublisher
- 登录认证
- 章节发布
- 数据统计获取
- 代理 IP 轮换
- 反爬虫策略

## 实现步骤

### Phase 1: API 逆向工程（待完成）

需要分析番茄小说平台的以下接口：

1. **登录接口**
   ```
   POST /api/auth/login
   - 请求参数：username, password, 验证码
   - 响应：token, user_info
   - 需要处理：Cookie, CSRF Token
   ```

2. **章节发布接口**
   ```
   POST /api/novel/{novel_id}/chapter
   - 请求参数：chapter_number, title, content
   - 动态参数：ab, msToken, _signature
   - 响应：chapter_id, status
   ```

3. **数据统计接口**
   ```
   GET /api/novel/{novel_id}/stats
   GET /api/chapter/{chapter_id}/stats
   - 响应：views, likes, comments, revenue
   ```

### Phase 2: 动态参数生成（待完成）

番茄小说使用动态参数防止爬虫：

- **ab**: 设备指纹参数
- **msToken**: 时间戳相关 Token
- **_signature**: 请求签名

需要：
1. 分析 JavaScript 代码
2. 提取参数生成算法
3. 用 Python 实现

### Phase 3: 风控策略

已实现：
- ✅ 代理 IP 池轮换
- ✅ 随机 User-Agent
- ✅ 随机延迟（2-6秒）
- ✅ 请求头伪装

待完成：
- ⏳ 设备指纹模拟
- ⏳ 行为模式模拟（浏览→编辑→发布）
- ⏳ 频率限制（每日≤1章）

### Phase 4: 前端集成（待完成）

需要添加：
1. 发布配置页面
2. 章节发布按钮
3. 发布状态监控
4. 发布记录查看

## 使用方式（Mock 模式）

### 1. 配置发布信息

```python
from apps.publishing.models import PublishConfig

config = PublishConfig.objects.create(
    user=user,
    project=project,
    platform_username='your_username',
    platform_password='encrypted_password',
    novel_id='platform_novel_id',
    proxy_list='http://proxy1:port\nhttp://proxy2:port',
    is_active=True,
)
```

### 2. 发布章节

```python
from services.tomato_publisher import TomatoPublisher
from apps.publishing.models import PublishRecord

# 初始化发布器
publisher = TomatoPublisher(proxy_pool=config.get_proxy_list())

# 登录
publisher.login(config.platform_username, config.platform_password)

# 发布章节
result = publisher.publish_chapter(
    novel_id=config.novel_id,
    chapter_number=chapter.chapter_number,
    chapter_title=chapter.title,
    content=chapter.final_content,
)

# 记录发布结果
PublishRecord.objects.create(
    chapter=chapter,
    config=config,
    status='success' if result['status'] == 'success' else 'failed',
    platform_chapter_id=result.get('chapter_id', ''),
)
```

## 安全与合规

### 风险提示

1. **账号风险**
   - 频繁操作可能导致账号封禁
   - 建议使用测试账号

2. **法律风险**
   - 自动化发布可能违反平台服务条款
   - 仅用于个人学习和测试

3. **数据安全**
   - 密码需加密存储
   - 代理 IP 需定期更换

### 合规建议

1. **人工审核**
   - 所有内容必须人工审核后才能发布
   - 系统仅作为辅助工具

2. **频率控制**
   - 每日发布≤1章
   - 发布时间随机化

3. **内容质量**
   - 确保内容符合平台规范
   - 避免敏感词和违规内容

## 开发路线图

### 短期（1-2周）
- [ ] 完成番茄小说 API 逆向
- [ ] 实现登录和发布接口
- [ ] 添加前端发布配置页面

### 中期（2-4周）
- [ ] 实现动态参数生成
- [ ] 完善风控策略
- [ ] 添加发布状态监控

### 长期（1-2月）
- [ ] 实现数据统计同步
- [ ] 添加自动化发布调度
- [ ] 完善错误处理和重试机制

## 参考资源

### 逆向工程工具
- Chrome DevTools（网络抓包）
- Fiddler / Charles（HTTPS 代理）
- JavaScript 反混淆工具

### 反爬虫绕过
- Selenium（浏览器自动化）
- Playwright（现代浏览器自动化）
- 指纹浏览器（AdsPower / Multilogin）

### 代理服务
- 亮数据（Bright Data）
- 智能代理（Smartproxy）
- 本地代理池搭建

## 注意事项

1. **本功能仅供学习研究**
   - 不建议用于商业用途
   - 使用前请阅读平台服务条款

2. **API 可能随时变化**
   - 平台更新可能导致接口失效
   - 需要持续维护和更新

3. **测试环境优先**
   - 先在测试账号验证
   - 确认稳定后再用于正式账号

## 联系与支持

如需完整实现番茄小说发布功能，需要：
1. 提供番茄小说账号用于测试
2. 分析平台最新 API 接口
3. 实现动态参数生成算法
4. 进行充分测试和调优

预计开发时间：2-4周
