# KodaXP 设计文档

> 极致轻量化 Coding Agent - 单文件实现，功能完整

---

## 1. 设计理念

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **单文件** | 所有代码在一个文件中，便于阅读和修改 |
| **功能完整** | 支持 7 种 LLM、长运行模式、并行执行等 |
| **标准库优先** | 文件操作、进程管理使用 Python 标准库 |
| **可扩展** | Skill 系统支持自定义功能 |

### 1.2 实际指标

```
代码总量:      ~2000 LOC
Provider 层:   ~600 LOC
工具实现:      ~400 LOC
长运行模式:    ~300 LOC
核心循环:      ~200 LOC
```

### 1.3 与其他工具的对比

| 特性 | 其他 Agent | KodaXP |
|------|-----------|--------|
| **代码量** | 成千上万行 | ~2000 行单文件 |
| **理解难度** | 高 | 低（30分钟读完） |
| **定制性** | 复杂插件系统 | 直接修改代码 |
| **长运行** | 通常不支持 | 完整支持 |

---

## 2. 架构概览

```
┌─────────────────────────────────────────┐
│           kodaxp.py (~2000 LOC)    │
│                                          │
│  ┌─────────┐ ┌─────────┐ ┌────────────┐ │
│  │ Config  │ │  Tools  │ │ Agent Loop │ │
│  │ (~50行) │ │ (~400行)│ │  (~200行)  │ │
│  └─────────┘ └─────────┘ └────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐│
│  │      Tool Execution (~200行)         ││
│  │  read | write | edit | bash | glob  ││
│  │  grep | undo                         ││
│  └─────────────────────────────────────┘│
│                                          │
│  ┌─────────────────────────────────────┐│
│  │       Provider Layer (~600行)        ││
│  │  anthropic | kimi | kimi-code       ││
│  │  qwen | openai | zhipu | zhipu-coding││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

---

## 3. 已实现功能 (P0)

### 3.1 核心 Agent 循环

```python
def main():
    messages = [{"role": "user", "content": user_prompt}]

    while iteration < max_iterations:
        # 流式调用 LLM
        text_blocks, tool_blocks = stream_llm(messages)

        # 添加 assistant 响应
        messages.append({"role": "assistant", "content": assistant_content})

        # 如果没有工具调用，结束
        if not tool_blocks:
            break

        # 执行工具调用
        for tool_call in tool_blocks:
            result = execute_tool(tool_name, tool_input, confirm_tools)
            tool_results.append(result)

        # 添加工具结果
        messages.append({"role": "user", "content": tool_results})
```

### 3.2 工具系统

**工具定义**:
```python
TOOLS = [
    {
        "name": "read",
        "description": "Read the contents of a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The absolute path"}
            },
            "required": ["path"]
        }
    },
    # write, edit, bash, glob, grep ...
]
```

**工具执行**:
```python
def execute_tool(name: str, input_data: dict, confirm_tools: set) -> str:
    # 确认机制
    if name in confirm_tools:
        response = input(f"[Confirm] Execute {name}? [y/N]: ")
        if response.lower() != 'y':
            return "Operation cancelled by user"

    match name:
        case "read":
            return Path(input_data["path"]).read_text(encoding="utf-8")
        case "write":
            # ...
        case "edit":
            # ...
        case "bash":
            # ...
        case "glob":
            # ...
        case "grep":
            # ...
```

### 3.3 确认机制

**默认需要确认的工具**: `bash`, `write`, `edit`

**CLI 选项**:
```bash
# 默认模式
uv run kodaxp.py "你的任务"

# 自定义确认列表
uv run kodaxp.py --confirm bash,write "你的任务"

# 禁用所有确认
uv run kodaxp.py --no-confirm "你的任务"
```

### 3.4 流式输出

```python
def stream_llm(messages: list) -> tuple[list, list]:
    """流式调用 LLM，返回 (text_blocks, tool_blocks)"""
    with get_client().messages.stream(...) as stream:
        for event in stream:
            if event.type == "content_block_delta":
                if event.delta.type == "text_delta":
                    print(event.delta.text, end="", flush=True)

        final_message = stream.get_final_message()
        # 分类处理 content blocks
        ...

    return text_blocks, tool_blocks
```

---

## 4. 多模型支持 (P1)

### 4.1 支持的 Provider

| Provider | 环境变量 | 默认模型 | 兼容类型 | Thinking |
|----------|----------|----------|----------|----------|
| **智谱 Coding** | `ZHIPU_API_KEY` | glm-5 | Anthropic | ✅ (默认) |
| **Kimi Code** | `KIMI_API_KEY` | k2p5 | Anthropic | ✅ |
| **Anthropic** | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 | 原生 | ✅ |
| **Kimi (Moonshot)** | `KIMI_API_KEY` | moonshot-v1-128k | OpenAI | ❌ |
| **智谱AI** | `ZHIPU_API_KEY` | glm-4-plus | zhipuai SDK | ❌ |
| **Qwen (阿里云)** | `QWEN_API_KEY` | qwen-max | OpenAI | ❌ |
| **OpenAI** | `OPENAI_API_KEY` | gpt-4o | 原生 | ❌ |

### 4.2 Provider 抽象设计

```python
from abc import ABC, abstractmethod

class Provider(ABC):
    @abstractmethod
    def stream(self, messages: list, tools: list, system: str, thinking: bool = False) -> tuple[list, list]:
        """流式调用，返回 (text_blocks, tool_blocks)"""
        pass
