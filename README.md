# Kodax Agent

An extremely lightweight Coding Agent.

## Quick Start

```bash
# Install dependencies
uv sync

# Run
uv run kodax_agent.py "your coding task"
```

## Supported Models

| Provider | Environment Variable | Description |
|----------|---------------------|-------------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude (default) |
| Kimi | `KIMI_API_KEY` | Moonshot (OpenAI compatible) |
| **Kimi Code** | `KIMI_API_KEY` | Kimi K2.5 Thinking (Anthropic compatible) |
| Zhipu AI | `ZHIPU_API_KEY` | GLM (zhipuai SDK) |
| **Zhipu Coding** | `ZHIPU_API_KEY` | GLM-5 (Anthropic compatible, supports Thinking) |
| Qwen | `QWEN_API_KEY` | Tongyi Qianwen (OpenAI compatible) |
| OpenAI | `OPENAI_API_KEY` | GPT (OpenAI compatible) |

### Recommended Coding Plans

Kimi Code and Zhipu Coding Plan offer cost-effective coding subscriptions:

```bash
# Kimi Code - Supports Thinking Mode and tool calling
uv run kodax_agent.py --provider kimi-code --thinking "complex task"

# Zhipu GLM Coding Plan - Supports Thinking Mode
uv run kodax_agent.py --provider zhipu-coding --thinking "complex task"
```

## Usage Examples

```bash
# Basic usage
uv run kodax_agent.py "create an HTTP server"

# Disable confirmations
uv run kodax_agent.py --no-confirm "delete temporary files"

# Specify provider
uv run kodax_agent.py --provider kimi "your task"

# Enable Thinking Mode (only Anthropic, Kimi Code, Zhipu Coding supported)
uv run kodax_agent.py --provider kimi-code --thinking "complex task"

# Use skills
uv run kodax_agent.py /commit
uv run kodax_agent.py /explain kodax_agent.py

# Resume session
uv run kodax_agent.py --session resume "continue task"
```

## P2: Parallel Execution

### Parallel Tool Execution

When the LLM returns multiple tool calls, execute them in parallel for better efficiency:

```bash
uv run kodax_agent.py --parallel "read all config files in src/ directory"
```

### Agent Team

Run multiple sub-agents in parallel for different tasks:

```bash
# Execute multiple tasks in parallel
uv run kodax_agent.py --team "analyze src/ structure,check test coverage,find TODO comments"

# With Thinking Mode
uv run kodax_agent.py --provider kimi-code --thinking --team "code review,performance analysis"
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--provider NAME` | Specify LLM provider |
| `--thinking` | Enable Thinking Mode (for complex reasoning) |
| `--confirm TOOLS` | Specify tools requiring confirmation |
| `--no-confirm` | Disable all confirmations |
| `--session resume\|list` | Session management |
| `--parallel` | Execute multiple tool calls in parallel (P2) |
| `--team TASKS` | Run multiple sub-agents in parallel (P2) |

## Feature Status

| Priority | Feature | Status |
|----------|---------|--------|
| P0 | Confirmation mechanism | ✅ Done |
| P0 | Streaming output | ✅ Done |
| P1 | Context compression | ✅ Done |
| P1 | Session persistence | ✅ Done |
| P1 | Skill system | ✅ Done |
| P1 | Multi-model support | ✅ Done |
| P2 | Parallel tool execution | ✅ Done |
| P2 | Agent Team | ✅ Done |

## Documentation

- [Design Document](docs/DESIGN.md) - Detailed architecture and implementation
- [Testing Guide](docs/TESTING.md) - Manual testing instructions
- [中文文档](docs/README_CN.md) - Chinese README
