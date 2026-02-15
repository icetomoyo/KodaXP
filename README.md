# KodaXP

<div align="center">

**A lightweight AI coding assistant that actually works.**

Single file • ~2000 LOC • 7 LLM providers • Streaming • Parallel execution • Long-running mode

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

## Why KodaXP?

**Transparent** • **Flexible** • **Powerful**

KodaXP is designed for developers who want to **understand**, **customize**, and **control** their AI coding assistant.

| What | KodaXP | Others |
|------|--------|--------|
| **Code** | Single file (~2000 LOC), read in 30 minutes | Thousands of files, hard to understand |
| **Providers** | 7 LLM providers, switch freely | Usually locked to one provider |
| **Cost** | Use cheap models (Kimi, Zhipu, Qwen) | Often requires expensive subscriptions |
| **Long-Running** | Feature tracking with auto-continue | Usually requires manual oversight |
| **Customization** | Modify the code directly | Complex plugin systems |
| **Learning** | Perfect for understanding how agents work | Black box |

**When to use KodaXP:**
- You want to **learn** how AI coding agents work
- You need **flexibility** across multiple LLM providers
- You want to **customize** the agent for your workflow
- You need **long-running** autonomous development
- You prefer **transparency** over magic

**When to use others:**
- You need a **production-ready** solution out of the box
- You want **IDE integration** (Cursor, Windsurf)
- You need **advanced features** beyond basic coding tasks

## Features

- **One File** - Everything in `kodaxp.py`. Read it, modify it, ship it.
- **7 Providers** - Anthropic, OpenAI, Kimi, Kimi Code, Zhipu, Zhipu Coding, Qwen
- **Streaming** - Real-time output, no waiting
- **Session Memory** - Conversations persist across runs
- **Long-Running Mode** - Feature tracking with `feature_list.json` and `PROGRESS.md`
- **Parallel Tools** - Execute multiple tools simultaneously
- **Skills** - Extend with custom Python functions
- **Thinking Mode** - Deep reasoning for complex tasks (supported providers)
- **Context Aware** - Auto-injects Git status and project structure
- **Undo Support** - Revert file modifications with the undo tool
- **Cross-Platform** - Works on Windows, macOS, and Linux

## Quick Start

```bash
# Install
git clone https://github.com/icetomoyo/KodaXP.git
cd KodaXP
uv sync

# Set your API key
export ANTHROPIC_API_KEY=your-key    # or KIMI_API_KEY, ZHIPU_API_KEY, etc.

# Run
uv run kodaxp.py "create a REST API with FastAPI"
```

## Usage

```bash
# Basic
uv run kodaxp.py "your coding task"

# Use a different provider
uv run kodaxp.py --provider kimi-code "your task"

# Enable thinking mode for complex tasks
uv run kodaxp.py --provider zhipu-coding --thinking "refactor this codebase"

# Resume previous conversation
uv run kodaxp.py --session resume "continue working on the API"

# Parallel execution (faster for multi-file tasks)
uv run kodaxp.py --parallel "read all markdown files and summarize"

# Run multiple tasks in parallel
uv run kodaxp.py --team "analyze code structure,check test coverage,find bugs"
```

## Supported Providers

| Provider | API Key | Thinking | Notes |
|----------|---------|----------|-------|
| Zhipu Coding | `ZHIPU_API_KEY` | Yes | GLM-5, Chinese-friendly (default) |
| Kimi Code | `KIMI_API_KEY` | Yes | K2.5, great value |
| Anthropic | `ANTHROPIC_API_KEY` | Yes | Claude |
| Kimi | `KIMI_API_KEY` | No | Moonshot |
| Zhipu | `ZHIPU_API_KEY` | No | GLM-4 |
| Qwen | `QWEN_API_KEY` | No | Tongyi |
| OpenAI | `OPENAI_API_KEY` | No | GPT-4 |

## Skills

Create custom skills in `~/.kodaxp/skills/`:

**Python skill** (flexible, can execute tools):
```python
# ~/.kodaxp/skills/commit.py

def skill_commit(agent, args: str) -> str:
    """Generate commit message from git diff"""  # <- This becomes the description
    diff = agent.execute_tool("bash", {"command": "git diff --staged"})
    if not diff.strip():
        return "No staged changes."
    return agent.call_llm([{"role": "user", "content": f"Generate commit message:\n{diff}"}])
```

**Markdown skill** (simple, pure prompts):
```markdown
# ~/.kodaxp/skills/review.md

# Code Review

Review the code for:
- Bugs and errors
- Security issues
- Performance problems
- Code style
```