```

### 4.3 Anthropic Provider

```python
class AnthropicProvider(Provider):
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"

    def stream(self, messages, tools, system, thinking=False):
        text_blocks, tool_blocks = [], []
        current_text = ""

        kwargs = {"model": self.model, "max_tokens": MAX_TOKENS, "system": system, "tools": tools, "messages": messages}
        if thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}

        with self.client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        print(event.delta.text, end="", flush=True)
                        current_text += event.delta.text
                    elif event.delta.type == "thinking_delta" and thinking:
                        print(f"\n\033[90m[Thinking] {event.delta.thinking[:200]}...\033[0m", flush=True)

            final = stream.get_final_message()
            for block in final.content:
                if block.type == "text" and block.text:
                    text_blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    tool_blocks.append(block)

        return text_blocks, tool_blocks
```

### 4.4 OpenAI 兼容 Provider (Kimi, Qwen, OpenAI)

```python
from openai import OpenAI

class OpenAICompatProvider(Provider):
    """OpenAI 兼容 API 基类"""
    BASE_URL: str
    API_KEY_ENV: str
    MODEL: str

    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get(self.API_KEY_ENV), base_url=self.BASE_URL)

    def stream(self, messages, tools, system, thinking=False):
        full_messages = [{"role": "system", "content": system}] + messages
        text_content = ""
        tool_calls_map = {}

        response = self.client.chat.completions.create(model=self.MODEL, messages=full_messages, tools=tools, stream=True)

        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                text_content += delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index not in tool_calls_map:
                        tool_calls_map[tc.index] = {"id": tc.id, "name": "", "arguments": ""}
                    if tc.function:
                        tool_calls_map[tc.index]["name"] = tc.function.name or tool_calls_map[tc.index]["name"]
                        tool_calls_map[tc.index]["arguments"] += tc.function.arguments or ""

        text_blocks = [{"type": "text", "text": text_content}] if text_content else []
        tool_blocks = [{"id": v["id"], "name": v["name"], "input": json.loads(v["arguments"])} for v in tool_calls_map.values()]
        return text_blocks, tool_blocks


class KimiProvider(OpenAICompatProvider):
    """Kimi (Moonshot) OpenAI 兼容接口"""
    BASE_URL = "https://api.moonshot.cn/v1"
    API_KEY_ENV = "KIMI_API_KEY"
    MODEL = "moonshot-v1-128k"


class QwenProvider(OpenAICompatProvider):
    """通义千问 OpenAI 兼容接口"""
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    API_KEY_ENV = "QWEN_API_KEY"
    MODEL = "qwen-max"


class OpenAIProvider(OpenAICompatProvider):
    """OpenAI GPT 模型"""
    BASE_URL = "https://api.openai.com/v1"
    API_KEY_ENV = "OPENAI_API_KEY"
    MODEL = "gpt-4o"
```

### 4.5 Anthropic 兼容 Provider (Kimi Code, GLM Coding Plan)

> 这些 Provider 提供与 Anthropic API 完全兼容的接口，支持 Thinking Mode 和工具调用。

```python
class AnthropicCompatProvider(Provider):
    """Anthropic 兼容 API 基类 (用于 Kimi Code, GLM Coding Plan)"""
    BASE_URL: str
    API_KEY_ENV: str
    MODEL: str

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(
            api_key=os.environ.get(self.API_KEY_ENV),
            base_url=self.BASE_URL
        )

    def stream(self, messages, tools, system, thinking=False):
        # 与 AnthropicProvider 实现相同
        ...


class KimiCodeProvider(AnthropicCompatProvider):
    """Kimi Code Anthropic 兼容接口 - 支持工具调用和 Thinking

    文档: https://www.kimi.com/code/docs/more/third-party-agents.html
    Model: k2p5 (Kimi K2.5 Thinking)
    """
    BASE_URL = "https://api.kimi.com/coding/"
    API_KEY_ENV = "KIMI_API_KEY"
    MODEL = "k2p5"


class ZhipuCodingProvider(AnthropicCompatProvider):
    """智谱 AI GLM Coding Plan - Anthropic 兼容接口"""
    BASE_URL = "https://open.bigmodel.cn/api/anthropic"
    API_KEY_ENV = "ZHIPU_API_KEY"
    MODEL = "glm-5"
```

**Coding Plan 优势**:
- **Kimi Code**: 最高 100 tokens/s 输出速度，256K 上下文
- **智谱 Coding**: GLM-5 模型，100元/月约等于 Claude Code $100 的 3 倍额度

### 4.6 智谱 AI Provider (zhipuai SDK)

```python
from zhipuai import ZhipuAI

class ZhipuProvider(Provider):
    """智谱 AI GLM 模型 (zhipuai SDK)"""
    def __init__(self):
        self.client = ZhipuAI(api_key=os.environ.get("ZHIPU_API_KEY"))
        self.model = "glm-4-plus"

    def stream(self, messages, tools, system, thinking=False):
        full_messages = [{"role": "system", "content": system}] + messages
        text_content = ""
        tool_calls_map = {}

        response = self.client.chat.completions.create(model=self.model, messages=full_messages, tools=tools, stream=True)

        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                print(delta.content, end="", flush=True)
                text_content += delta.content
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index if hasattr(tc, 'index') else 0
                    if idx not in tool_calls_map:
                        tool_calls_map[idx] = {"id": tc.id, "name": "", "arguments": ""}
                    if tc.function:
                        tool_calls_map[idx]["name"] = tc.function.name or tool_calls_map[idx]["name"]
                        tool_calls_map[idx]["arguments"] += tc.function.arguments or ""

        text_blocks = [{"type": "text", "text": text_content}] if text_content else []
        tool_blocks = [{"id": v["id"], "name": v["name"], "input": json.loads(v["arguments"])} for v in tool_calls_map.values()]
        return text_blocks, tool_blocks
