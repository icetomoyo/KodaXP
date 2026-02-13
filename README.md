# Kodax Agent

<div align="center">

**A lightweight AI coding assistant that actually works.**

Single file • ~800 LOC • 7 LLM providers • Streaming • Parallel execution

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## Why Kodax?

Other AI coding assistants are bloated. Kodax is **one file**, **zero config**, and supports **7 LLM providers** out of the box.

```
# Compare
Claude Code:   ~50,000 LOC, $20/month
Aider:         ~15,000 LOC, complex setup
Kodax:           ~800 LOC, uv sync && go
```

## Features

- **One File** - Everything in `kodax_agent.py`. Read it, modify it, ship it.
- **7 Providers** - Anthropic, OpenAI, Kimi, Kimi Code, Zhipu, Zhipu Coding, Qwen
- **Streaming** - Real-time output, no waiting
- **Session Memory** - Conversations persist across runs
- **Parallel Tools** - Execute multiple tools simultaneously
- **Skills** - Extend with custom Python functions
- **Thinking Mode** - Deep reasoning for complex tasks (supported providers)

## Quick Start

```bash
# Install
git clone https://github.com/icetomoyo/KodaX.git
cd KodaX
uv sync

# Set your API key
export ANTHROPIC_API_KEY=your-key    # or KIMI_API_KEY, ZHIPU_API_KEY, etc.

# Run
uv run kodax_agent.py "create a REST API with FastAPI"
```

## Usage

```bash
# Basic
uv run kodax_agent.py "your coding task"

# Use a different provider
uv run kodax_agent.py --provider kimi-code "your task"

# Enable thinking mode for complex tasks
uv run kodax_agent.py --provider zhipu-coding --thinking "refactor this codebase"

# Resume previous conversation
uv run kodax_agent.py --session resume "continue working on the API"

# Parallel execution (faster for multi-file tasks)
uv run kodax_agent.py --parallel "read all markdown files and summarize"

# Run multiple tasks in parallel
uv run kodax_agent.py --team "analyze code structure,check test coverage,find bugs"
```

## Supported Providers

| Provider | API Key | Thinking | Notes |
|----------|---------|----------|-------|
| Anthropic | `ANTHROPIC_API_KEY` | Yes | Claude (default) |
| Kimi Code | `KIMI_API_KEY` | Yes | K2.5, great value |
| Zhipu Coding | `ZHIPU_API_KEY` | Yes | GLM-5, Chinese-friendly |
| Kimi | `KIMI_API_KEY` | No | Moonshot |
| Zhipu | `ZHIPU_API_KEY` | No | GLM-4 |
| Qwen | `QWEN_API_KEY` | No | Tongyi |
| OpenAI | `OPENAI_API_KEY` | No | GPT-4 |

## Skills

Create custom skills in `~/.kodax/skills/`:

**Python skill** (flexible, can execute tools):
```python
# ~/.kodax/skills/commit.py

def skill_commit(agent, args: str) -> str:
    """Generate commit message from git diff"""  # <- This becomes the description
    diff = agent.execute_tool("bash", {"command": "git diff --staged"})
    if not diff.strip():
        return "No staged changes."
    return agent.call_llm([{"role": "user", "content": f"Generate commit message:\n{diff}"}])
```

**Markdown skill** (simple, pure prompts):
```markdown
# ~/.kodax/skills/review.md

# Code Review

Review the code for:
- Bugs and errors
- Security issues
- Performance problems
- Code style
```

```bash
uv run kodax_agent.py              # List all skills with descriptions
uv run kodax_agent.py /commit      # Execute skill
uv run kodax_agent.py /review src/main.py
```

## CLI Options

| Option | Description |
|--------|-------------|
| `--provider NAME` | LLM provider to use |
| `--thinking` | Enable extended thinking |
| `--no-confirm` | Skip confirmations |
| `--session resume\|list` | Session management |
| `--parallel` | Parallel tool execution |
| `--team TASKS` | Run multiple agents in parallel |

## How It Works

Kodax is a simple agent loop:

1. Send your task + available tools to the LLM
2. LLM responds with text and/or tool calls
3. Execute tools, send results back
4. Repeat until done

The entire core logic is ~100 lines. Read [kodax_agent.py](kodax_agent.py) to understand exactly how it works.

## Documentation

- [Design Document](docs/DESIGN.md) - Architecture and implementation details
- [Testing Guide](docs/TESTING.md) - How to test all features
- [中文文档](docs/README_CN.md) - Chinese README

## License

MIT
