# Kodax Agent 设计文档

> 极致轻量化 Coding Agent - 基于 pi-mono 项目研究设计

---

## 1. 设计理念

### 1.1 核心原则

| 原则 | 说明 |
|------|------|
| **系统极简** | 代码保持精简，单文件核心 ~400 LOC |
| **依赖最小** | 仅必要的 SDK |
| **标准库优先** | 文件操作、进程管理使用 Python 标准库 |
| **无框架** | 不引入 Agent 框架，保持代码直白 |

### 1.2 目标指标

```
核心代码:      ~400 LOC
启动时间:      < 50ms
内存占用:      < 50MB
```

### 1.3 与 pi-mono 的对比

| 特性 | pi-mono | Kodax Agent |
|------|---------|------------|
| **语言** | TypeScript | Python |
| **代码量** | ~10,000 LOC | ~400 LOC |
| **依赖** | 多个 | 精简 |
| **状态管理** | 复杂订阅系统 | 简单消息列表 |
| **UI** | TUI 框架 | 终端输出 |
| **扩展** | 插件系统 | Skill 动态加载 |

---

## 2. 架构概览

```
┌─────────────────────────────────────────┐
│           kodax_agent.py (~500 LOC)       │
│                                          │
│  ┌─────────┐ ┌─────────┐ ┌────────────┐ │
│  │ Config  │ │  Tools  │ │ Agent Loop │ │
│  │ (~20行) │ │ (~100行)│ │  (~80行)   │ │
│  └─────────┘ └─────────┘ └────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐│
│  │        Tool Execution (~80行)        ││
│  │  read | write | edit | bash | glob  ││
│  │                grep                  ││
│  └─────────────────────────────────────┘│
│                                          │
│  ┌─────────────────────────────────────┐│
│  │        Provider Layer (~200行)       ││
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
uv run kodax_agent.py "你的任务"

# 自定义确认列表
uv run kodax_agent.py --confirm bash,write "你的任务"

# 禁用所有确认
uv run kodax_agent.py --no-confirm "你的任务"
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
| **Anthropic** | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 | 原生 | ✅ |
| **Kimi (Moonshot)** | `KIMI_API_KEY` | moonshot-v1-128k | OpenAI | ❌ |
| **Kimi Code** | `KIMI_API_KEY` | k2p5 | Anthropic | ✅ |
| **智谱AI** | `ZHIPU_API_KEY` | glm-4-plus | zhipuai SDK | ❌ |
| **智谱 Coding** | `ZHIPU_API_KEY` | glm-5 | Anthropic | ✅ |
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

```bash
# 方式 1: 环境变量
export KODA_PROVIDER=kimi
export KIMI_API_KEY=your-key
uv run kodax_agent.py "你的任务"

# 方式 2: 命令行参数
uv run kodax_agent.py --provider zhipu "你的任务"

# 启用 Thinking Mode (仅 Anthropic, Kimi Code, 智谱 Coding 支持)
uv run kodax_agent.py --provider kimi-code --thinking "复杂任务"
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
~/.kodax/
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
# ~/.kodax/skills/commit.py

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
# ~/.kodax/skills/commit.md

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
uv run kodax_agent.py

# 执行 skill
uv run kodax_agent.py /commit
uv run kodax_agent.py /explain kodax_agent.py
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
- **存储位置**: `~/.kodax/sessions/{session_id}.jsonl`
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

SESSIONS_DIR = Path.home() / ".kodax" / "sessions"

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
uv run kodax_agent.py "你的任务"

# 恢复最近会话
uv run kodax_agent.py --session resume "继续任务"

# 恢复指定会话
uv run kodax_agent.py --session 20260213_141051 "继续任务"

# 列出所有会话（显示标题和消息数）
uv run kodax_agent.py --session list

# 输出示例：
# Sessions:
#   20260213_141051  [19 msgs]  读取项目目录下的所有md文件
#   20260213_140910  [6 msgs]   分析代码结构并添加注释
```

---

## 8. Agent Team (P2) ✅ 已完成

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
uv run kodax_agent.py --parallel "读取 src/ 目录下的所有配置文件"

# Agent Team - 多个任务并行执行
uv run kodax_agent.py --team "分析 src/ 目录结构,检查测试覆盖率,查找 TODO 注释"

# 使用 Thinking Mode
uv run kodax_agent.py --provider kimi-code --thinking --team "代码审查,性能分析"
```

---

## 9. 不实现的功能

以下功能暂不考虑，原因如下：

| 功能 | 不实现原因 |
|------|-----------|
| **MCP 集成** | 复杂度高，内置工具已覆盖核心功能 |
| **Notebook 支持** | 特定场景，可通过 bash 工具操作 |
| **TUI 界面** | 保持简单终端输出 |
| **Web UI** | 与 CLI 定位不符 |
| **分布式执行** | 过于复杂，单机足够 |

---

## 10. 快速开始

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
uv run kodax_agent.py "创建一个简单的 HTTP 服务器"

# 禁用确认
uv run kodax_agent.py --no-confirm "删除临时文件"

# 使用 Skill
uv run kodax_agent.py /commit
uv run kodax_agent.py /explain kodax_agent.py

# 恢复会话
uv run kodax_agent.py --session resume "继续修改"
```

---

## 11. 文件结构

```
koda-agent/
├── pyproject.toml          # 项目配置
├── README.md               # 使用说明
├── kodax_agent.py           # 核心实现 (~400 LOC)
├── test_tools.py           # 测试脚本
├── docs/
│   └── DESIGN.md           # 设计文档（本文件）
└── ~/.kodax/                # 用户配置目录
    ├── config.toml         # 全局配置
    ├── skills/             # Skill 目录
    └── sessions/           # 会话存储
```