```

### 4.7 CLI 配置

**优先级**: `--provider` 命令行参数 > `KODAX_PROVIDER` 环境变量 > 默认值 (zhipu-coding)

```bash
# 使用默认 Provider (zhipu-coding)
uv run kodaxp.py "你的任务"

# 方式 1: 环境变量设置默认 Provider
export KODAX_PROVIDER=kimi-code
export KIMI_API_KEY=your-key
uv run kodaxp.py "你的任务"

# 方式 2: 命令行参数覆盖
uv run kodaxp.py --provider anthropic "你的任务"

# 启用 Thinking Mode (仅 Anthropic, Kimi Code, 智谱 Coding 支持)
uv run kodaxp.py --provider zhipu-coding --thinking "复杂任务"
```

### 4.8 依赖配置

```toml
# pyproject.toml
dependencies = [
    "anthropic>=0.40.0",
    "openai>=1.0.0",
    "zhipuai>=2.0.0",
    "httpx>=0.27.0",
]
```

---

## 5. Skill 系统 (P1)

### 5.1 设计目标

- **动态加载**: 无需重启即可添加新 skill
- **两种格式**: Python 函数（灵活）或 Markdown（简单）
- **描述自动提取**: 从 docstring 或首行提取
- **访问上下文**: 可访问 agent 工具和 LLM

### 5.2 目录结构

```
~/.kodaxpp/
├── config.toml           # 全局配置
├── skills/
│   ├── commit.py         # /commit skill (Python)
│   ├── commit.md         # /commit skill (Markdown) - 二选一
│   ├── review.py         # /review skill
│   └── custom/           # 用户自定义
└── sessions/             # 会话存储
    └── *.jsonl
```

### 5.3 Skill 定义格式

**方式一：Python 函数**（灵活，可执行工具）

```python
# ~/.kodaxpp/skills/commit.py

def skill_commit(agent, args: str) -> str:
    """根据 git diff 生成 commit 消息

    描述从 docstring 第一行自动提取。
    """
    diff = agent.execute_tool("bash", {"command": "git diff --staged"})
    if not diff.strip():
        return "No staged changes."

    return agent.call_llm([{
        "role": "user",
        "content": f"Generate commit message:\n\n{diff}"
    }])
```

**方式二：Markdown 文件**（简单，纯提示词）

```markdown
# ~/.kodaxpp/skills/commit.md

# Generate commit message

Generate a concise git commit message following conventional commits format.
Use git diff --staged to see the changes.

Format: <type>: <description>
Types: feat, fix, refactor, docs, test, chore
```

- 文件内容作为用户提示词发送给 LLM
- 描述从第一个 `#` 标题行提取
- 如需参数，会追加到提示词末尾

### 5.4 Skill API

Python skill 可通过 `agent` 参数访问：

```python
def skill_xxx(agent, args: str) -> str:
    # 执行工具
    result = agent.execute_tool("bash", {"command": "ls"})

    # 调用 LLM
    response = agent.call_llm([{"role": "user", "content": "..."}])

    # 访问消息历史
    history = agent.messages

    return "result"
```

### 5.5 使用示例

```bash
# 查看可用 skills
uv run kodaxp.py

# 执行 skill
uv run kodaxp.py /commit
uv run kodaxp.py /explain kodaxp.py
```

---

## 6. 上下文压缩 (P1)

### 6.1 设计要点

- **自动触发**: 每次 LLM 调用前检查 token 数
- **阈值**: 100K tokens（可配置）
- **策略**: 保留最近 10 条消息 + 旧消息摘要

### 6.2 Token 估算

```python
def estimate_tokens(messages: list) -> int:
    """估算消息的 token 数量（启发式：chars/4）"""
    total = 0

    for msg in messages:
        content = msg.get("content", "")

        if isinstance(content, str):
            total += len(content) // 4

        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        total += len(block.get("text", "")) // 4
                    elif block.get("type") == "tool_result":
                        total += len(block.get("content", "")) // 4
                    elif block.get("type") == "tool_use":
                        total += len(str(block.get("input", ""))) // 4

    return total
```

### 6.3 压缩策略

```python
def compact_messages(messages: list, max_tokens: int = 100000) -> list:
    """压缩消息历史"""
    if estimate_tokens(messages) <= max_tokens:
        return messages

    # 保留最近 10 条消息
    recent = messages[-10:]
    older = messages[:-10]

    # 生成摘要（简单方案）
    summary_lines = []
    for msg in older:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if isinstance(content, str):
            preview = content[:100] if len(content) > 100 else content
            summary_lines.append(f"- {role}: {preview}")
        elif isinstance(content, list):
            # 提取工具调用信息
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    summary_lines.append(
                        f"- Tool: {block.get('name', 'unknown')}"
                    )

    summary = "\n".join(summary_lines[-30:])  # 最多 30 条
    summary_block = {
        "role": "user",
        "content": f"[之前的对话摘要]\n{summary}"
    }

    return [summary_block] + recent
```

### 6.4 集成到 Agent 循环

```python
def stream_llm(messages: list) -> tuple[list, list]:
    # 调用前压缩
    messages = compact_messages(messages, max_tokens=100000)

    # 正常调用 LLM
    ...
```

---

## 7. 会话持久化 (P1)

### 7.1 设计要点

- **存储格式**: JSONL（第一行为元数据，后续为消息）
- **存储位置**: `~/.kodaxpp/sessions/{session_id}.jsonl`
- **自动保存**: 每次消息后覆盖保存
- **自动标题**: 从第一条用户消息提取前 50 字符作为标题

