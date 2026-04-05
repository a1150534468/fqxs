# AI 协作启动说明

本文档根据教程整理 fqxs 仓库里的多模型协作方式，目标是把“谁负责什么、怎么通信、怎么启动”都落到仓库内。

## 1. 通信是怎么发生的

本项目使用的是 **CCB 本地桥接通信**，不是 Claude、Codex、Gemini 彼此直连。

实际链路是：

1. Claude 作为总控，在自己的会话中下发任务。
2. CCB 把 Claude 的请求路由给目标模型。
3. Codex 和 Gemini 在各自 pane/session 中异步执行。
4. Claude 再通过 `pend` 把结果收回来做整合和裁决。

在 fqxs 里，统一约束为：

- Claude 负责计划、分派、审阅、汇总
- Codex 只负责后端
- Gemini 只负责前端
- Codex 与 Gemini 不直接对话，跨域问题回到 Claude

## 2. 仓库里已经补齐了什么

- `AGENTS.md`
  角色分工、交接协议、通信约束
- `CLAUDE.md`
  Claude 的总控职责和 CCB 通信命令
- `CODEX.md`
  Codex 的后端职责说明
- `GEMINI.md`
  Gemini 的前端职责说明
- `.ccb/ccb.config`
  项目级 CCB 默认启动配置，固定为 `codex,gemini,claude`
- `start-role-team.sh`
  项目协作启动入口，默认走 CCB

## 3. 启动前检查

先确认这些命令可用：

```bash
ccb --help
claude --version
codex --version
gemini --version
```

如果 Claude 里没有 `/ask`、`/pend`、`/cping` 这些命令，先修复你的全局 CCB 安装，再回来启动项目协作。

## 4. 如何启动协作

在仓库根目录执行：

```bash
./start-role-team.sh
```

如果你想恢复上一次协作上下文：

```bash
./start-role-team.sh -r
```

如果你需要自动放开权限模式：

```bash
./start-role-team.sh -a
```

说明：

- `.ccb/ccb.config` 已固定启动 `codex + gemini + claude`
- `claude` 被放在最后，作为当前项目的总控 anchor pane
- 启动后，Claude 先读 `CLAUDE.md` 和 `AGENTS.md`，再开始拆任务

## 5. Claude 里的典型协作节奏

启动完成后，Claude 里按这个节奏工作：

1. 先输出一个短计划。
2. 用 `/ask codex` 发后端任务。
3. 用 `/ask gemini` 发前端任务。
4. 等异步处理一段时间后，用 `/pend codex` 和 `/pend gemini` 收结果。
5. Claude 再做冲突协调、验收和下一步安排。

示例：

```text
/ask codex 请实现 inspirations 列表 API，补 serializer、view、url，并写最小测试
/ask gemini 请先基于 inspirations 列表接口做创意库页面骨架，接口字段按 title/synopsis/tags/hot_score 预留
/pend codex
/pend gemini
```

## 6. 常见问题

### 看起来启动了，但 Claude 里没有协作命令

这是全局 CCB/Claude 配置问题，不是仓库问题。先检查你的 `~/.claude/CLAUDE.md` 里是否已经注入 CCB 配置。

### `cping` 或 `pend` 说没有活动会话

说明目标 provider 还没被 CCB 正常拉起，或者之前的 session 已失效。直接回到仓库根目录重新执行：

```bash
./start-role-team.sh
```

### 为什么不用 Codex 和 Gemini 直接互相发消息

这是故意的。教程强调总控单点协调，避免前后端 agent 互相改口径、产生冲突或丢失约束。

### Gemini 一收到实现任务就报 `function_response.name` 或 `undefined_tool_name`

优先检查当前 Gemini 默认模型。

在 fqxs 里已经验证：

- `gemini-3-pro-preview` 可以正常调用 `write_file`
- `gemini-3.1-pro-preview` 也可以，但更贵
- 轻量 preview/flash-lite 模型更容易在工具调用时产生错误参数或空工具名

因此建议：

- 将 Gemini 默认执行模型固定为 `gemini-3-pro-preview`
- 重新启动 Gemini/CCB 会话后再重试实现任务
