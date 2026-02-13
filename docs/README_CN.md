# Kodax Agent

极致轻量化 Coding Agent

## 快速开始

```bash
# 安装依赖
uv sync

# 运行
uv run kodax_agent.py "你的编程任务"
```

## 支持的模型

| Provider | 环境变量 | 说明 |
|----------|----------|------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude (默认) |
| Kimi | `KIMI_API_KEY` | Moonshot (OpenAI 兼容) |
| **Kimi Code** | `KIMI_API_KEY` | Kimi K2.5 Thinking (Anthropic 兼容) |
| 智谱AI | `ZHIPU_API_KEY` | GLM (zhipuai SDK) |
| **智谱 Coding** | `ZHIPU_API_KEY` | GLM-5 (Anthropic 兼容, 支持 Thinking) |
| Qwen | `QWEN_API_KEY` | 通义千问 (OpenAI 兼容) |
| OpenAI | `OPENAI_API_KEY` | GPT (OpenAI 兼容) |

### Coding Plan 推荐配置

Kimi Code 和 智谱 Coding Plan 提供更优惠的 Coding 套餐：

```bash
# Kimi Code - 支持 Thinking Mode 和工具调用
uv run kodax_agent.py --provider kimi-code --thinking "复杂任务"

# 智谱 GLM Coding Plan - 支持 Thinking Mode
uv run kodax_agent.py --provider zhipu-coding --thinking "复杂任务"
```

## 使用示例

```bash
# 基本使用
uv run kodax_agent.py "创建一个 HTTP 服务器"

# 禁用确认
uv run kodax_agent.py --no-confirm "删除临时文件"

# 指定 Provider
uv run kodax_agent.py --provider kimi "你的任务"

# 启用 Thinking Mode (仅 Anthropic, Kimi Code, 智谱 Coding 支持)
uv run kodax_agent.py --provider kimi-code --thinking "复杂任务"

# 使用 Skill
uv run kodax_agent.py /commit
uv run kodax_agent.py /explain kodax_agent.py

# 恢复会话
uv run kodax_agent.py --session resume "继续任务"
```

## P2: 并行执行

### 并行工具执行

当 LLM 返回多个工具调用时，可以并行执行以提高效率：

```bash
uv run kodax_agent.py --parallel "读取 src/ 目录下的所有配置文件"
```

### Agent Team

运行多个子 Agent 并行执行不同任务：

```bash
# 多个任务并行执行
uv run kodax_agent.py --team "分析 src/ 目录结构,检查测试覆盖率,查找 TODO 注释"

# 使用 Thinking Mode
uv run kodax_agent.py --provider kimi-code --thinking --team "代码审查,性能分析"
```

## CLI 选项

| 选项 | 说明 |
|------|------|
| `--provider NAME` | 指定 LLM Provider |
| `--thinking` | 启用 Thinking Mode (复杂推理任务) |
| `--confirm TOOLS` | 指定需要确认的工具 |
| `--no-confirm` | 禁用所有确认 |
| `--session resume\|list` | 会话管理 |
| `--parallel` | 并行执行多个工具调用 (P2) |
| `--team TASKS` | 运行多个子 Agent 并行 (P2) |

## 功能状态

| 优先级 | 功能 | 状态 |
|--------|------|------|
| P0 | 确认机制 | ✅ 已完成 |
| P0 | 流式输出 | ✅ 已完成 |
| P1 | 上下文压缩 | ✅ 已完成 |
| P1 | 会话持久化 | ✅ 已完成 |
| P1 | Skill 系统 | ✅ 已完成 |
| P1 | 多模型支持 | ✅ 已完成 |
| P2 | 工具并行执行 | ✅ 已完成 |
| P2 | Agent Team | ✅ 已完成 |

## 文档

- [设计文档](DESIGN.md) - 详细的架构和实现
- [测试指南](TESTING.md) - 手动测试说明
- [English README](../README.md) - 英文版 README