### 7.2 存储格式

```jsonl
{"_type": "meta", "title": "读取项目目录下的所有md文件", "id": "20260213_141051"}
{"role": "user", "content": "读取项目目录下的所有md文件"}
{"role": "assistant", "content": [{"type": "text", "text": "好的，我来读取..."}, {"type": "tool_use", "id": "...", "name": "glob", "input": {...}}]}
{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]}
```

### 7.3 Session 类实现

```python
from dataclasses import dataclass
from pathlib import Path
import json
import time

SESSIONS_DIR = Path.home() / ".kodaxp" / "sessions"

@dataclass
class Session:
    """会话管理类"""
    id: str
    messages: list
    title: str = ""

    def _extract_title(self, content) -> str:
        """从消息内容提取标题（前 50 字符）"""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
            text = " ".join(texts)
        else:
            text = str(content)
        title = text.strip()[:50]
        return title + ("..." if len(text) > 50 else "")

    @classmethod
    def load(cls, session_id: str) -> "Session":
        """加载会话"""
        path = SESSIONS_DIR / f"{session_id}.jsonl"
        messages = []
        title = ""
        if path.exists():
            for i, line in enumerate(path.read_text(encoding="utf-8").strip().split("\n")):
                if line:
                    data = json.loads(line)
                    if i == 0 and isinstance(data, dict) and data.get("_type") == "meta":
                        title = data.get("title", "")
                    else:
                        messages.append(data)
        return cls(id=session_id, messages=messages, title=title)

    def save(self):
        """保存会话"""
        # 自动生成标题
        if not self.title and self.messages:
            for msg in self.messages:
                if msg.get("role") == "user":
                    self.title = self._extract_title(msg.get("content", ""))
                    break

        path = SESSIONS_DIR / f"{self.id}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            # 第一行：元数据
            meta = {"_type": "meta", "title": self.title, "id": self.id}
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            # 后续：消息
            for msg in self.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    @staticmethod
    def list_all() -> list[dict]:
        """返回会话列表 [{id, title, msg_count}, ...]"""
        if not SESSIONS_DIR.exists():
            return []
        sessions = []
        for f in sorted(SESSIONS_DIR.glob("*.jsonl"), reverse=True):
            try:
                lines = f.read_text(encoding="utf-8").strip().split("\n")
                if not lines:
                    continue
                first = json.loads(lines[0])
                if first.get("_type") == "meta":
                    sessions.append({
                        "id": f.stem,
                        "title": first.get("title", ""),
                        "msg_count": len(lines) - 1
                    })
                else:
                    # 旧格式兼容
                    sessions.append({
                        "id": f.stem,
                        "title": "",
                        "msg_count": len(lines)
                    })
            except:
                continue
        return sessions[:10]
```

### 7.4 CLI 命令

```bash
# 新会话（默认）
uv run kodaxp.py "你的任务"

# 恢复最近会话
uv run kodaxp.py --session resume "继续任务"

# 恢复指定会话
uv run kodaxp.py --session 20260213_141051 "继续任务"

# 列出所有会话（显示标题和消息数）
uv run kodaxp.py --session list

# 输出示例：
# Sessions:
#   20260213_141051  [19 msgs]  读取项目目录下的所有md文件
#   20260213_140910  [6 msgs]   分析代码结构并添加注释
```

---

## 8. 上下文增强 (P1) ✅ 已完成

### 8.1 Git Context 自动注入

自动检测当前 Git 仓库状态并注入到系统提示词中，帮助 Agent 了解当前工作上下文。

**实现**:
```python
def get_git_context() -> str:
    """获取 Git 上下文信息（分支、状态）"""
    try:
        # 检查是否在 Git 仓库中
        r = subprocess.run("git rev-parse --is-inside-work-tree", shell=True, ...)
        if r.returncode != 0:
            return ""

        lines = []

        # 获取分支名
        r = subprocess.run("git branch --show-current", shell=True, ...)
        if r.returncode == 0 and r.stdout.strip():
            lines.append(f"Git Branch: {r.stdout.strip()}")

        # 获取状态摘要（最多 10 条）
        r = subprocess.run("git status --short", shell=True, ...)
        if r.returncode == 0 and r.stdout.strip():
            status_lines = r.stdout.strip().split("\n")[:10]
            lines.append(f"Git Status:\n" + "\n".join(f"  {s}" for s in status_lines))

        return "\n".join(lines) if lines else ""
    except Exception:
        return ""
```

**使用效果**:
```
System Prompt:
...
Git Branch: main
Git Status:
   M kodaxp.py
  ?? test_new_feature.py
```

**特性**:
- 仅在新会话时获取（避免重复注入）
- 非 Git 仓库不报错，静默跳过
- 最多显示 10 条状态，避免上下文过长

### 8.2 项目快照

在会话开始时自动获取项目目录结构，帮助 Agent 快速了解项目布局。

**实现**:
```python
def get_project_snapshot(max_depth: int = 2, max_files: int = 50) -> str:
    """获取项目结构快照"""
    try:
        cwd = Path.cwd()
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
        ignore_exts = {".pyc", ".pyo", ".so", ".dll", ".exe"}

        lines = [f"Project: {cwd.name}"]
        file_count = 0

        for root, dirs, files in os.walk(cwd):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            depth = len(Path(root).relative_to(cwd).parts)
            if depth > max_depth:
                continue

            # 显示目录和文件...
            if file_count >= max_files:
                lines.append("  ... (more files)")
                break

        return "\n".join(lines)
    except Exception:
        return ""
```

