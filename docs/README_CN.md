# Kodax Agent

<div align="center">

**一个真正好用的轻量级 AI 编程助手。**

单文件 • ~800 行代码 • 7 个大模型 • 流式输出 • 并行执行

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## 为什么选择 Kodax？

其他 AI 编程助手都太臃肿了。Kodax 只有**一个文件**，**零配置**，开箱即用支持 **7 个大模型**。

```
# 对比
Claude Code:   ~50,000 行, $20/月
Aider:         ~15,000 行, 配置复杂
Kodax:           ~800 行, uv sync 直接用
```

## 特性

- **单文件** - 所有代码在 `kodax_agent.py`，读懂它，改它，发布它
- **7 个模型** - Anthropic, OpenAI, Kimi, Kimi Code, 智谱, 智谱 Coding, 通义千问
- **流式输出** - 实时显示，不用等待
- **会话记忆** - 对话跨次保存
- **并行工具** - 同时执行多个工具
- **技能系统** - 用 Python 函数扩展功能
- **思考模式** - 复杂任务的深度推理（部分模型支持）

## 快速开始

```bash
# 安装
git clone https://github.com/icetomoyo/KodaX.git
cd KodaX
uv sync

# 设置 API Key
export ANTHROPIC_API_KEY=your-key    # 或 KIMI_API_KEY, ZHIPU_API_KEY 等

# 运行
uv run kodax_agent.py "用 FastAPI 创建一个 REST API"
```

## 使用

```bash
# 基本用法
uv run kodax_agent.py "你的编程任务"

# 使用其他模型
uv run kodax_agent.py --provider kimi-code "你的任务"

# 复杂任务开启思考模式
uv run kodax_agent.py --provider zhipu-coding --thinking "重构这个项目"

# 恢复之前的对话
uv run kodax_agent.py --session resume "继续之前的 API 开发"

# 并行执行（多文件任务更快）
uv run kodax_agent.py --parallel "读取所有 markdown 文件并总结"

# 多任务并行
uv run kodax_agent.py --team "分析代码结构,检查测试覆盖率,查找 bug"
```

## 支持的模型

| 模型 | API Key | 思考模式 | 说明 |
|------|---------|----------|------|
| Anthropic | `ANTHROPIC_API_KEY` | 支持 | Claude（默认） |
| Kimi Code | `KIMI_API_KEY` | 支持 | K2.5，性价比高 |
| 智谱 Coding | `ZHIPU_API_KEY` | 支持 | GLM-5，中文友好 |
| Kimi | `KIMI_API_KEY` | 不支持 | Moonshot |
| 智谱 | `ZHIPU_API_KEY` | 不支持 | GLM-4 |
| 通义千问 | `QWEN_API_KEY` | 不支持 | Qwen |
| OpenAI | `OPENAI_API_KEY` | 不支持 | GPT-4 |

## 技能系统

在 `~/.kodax/skills/` 创建自定义技能：

**Python 技能**（灵活，可执行工具）：
```python
# ~/.kodax/skills/commit.py

def skill_commit(agent, args: str) -> str:
    """根据 git diff 生成 commit 消息"""  # <- 自动提取为描述
    diff = agent.execute_tool("bash", {"command": "git diff --staged"})
    if not diff.strip():
        return "没有暂存的更改。"
    return agent.call_llm([{"role": "user", "content": f"生成 commit 消息：\n{diff}"}])
```

**Markdown 技能**（简单，纯提示词）：
```markdown
# ~/.kodax/skills/review.md

# 代码审查

审查代码的以下方面：
- Bug 和错误
- 安全问题
- 性能问题
- 代码风格
```

```bash
uv run kodax_agent.py              # 列出所有技能及描述
uv run kodax_agent.py /commit      # 执行技能
uv run kodax_agent.py /review src/main.py
```

## 命令选项

| 选项 | 说明 |
|------|------|
| `--provider NAME` | 指定大模型 |
| `--thinking` | 开启思考模式 |
| `--no-confirm` | 跳过确认 |
| `--session resume\|list` | 会话管理 |
| `--parallel` | 并行执行工具 |
| `--team TASKS` | 多 Agent 并行 |

## 原理

Kodax 是一个简单的 Agent 循环：

1. 把你的任务 + 可用工具发给大模型
2. 大模型返回文本和/或工具调用
3. 执行工具，把结果发回去
4. 重复直到完成

核心逻辑只有 ~100 行。读 [kodax_agent.py](../kodax_agent.py) 就能完全理解它是怎么工作的。

## 文档

- [设计文档](DESIGN.md) - 架构和实现细节
- [测试指南](TESTING.md) - 如何测试所有功能
- [English README](../README.md) - 英文版

## 许可证

MIT
