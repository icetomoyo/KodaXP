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
- **上下文感知** - 自动注入 Git 状态和项目结构
- **撤销支持** - 使用 undo 工具撤销文件修改
- **跨平台** - 支持 Windows、macOS 和 Linux

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
| 智谱 Coding | `ZHIPU_API_KEY` | 支持 | GLM-5，中文友好（默认） |
| Kimi Code | `KIMI_API_KEY` | 支持 | K2.5，性价比高 |
| Anthropic | `ANTHROPIC_API_KEY` | 支持 | Claude |
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
| `--init TASK` | 初始化长时间运行任务 |
| `--auto-continue` | 自动继续直到所有功能完成 |
| `--max-iter N` | 单次会话最大迭代次数（默认：50） |
| `--max-sessions N` | --auto-continue 最大会话数（默认：50） |
| `--max-hours H` | --auto-continue 最大小时数（默认：2.0） |

## 最佳实践

### 运行方式

**方式一：直接运行（推荐开发时使用）**
```bash
uv run kodax_agent.py "你的任务"
```
- 代码修改立即生效
- 适合开发调试

**方式二：安装后使用**
```bash
uv pip install -e .
kodax "你的任务"
```
- 命令更短
- `-e` 表示可编辑模式，代码修改仍然生效

### 设置默认 Provider

**方式一：环境变量**
```bash
export KODAX_PROVIDER=kimi-code
uv run kodax_agent.py "你的任务"  # 使用 kimi-code
```

**方式二：Shell Alias**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
alias kodax='uv run /path/to/KodaX/kodax_agent.py --provider kimi-code'
```

**优先级**：`--provider` 命令行参数 > `KODAX_PROVIDER` 环境变量 > 默认值 (zhipu-coding)

### API Key 配置

```bash
export ZHIPU_API_KEY=your-key      # 智谱 Coding（默认）
export KIMI_API_KEY=your-key       # Kimi / Kimi Code
export ANTHROPIC_API_KEY=your-key  # Anthropic Claude
export QWEN_API_KEY=your-key       # 通义千问
export OPENAI_API_KEY=your-key     # OpenAI
```

### 使用技巧

- 复杂推理任务使用 `--thinking`（支持：zhipu-coding、kimi-code、anthropic）
- 涉及多个独立文件的任务使用 `--parallel`
- 不相关的并行任务使用 `--team`（如："分析代码,写测试,更新文档"）
- 会话是项目级别的（基于 git root），不会混淆上下文

## 长时间运行任务

对于需要跨多个 session 完成的复杂项目，使用 `--init` 初始化：

```bash
# 初始化
uv run kodax_agent.py --init "构建 claude.ai 克隆"

# 这会创建：
# - feature_list.json (所有功能，初始 passes: false)
# - PROGRESS.md (进度日志)

# 继续工作（自动检测长运行模式）
uv run kodax_agent.py "继续开发"

# 第二天继续
uv run kodax_agent.py --session resume "继续昨天的工作"
```

### 自动继续模式

完全自主开发，直到所有功能完成：

```bash
# 先初始化
uv run kodax_agent.py --init "构建带认证的 REST API"

# 自动继续直到所有功能通过（带安全限制）
uv run kodax_agent.py --auto-continue

# 自定义限制
uv run kodax_agent.py --auto-continue --max-sessions 20 --max-hours 4.0
```

自动继续会在以下情况停止：
- `feature_list.json` 中所有功能都标记为 `passes: true`
- 达到最大会话数（默认：50）
- 达到最大小时数（默认：2.0）
- 连续错误超过阈值

基于 [Anthropic 研究](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) 实现的长运行代理能力。

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