**使用效果**:
```
Project: KodaXP
  README.md
  pyproject.toml
  kodaxp.py
  docs/
    DESIGN.md
    TESTING.md
```

**特性**:
- 限制深度（默认 2 层）和文件数（默认 50）
- 自动忽略常见目录和二进制文件
- 仅在新会话时获取

### 8.3 Todo 自追踪

通过系统提示词引导 Agent 自动追踪多步骤任务进度。

**系统提示词增强**:
```
For multi-step tasks:
- Track your progress by listing what you've done and what's next
- Break complex tasks into smaller steps
- Summarize progress periodically
```

**示例输出**:
```
[Assistant] I'll help you implement this feature. Let me break it down:

1. ✅ Read the existing code structure
2. ✅ Add the new function
3. 🔄 Write tests
4. ⏳ Update documentation

Now working on step 3: Writing tests...
```

### 8.4 简单 Undo

在修改文件前自动备份，支持撤销最近的文件修改。

**实现**:
```python
# 全局备份存储
FILE_BACKUPS: dict[str, str] = {}

# 在 write/edit 前备份
case "write":
    path = Path(input_data["path"])
    if path.exists():
        FILE_BACKUPS[str(path)] = path.read_text(encoding="utf-8")
    # ... 执行写入

case "edit":
    # ... 验证后
    FILE_BACKUPS[str(path)] = content  # 备份原内容
    # ... 执行编辑

# undo 工具
def undo_last_edit() -> str:
    """撤销最近一次文件修改"""
    if not FILE_BACKUPS:
        return "No backups available."

    path, content = list(FILE_BACKUPS.items())[-1]
    Path(path).write_text(content, encoding="utf-8")
    del FILE_BACKUPS[path]
    return f"Restored: {path}"
```

**工具定义**:
```python
{"name": "undo", "description": "Undo the last file modification.", "input_schema": {"type": "object", "properties": {}, "required": []}}
```

**使用示例**:
```bash
# Agent 执行 write/edit 后可以撤销
uv run kodaxp.py "修改 kodaxp.py 添加新功能，然后撤销"
```

**限制**:
- 仅在当前会话有效（重启后清空）
- 只保留最新一次修改的备份
- 不适用于批量操作

---

## 9. 长时间运行模式 (P1) ✅ 已完成