```bash
uv run kodaxp.py              # List all skills with descriptions
uv run kodaxp.py /commit      # Execute skill
uv run kodaxp.py /review src/main.py
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
| `--init TASK` | Initialize a long-running task |
| `--append` | With --init: append to existing features |
| `--overwrite` | With --init: overwrite existing features |
| `--auto-continue` | Auto-continue until all features pass |
| `--max-iter N` | Max iterations per session (default: 50) |
| `--max-sessions N` | Max sessions for --auto-continue (default: 50) |
| `--max-hours H` | Max hours for --auto-continue (default: 2.0) |

## Best Practices

### Running Kodax

**Option 1: Direct Execution (Recommended for Development)**
```bash
uv run kodaxp.py "your task"
```
- Code changes take effect immediately
- Best for development and debugging

**Option 2: Install as Global Tool**
```bash
uv tool install -e .
kodaxp "your task"
```
- Shorter command, available from any directory
- `-e` flag means editable mode (code changes still work)
- Uninstall with `uv tool uninstall kodaxp`

### Setting Default Provider

**Option 1: Environment Variable**
```bash
export KODAX_PROVIDER=kimi-code
uv run kodaxp.py "your task"  # Uses kimi-code
```

**Option 2: Shell Alias**
```bash
# Add to ~/.bashrc or ~/.zshrc
alias kodaxp='uv run /path/to/KodaXP/kodaxp.py --provider kimi-code'
```

**Priority**: `--provider` CLI arg > `KODAX_PROVIDER` env > default (zhipu-coding)

### API Keys

Set the API key for your provider:
```bash
export ZHIPU_API_KEY=your-key      # Zhipu Coding (default)
export KIMI_API_KEY=your-key       # Kimi / Kimi Code
export ANTHROPIC_API_KEY=your-key  # Anthropic Claude
export QWEN_API_KEY=your-key       # Qwen
export OPENAI_API_KEY=your-key     # OpenAI
```

### Tips

- Use `--thinking` for complex reasoning tasks (supported: zhipu-coding, kimi-code, anthropic)
- Use `--parallel` for tasks involving multiple independent files
- Use `--team` for unrelated parallel tasks (e.g., "analyze code,write tests,update docs")
- Sessions are project-scoped (based on git root), so you won't mix contexts

## Long-Running Tasks

For complex projects that span multiple sessions, use `--init` to set up a long-running task:

```bash
# Initialize
uv run kodaxp.py --init "build a claude.ai clone"

# This creates:
# - feature_list.json (all features with passes: false)
# - PROGRESS.md (progress log)

# Continue work (auto-detects long-running mode)
uv run kodaxp.py "continue development"

# Resume next day
uv run kodaxp.py --session resume "continue yesterday's work"
```

### Auto-Continue Mode

For fully autonomous development until all features are complete:

```bash
# Initialize first
uv run kodaxp.py --init "build a REST API with authentication"

# Auto-continue until all features pass (with safety limits)
uv run kodaxp.py --auto-continue

# With custom limits
uv run kodaxp.py --auto-continue --max-sessions 20 --max-hours 4.0
```

Auto-continue stops automatically when:
- All features in `feature_list.json` have `passes: true`
- Max sessions reached (default: 50)
- Max hours reached (default: 2.0)
- Consecutive errors exceed threshold

### Incremental Development

After completing a project, you can add new features without losing history:

```bash
# Project already completed (all features pass)
# Now add new features:

# Option 1: Append new features (recommended)
uv run kodaxp.py --init "add search functionality" --append
uv run kodaxp.py --auto-continue

# Option 2: Start fresh (lose history)
uv run kodaxp.py --init "new project" --overwrite
```

**Use `--append` for:**
- Adding new features
- Bug fixes (as new features)
- Refactoring tasks
- Performance optimizations

**How it works:**
- New features are appended to existing `feature_list.json`
- Completed features (`passes: true`) are preserved
- `--auto-continue` only processes incomplete features

Based on [Anthropic's research](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) on long-running agents.

## How It Works

KodaXP is a simple agent loop:

1. Send your task + available tools to the LLM
2. LLM responds with text and/or tool calls
3. Execute tools, send results back
4. Repeat until done

The entire code is in a single file (~2000 LOC). Read [kodaxp.py](kodaxp.py) to understand exactly how it works.

Core components:
- **Provider abstraction**: 7 LLM providers with unified interface
- **Tool system**: read, write, edit, glob, grep, bash, undo
- **Session management**: Persistent conversations with project scoping
- **Long-running mode**: Feature tracking with auto-continue
- **Context enhancement**: Git status, project snapshot, platform info

## Documentation

- [Design Document](docs/DESIGN.md) - Architecture and implementation details
- [Long-Running Guide](docs/LONG_RUNNING_GUIDE.md) - Best practices and prompt templates for `--init`
- [Testing Guide](docs/TESTING.md) - How to test all features
- [中文文档](docs/README_CN.md) - Chinese README

## Version History

### v0.6.2 (2026-02-15)

- **Environment Awareness**: Platform context injection for cross-platform commands
  - Auto-detects Windows and suggests correct commands (move, dir, del)
  - Helps Agent avoid platform-specific command errors
  - ~18 lines of code, minimal token overhead

### v0.6.1 (2026-02-15)

- **Plan Before Action**: Thinking guidance in SYSTEM_PROMPT for all modes
- **Session Planning**: Automatic session plan creation in long-running mode

### v0.1.0 (2026-02-14)

- **Incremental Development**: Support for adding features to completed projects
  - `--append` flag to add new features to existing `feature_list.json`
  - `--overwrite` flag to start fresh
  - Warning when running `--init` on existing project
- **Error Handling Enhancement**: Improved error messages and recovery guidance
  - Error messages now show tool name and missing parameter clearly
  - Added explicit error handling guidance in system prompt
  - Model is instructed not to repeat the same tool call errors
- **Hard Timeout**: Bash commands capped at 300s max (configurable)
- **Windows Compatibility**: Smart decode (UTF-8 first, OEM fallback) for bash output
- **Documentation**: Added LONG_RUNNING_GUIDE.md with best practices

## License

MIT