基于 Anthropic 文章：[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

### 9.1 背景

长时间运行代理面临两个核心问题：
1. **Agent 一次做太多** - 尝试一次性完成所有功能，导致上下文溢出
2. **过早宣布完成** - 看到部分进度就认为项目已完成

### 9.2 解决方案

采用 **Initializer Agent + Coding Agent** 两阶段模式：

**Initializer Agent** (`--init`):
- 创建 `feature_list.json` - 所有功能的详细列表，初始 `passes: false`
- 创建 `PROGRESS.md` - 进度日志
- 初始 git commit

**Coding Agent** (后续运行):
- 自动检测 `feature_list.json` 存在，进入长运行模式
- 每个 session 只处理一个 feature
- 结束前 git commit + 更新 PROGRESS.md

### 9.3 状态文件

**feature_list.json**:
```json
{
  "features": [
    {
      "description": "User can create new chat",
      "steps": ["Navigate to interface", "Click New Chat", "Verify conversation created"],
      "passes": false
    },
    {
      "description": "User can send message",
      "steps": ["Type message", "Press enter", "See AI response"],
      "passes": false
    }
  ]
}
```

**PROGRESS.md**:
```markdown
# Progress Log

## 2026-02-12 15:30

### Completed
- Basic chat interface setup
- Message sending functionality

### Next
- Add conversation history
- Implement theme switching
```

### 9.4 实现

**状态检测函数**:
```python
def get_long_running_context() -> str:
    """检测并加载长运行任务上下文"""
    parts = []

    # Feature List
    if Path(FEATURES_FILE).exists():
        features = json.loads(Path(FEATURES_FILE).read_text(encoding="utf-8"))
        parts.append("## Feature List (from feature_list.json)\n")
        for f in features.get("features", []):
            status = "[x]" if f.get("passes") else "[ ]"
            parts.append(f"- {status} {f.get('description')}")

    # Progress
    if Path(PROGRESS_FILE).exists():
        progress = Path(PROGRESS_FILE).read_text(encoding="utf-8")
        parts.append(f"\n## Last Session Progress\n\n{progress[:1500]}")

    return "\n".join(parts) if parts else ""
```

**长运行模式提示词**:
```python
LONG_RUNNING_PROMPT = """
## Long-Running Task Mode

At the start of EACH session:
1. Run `pwd` to confirm working directory
2. Read git logs and PROGRESS.md
3. Read feature_list.json, pick ONE incomplete feature
4. Test basic functionality before implementing
5. Implement feature incrementally
6. End with: git commit + update PROGRESS.md

IMPORTANT:
- Only change `passes` field in feature_list.json
- Leave codebase in clean state
- Work on ONE feature at a time
"""
```

### 9.5 使用方式

```bash
# 1. 初始化长运行项目
uv run kodaxp.py --init "构建 claude.ai 克隆"

# 2. 后续运行（自动检测长运行模式）
uv run kodaxp.py "继续开发"

# 3. 第二天继续
uv run kodaxp.py --session resume "继续昨天的工作"
```

### 9.6 自动继续模式 (Auto-Continue)

完全自主运行，直到所有功能完成。

**使用方式**:
```bash
# 1. 初始化（必须先执行 --init）
uv run kodaxp.py --init "构建带认证的 REST API"

# 2. 自动继续直到完成
uv run kodaxp.py --auto-continue

# 3. 自定义安全限制
uv run kodaxp.py --auto-continue --max-sessions 20 --max-hours 4.0
```

**安全阀设计**（自动停止，无需人工介入）:

| 条件 | 默认值 | 说明 |
|------|--------|------|
| 所有功能完成 | - | `feature_list.json` 中所有 `passes: true` |
| 最大会话数 | 50 | `--max-sessions` 参数控制 |
| 最大小时数 | 2.0 | `--max-hours` 参数控制 |
| 连续错误 | 3次 | 连续 3 次会话失败 |

**实现**:
```python
def check_all_features_complete() -> bool:
    """检查所有 feature 是否已完成"""
    features_path = Path(FEATURES_FILE)
    if not features_path.exists():
        return False
    try:
        features = json.loads(features_path.read_text(encoding="utf-8"))
        for f in features.get("features", []):
            if not f.get("passes", False):
                return False
        return True
    except Exception:
        return False

def get_feature_progress() -> tuple[int, int]:
    """获取 feature 完成进度 (completed, total)"""
    # ...
```

**主循环**:
```python
# auto-continue 模式
if args.auto_continue:
    start_time = time.time()
    session_count = 0
    consecutive_errors = 0

    while True:
        # 检查安全阀
        completed, total = get_feature_progress()
        if check_all_features_complete():
            print(f"\n[KodaXP] All features completed! ({completed}/{total})")
            break

        if session_count >= args.max_sessions:
            print(f"\n[KodaXP] Max sessions reached ({args.max_sessions})")
            break

        elapsed_hours = (time.time() - start_time) / 3600
        if elapsed_hours >= args.max_hours:
            print(f"\n[KodaXP] Max hours reached ({args.max_hours}h)")
            break

        # 运行一个 session
        success = run_single_session(args, prompt)

        if success:
            consecutive_errors = 0
        else:
            consecutive_errors += 1
            if consecutive_errors >= 3:
                print(f"\n[KodaXP] Too many consecutive errors, stopping")
                break

        session_count += 1
```

**与 `--init` 的语义配对**:

| 命令 | 作用 | 依赖 |
|------|------|------|
| `--init TASK` | 初始化长运行项目 | 无 |
| `--auto-continue` | 自动继续直到完成 | 需要 `feature_list.json` |

`--auto-continue` 必须在 `--init` 之后使用，否则会报错：
```
[Error] --auto-continue requires a long-running project.
       Run 'kodaxp.py --init "your task"' first.
```

### 9.7 单次会话迭代限制 (--max-iter)

控制单个 session 内的 Agent 迭代次数。

**默认值**: 50

**使用场景**:
- 防止单个 session 无限循环
- 控制单次运行的成本
- 调试时限制迭代次数

```bash
# 默认 50 次迭代
uv run kodaxp.py "你的任务"

# 限制为 20 次迭代
uv run kodaxp.py --max-iter 20 "你的任务"

# 配合 auto-continue 使用
uv run kodaxp.py --auto-continue --max-iter 30
```

**三个正交维度**:

| 维度 | 参数 | 层级 | 说明 |
|------|------|------|------|
| 项目级别 | `--init` / `--auto-continue` | 跨 session | 控制长运行任务生命周期 |
| 会话级别 | `--max-iter` | 单 session | 控制单次运行的迭代次数 |
| 安全级别 | `--max-sessions` / `--max-hours` | auto-continue | 控制 auto-continue 的边界 |

### 9.8 设计原则

| 原则 | 实现 |
|------|------|
| **提示词驱动** | 通过 LONG_RUNNING_PROMPT 引导行为，不增加复杂代码逻辑 |
| **状态文件** | JSON + Markdown 格式，人类可读可编辑 |
| **自动检测** | 检测 `feature_list.json` 存在自动启用长运行模式 |
| **极简代码** | 仅增加 ~45 行代码 |
| **语义配对** | `--init` 初始化，`--auto-continue` 持续运行 |
| **安全阀** | 自动停止条件，无需人工干预 |

### 9.9 Promise 信号系统 (Ralph-Loop 风格)

借鉴 Anthropic 官方插件 **Ralph Loop (Ralph Wiggum)** 的设计，KodaXP 实现了 Promise 信号系统，让 Agent 能够主动与 auto-continue 循环通信。

#### 背景

**Ralph Loop** 是 Anthropic 官方维护的插件，核心创新是用特殊标记让 Agent 主动通信状态：
- `<promise>COMPLETE</promise>` - 任务完成
- `<promise>BLOCKED:reason</promise>` - 需要人类帮助
- `<promise>DECIDE:question</promise>` - 需要用户决策

#### 实现

**检测函数**:
```python
PROMISE_PATTERN = re.compile(r'<promise>(COMPLETE|BLOCKED|DECIDE)(?::(.*?))?</promise>', re.IGNORECASE)

def check_promise_signal(text: str) -> tuple[str, str]:
    """检查 Agent 输出中的 promise 信号"""
    match = PROMISE_PATTERN.search(text)
    if match:
        return match.group(1).upper(), match.group(2) or ""
    return "", ""
```

**auto-continue 循环集成**:
```python
# 运行 session 后检查信号
success, last_text = run_single_session(args, prompt)

signal, reason = check_promise_signal(last_text)
if signal == "COMPLETE":
    print("[KodaXP Auto-Continue] Agent signaled COMPLETE")
    break
elif signal == "BLOCKED":
    print(f"[KodaXP Auto-Continue] Agent BLOCKED: {reason}")
    break
elif signal == "DECIDE":
    print(f"[KodaXP Auto-Continue] Agent needs decision: {reason}")
    break
```

**提示词引导**:
```
## Promise Signals (Ralph-Loop Style)

When you need to communicate status to the orchestrator, use these special signals:

<promise>COMPLETE</promise>       - All features are done
<promise>BLOCKED:reason</promise>  - Need human intervention
<promise>DECIDE:question</promise> - Need a decision from user
```

#### 与 Ralph Loop 对比

| 特性 | Ralph Loop | KodaXP |
|------|------------|-------|
| **信号系统** | ✅ Promise tags | ✅ Promise tags |
| **Stop Hook** | ✅ 拦截退出 | ❌ 使用 --auto-continue |
| **Initializer Agent** | ❌ | ✅ `--init` |
| **Feature List** | ❌ | ✅ `feature_list.json` |
| **Progress File** | ✅ txt | ✅ Markdown |
| **时间限制** | ❌ | ✅ `--max-hours` |

KodaXP 结合了 Ralph Loop 的信号系统和 Anthropic Engineering Blog 推荐的状态管理，形成更完整的解决方案。

---

## 10. Agent Team (P2) ✅ 已完成

### 8.1 使用场景

1. **代码探索并行**: 多个 agent 同时搜索不同文件，汇总结果
2. **测试与编码并行**: 一个 agent 写代码，另一个同时运行测试

### 8.2 实现

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def execute_tools_async(tool_calls: list, confirm_tools: set) -> list:
    """并行执行多个独立的工具调用"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [
            loop.run_in_executor(executor, execute_tool, tc["name"], tc["input"], confirm_tools)
            for tc in tool_calls
        ]
        return await asyncio.gather(*tasks)


def run_subagent(task: str, provider_name: str, thinking: bool = False, max_rounds: int = 5) -> str:
    """运行子 Agent（简化版，用于并行任务）"""
    provider = PROVIDERS[provider_name]()
    messages = [{"role": "user", "content": task}]
    sub_system = SYSTEM_PROMPT + "\n\nYou are a sub-agent working on a specific task."

    for _ in range(max_rounds):
        text_blocks, tool_blocks = provider.stream(messages, TOOLS, sub_system, thinking)
        # ... agent loop logic
        if not tool_blocks:
            return text_blocks[-1]["text"] if text_blocks else "Task completed"

    return "[SubAgent] Max iterations reached"


async def run_parallel_agents_async(tasks: list, provider_name: str, thinking: bool = False) -> list:
    """并行运行多个子 Agent"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            loop.run_in_executor(executor, run_subagent, task, provider_name, thinking)
            for task in tasks
        ]
        return await asyncio.gather(*futures)
```

### 8.3 CLI 集成

```bash
# 并行工具执行模式
uv run kodaxp.py --parallel "读取 src/ 目录下的所有配置文件"

# Agent Team - 多个任务并行执行
uv run kodaxp.py --team "分析 src/ 目录结构,检查测试覆盖率,查找 TODO 注释"

# 使用 Thinking Mode
uv run kodaxp.py --provider kimi-code --thinking --team "代码审查,性能分析"
```

### 8.4 流式输出优化 ✅

**问题**：并行 Agent 同时执行时存在两个挑战：
1. **Rate Limit**：多个 Agent 同时请求 API 触发速率限制
2. **输出交错**：多个 Agent 同时打印导致输出混乱

**解决方案**：两层锁机制

```python
# 全局锁
api_lock = threading.Lock()       # Rate Limit 控制
stream_lock = threading.Lock()    # 流式输出锁
```

**执行流程**：
```
Agent 1: [工具执行] → 等待 stream_lock → [API + 流式输出] → 释放
Agent 2: [工具执行] → 等待 stream_lock → [API + 流式输出] → 释放
Agent 3: [工具执行] → 等待 stream_lock → [API + 流式输出] → 释放
         ↑ 并行      ↑ 串行化输出         ↑ 实时流式
```

**StreamingSubAgent 实现**：

```python
class StreamingSubAgent:
    """实时流式输出的子 Agent"""

    def _stream_with_lock(self, messages, tools, system):
        """带输出锁的流式 API 调用"""
        provider = self._init_provider()

        with stream_lock:
            # 打印 Agent 标识
            print(f"\n[Agent {self.agent_id}] {self.task_desc[:50]}...")
            # 直接流式输出（provider 会打印 [Assistant]）
            return provider.stream(messages, tools, system, self.thinking)

    def _call_api_with_rate_limit(self, messages, tools, system):
        """带 Rate Limit 控制的 API 调用"""
        def do_call():
            return self._stream_with_lock(messages, tools, system)
        return rate_limited_call(do_call)
```

**配置参数**：

```python
STAGGER_DELAY = 1.0      # Agent 启动间隔（秒）
MAX_RETRIES = 3          # Rate limit 最大重试次数
RETRY_BASE_DELAY = 2     # 重试基础延迟（秒）
API_MIN_INTERVAL = 0.5   # API 调用最小间隔（秒）
```

---

## 10.1 跨平台兼容性 (P0) ✅ 已完成

### Windows 环境修复

#### 编码修复

**问题**: Windows 中文环境下，`subprocess.run` 的输出编码问题。

- **v0.6.0 尝试**：强制 `encoding='utf-8'` - 但 cmd.exe 输出是 GBK 编码，导致中文乱码
- **v0.6.1 修复**：使用 `encoding='oem'` - 自动匹配 Windows 控制台编码（中文环境是 GBK）

**错误示例 (v0.6.0)**:
```
[Result] Exit: 1
'pwd' 不是内部或外部命令，也不是可运行的程序或批处理文件。
```

**解决方案 (v0.6.1)**:
```python
case "bash":
    timeout = input_data.get("timeout", 30)
    try:
        # Windows 使用 OEM 编码（GBK），其他系统使用 UTF-8
        encoding = 'oem' if sys.platform == 'win32' else 'utf-8'

        r = subprocess.run(
            input_data["command"],
            shell=True,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors='replace',
            timeout=timeout
        )
        return f"Exit: {r.returncode}\n{r.stdout}{r.stderr}"
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
```

**关键点**:
- `'oem'` 是 Python 特殊编码名称，自动使用当前控制台的代码页
- 中文 Windows 默认是 GBK (cp936)
- 这样能正确显示 cmd.exe 的中文错误消息

#### 智能并行执行

**问题**: `git add .` 和 `git commit` 并行执行会导致 `.git/index.lock` 竞争条件。

**错误示例**:
```
fatal: Unable to create '.git/index.lock': File exists.
```

**解决方案**: Bash 命令顺序执行，其他命令（read, glob, grep）并行执行。

```python
def execute_tools_parallel(tool_calls: list, confirm_tools: set) -> list:
    """智能并行执行：bash 命令顺序执行，其他命令并行执行"""
    bash_indices, bash_calls = [], []
    other_indices, other_calls = [], []

    for i, tc in enumerate(tool_calls):
        if tc["name"] == "bash":
            bash_indices.append(i)
            bash_calls.append(tc)
        else:
            other_indices.append(i)
            other_calls.append(tc)

    results = [None] * len(tool_calls)

    # 1. 非 bash 命令并行执行
    if other_calls:
        other_results = asyncio.run(execute_tools_async(other_calls, confirm_tools))
        for idx, result in zip(other_indices, other_results):
            results[idx] = result

    # 2. bash 命令顺序执行（避免 race condition）
    for idx, tc in zip(bash_indices, bash_calls):
        results[idx] = execute_tool(tc["name"], tc["input"], confirm_tools)

    return results
```

### Thinking Blocks 保留 (P0) ✅ 已完成

**问题**: Kimi Code Thinking Mode 多轮工具调用时报错：
```
thinking is enabled but reasoning_content is missing in assistant tool call message at index 2
```

**根因**: 当 `thinking` 启用时，每个 assistant 消息必须以 thinking block 开始，且包含 `signature` 字段。

**解决方案**:

1. 在 `AnthropicBaseProvider.stream()` 中提取完整的 thinking blocks：

```python
def stream(self, messages, tools, system, thinking=False):
    text_blocks, tool_blocks, thinking_blocks = [], [], []
    # ... streaming code ...

    final = stream.get_final_message()
    for block in final.content:
        if block.type == "thinking":
            thinking_blocks.append({
                "type": "thinking",
                "thinking": block.thinking,
                "signature": getattr(block, "signature", "")  # 关键！
            })
        elif block.type == "redacted_thinking":
            thinking_blocks.append({
                "type": "redacted_thinking",
                "data": getattr(block, "data", "")
            })
        # ... other blocks ...

    return text_blocks, tool_blocks, thinking_blocks
```

2. 构建消息时 thinking blocks 放在最前面：

```python
assistant_content = []

# 1. Thinking blocks 必须在最前面
for tb in thinking_blocks:
    assistant_content.append(tb)

# 2. 然后是 text blocks
for b in text_blocks:
    assistant_content.append({"type": "text", "text": b["text"]})

# 3. 最后是 tool_use blocks
for b in tool_blocks:
    assistant_content.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]})

session.messages.append({"role": "assistant", "content": assistant_content})
```

**关键点**:
- Thinking blocks 必须在 content 数组的最前面
- Signature 不可省略，即使为空也必须传递
- 适用于所有使用 Anthropic API 的 Provider (anthropic, kimi-code, zhipu-coding)

---

## 11. 不实现的功能

以下功能暂不考虑，原因如下：

| 功能 | 不实现原因 |
|------|-----------|
| **MCP 集成** | 复杂度高，内置工具已覆盖核心功能 |
| **Notebook 支持** | 特定场景，可通过 bash 工具操作 |
| **TUI 界面** | 保持简单终端输出 |
| **Web UI** | 与 CLI 定位不符 |
| **分布式执行** | 过于复杂，单机足够 |

---

## 11. 快速开始

### 10.1 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/koda-agent.git
cd koda-agent

# 安装依赖
uv sync
```

### 10.2 配置

```bash
# 设置 API Key
export ANTHROPIC_API_KEY=your-key

# 或使用其他 Provider
export KODA_PROVIDER=kimi
export KIMI_API_KEY=your-key
```

### 10.3 使用

```bash
# 基本使用
uv run kodaxp.py "创建一个简单的 HTTP 服务器"

# 禁用确认
uv run kodaxp.py --no-confirm "删除临时文件"

# 使用 Skill
uv run kodaxp.py /commit
uv run kodaxp.py /explain kodaxp.py

# 恢复会话
uv run kodaxp.py --session resume "继续修改"
```

---

## 12. 文件结构

```
KodaXP/
├── pyproject.toml          # 项目配置
├── README.md               # 使用说明（英文）
├── kodaxp.py          # 核心实现 (~2000 LOC)
├── docs/
│   ├── README_CN.md        # 使用说明（中文）
│   ├── DESIGN.md           # 设计文档（本文件）
│   ├── LONG_RUNNING_GUIDE.md  # 长运行模式指南
│   └── TESTING.md          # 测试指南
└── ~/.kodaxpp/               # 用户配置目录
    ├── skills/             # Skill 目录
    └── sessions/           # 会话存储
```
