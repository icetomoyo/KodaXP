"""
Kodax Agent - 极致轻量化 Coding Agent

单文件实现，约 500 LOC
使用 uv 进行环境管理

使用方式:
    uv run kodax_agent.py "你的编程任务"
    uv run kodax_agent.py --provider kimi "你的任务"
    uv run kodax_agent.py --thinking "复杂任务"
    uv run kodax_agent.py /commit

环境变量:
    ANTHROPIC_API_KEY - Anthropic API 密钥
    KIMI_API_KEY - Kimi API 密钥
    ZHIPU_API_KEY - 智谱 AI API 密钥
    MINIMAX_API_KEY - MiniMax API 密钥
    QWEN_API_KEY - 通义千问 API 密钥
    OPENAI_API_KEY - OpenAI API 密钥
"""

import os
import sys
import subprocess
import argparse
import json
import time
import importlib.util
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# ============ 配置 ============
MAX_TOKENS = 4096
DEFAULT_CONFIRM_TOOLS = {"bash", "write", "edit"}
KODAX_DIR = Path.home() / ".kodax"
SKILLS_DIR = KODAX_DIR / "skills"
SESSIONS_DIR = KODAX_DIR / "sessions"

# ============ 工具定义 ============
TOOLS = [
    {"name": "read", "description": "Read the contents of a file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write", "description": "Write content to a file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit", "description": "Perform exact string replacement in a file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}},
    {"name": "bash", "description": "Execute a shell command.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "number"}}, "required": ["command"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "grep", "description": "Search for a pattern in files.", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}, "ignore_case": {"type": "boolean"}}, "required": ["pattern", "path"]}},
]

SYSTEM_PROMPT = """You are a helpful coding assistant. You can read, write, and edit files, and execute shell commands.

When making edits:
- Always read the file first to understand its current content
- Make precise, targeted edits rather than rewriting entire files
- Preserve the existing code style and formatting

When executing commands:
- Be careful with destructive operations
- Prefer read-only operations when possible

Always explain what you're doing before taking action."""


# ============ Provider 抽象 ============
class Provider(ABC):
    """LLM Provider 抽象基类

    所有 Provider 必须实现 stream 方法，支持流式输出和工具调用。
    """
    @abstractmethod
    def stream(self, messages: list, tools: list, system: str, thinking: bool = False) -> tuple[list, list]:
        """流式调用 LLM

        Args:
            messages: 对话消息列表
            tools: 可用工具定义
            system: 系统提示词
            thinking: 是否启用 thinking mode

        Returns:
            (text_blocks, tool_blocks): 文本块和工具调用块
        """
        pass


class AnthropicProvider(Provider):
    """Anthropic Claude 原生 Provider

    支持 Claude 模型的所有特性，包括 Thinking Mode。
    """
    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"

    def stream(self, messages, tools, system, thinking=False):
        text_blocks, tool_blocks = [], []
        current_text = ""
        thinking_text = ""
        in_thinking = False

        kwargs = {"model": self.model, "max_tokens": MAX_TOKENS, "system": system, "tools": tools, "messages": messages}
        if thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}

        print("\033[35m[Assistant]\033[0m ", end="", flush=True)

        with self.client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        if in_thinking and thinking_text:
                            # 结束 thinking 块，打印累积的内容
                            print(f"\n\033[90m[Thinking] {thinking_text[:500]}{'...' if len(thinking_text) > 500 else ''}\033[0m", flush=True)
                            thinking_text = ""
                            in_thinking = False
                        print(event.delta.text, end="", flush=True)
                        current_text += event.delta.text
                    elif event.delta.type == "thinking_delta" and thinking:
                        if not in_thinking:
                            in_thinking = True
                        thinking_text += event.delta.thinking
                elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                    if current_text:
                        text_blocks.append({"type": "text", "text": current_text})
                        current_text = ""
                    print()

            # 打印剩余的 thinking 内容
            if thinking_text:
                print(f"\n\033[90m[Thinking] {thinking_text[:500]}{'...' if len(thinking_text) > 500 else ''}\033[0m", flush=True)

            final = stream.get_final_message()
            for block in final.content:
                if block.type == "text" and block.text:
                    if not text_blocks or text_blocks[-1].get("text") != block.text:
                        text_blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    # 转换为 dict 以统一处理
                    tool_blocks.append({"id": block.id, "name": block.name, "input": block.input})

        if current_text and not text_blocks:
            text_blocks.append({"type": "text", "text": current_text})
        print()
        return text_blocks, tool_blocks


class OpenAICompatProvider(Provider):
    """OpenAI 兼容 API 基类

    适用于支持 OpenAI API 格式的服务 (Kimi Moonshot, Qwen, OpenAI)。
    不支持 Thinking Mode。
    """
    BASE_URL: str  # API 基础 URL
    API_KEY_ENV: str  # 环境变量名称
    MODEL: str  # 模型名称

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ.get(self.API_KEY_ENV), base_url=self.BASE_URL)

    def stream(self, messages, tools, system, thinking=False):
        full_messages = [{"role": "system", "content": system}] + messages
        text_content = ""
        tool_calls_map = {}

        print("\033[35m[Assistant]\033[0m ", end="", flush=True)

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

        print()

        text_blocks = [{"type": "text", "text": text_content}] if text_content else []
        tool_blocks = [{"id": v["id"], "name": v["name"], "input": json.loads(v["arguments"])} for v in tool_calls_map.values()]
        return text_blocks, tool_blocks


class KimiProvider(OpenAICompatProvider):
    BASE_URL = "https://api.moonshot.cn/v1"
    API_KEY_ENV = "KIMI_API_KEY"
    MODEL = "moonshot-v1-128k"


class QwenProvider(OpenAICompatProvider):
    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    API_KEY_ENV = "QWEN_API_KEY"
    MODEL = "qwen-max"


class OpenAIProvider(OpenAICompatProvider):
    BASE_URL = "https://api.openai.com/v1"
    API_KEY_ENV = "OPENAI_API_KEY"
    MODEL = "gpt-4o"


class ZhipuProvider(Provider):
    """智谱 AI GLM 模型 (使用 zhipuai SDK)

    通过官方 SDK 调用智谱 GLM 模型。
    不支持 Thinking Mode，使用 zhipu-coding 可启用 Thinking。
    """
    def __init__(self):
        from zhipuai import ZhipuAI
        self.client = ZhipuAI(api_key=os.environ.get("ZHIPU_API_KEY"))
        self.model = "glm-4-plus"

    def stream(self, messages, tools, system, thinking=False):
        full_messages = [{"role": "system", "content": system}] + messages
        text_content = ""
        tool_calls_map = {}

        print("\033[35m[Assistant]\033[0m ", end="", flush=True)

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

        print()

        text_blocks = [{"type": "text", "text": text_content}] if text_content else []
        tool_blocks = [{"id": v["id"], "name": v["name"], "input": json.loads(v["arguments"])} for v in tool_calls_map.values()]
        return text_blocks, tool_blocks


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
        text_blocks, tool_blocks = [], []
        current_text = ""
        thinking_text = ""
        in_thinking = False

        kwargs = {"model": self.MODEL, "max_tokens": MAX_TOKENS, "system": system, "tools": tools, "messages": messages}
        if thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}

        print("\033[35m[Assistant]\033[0m ", end="", flush=True)

        with self.client.messages.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        if in_thinking and thinking_text:
                            print(f"\n\033[90m[Thinking] {thinking_text[:500]}{'...' if len(thinking_text) > 500 else ''}\033[0m", flush=True)
                            thinking_text = ""
                            in_thinking = False
                        print(event.delta.text, end="", flush=True)
                        current_text += event.delta.text
                    elif event.delta.type == "thinking_delta" and thinking:
                        if not in_thinking:
                            in_thinking = True
                        thinking_text += event.delta.thinking
                elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                    if current_text:
                        text_blocks.append({"type": "text", "text": current_text})
                        current_text = ""
                    print()

            if thinking_text:
                print(f"\n\033[90m[Thinking] {thinking_text[:500]}{'...' if len(thinking_text) > 500 else ''}\033[0m", flush=True)

            final = stream.get_final_message()
            for block in final.content:
                if block.type == "text" and block.text:
                    if not text_blocks or text_blocks[-1].get("text") != block.text:
                        text_blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    # 转换为 dict 以统一处理
                    tool_blocks.append({"id": block.id, "name": block.name, "input": block.input})

        if current_text and not text_blocks:
            text_blocks.append({"type": "text", "text": current_text})
        print()
        return text_blocks, tool_blocks


class KimiCodeProvider(AnthropicCompatProvider):
    """Kimi Code Anthropic 兼容接口 - 支持工具调用和 Thinking

    文档: https://www.kimi.com/code/docs/more/third-party-agents.html
    Base URL: https://api.kimi.com/coding/
    Model: k2p5 (Kimi K2.5 Thinking)

    配置方式 (Claude Code 集成):
        export ANTHROPIC_BASE_URL=https://api.kimi.com/coding/
        export ANTHROPIC_API_KEY=sk-kimi-xxx
    """
    BASE_URL = "https://api.kimi.com/coding/"
    API_KEY_ENV = "KIMI_API_KEY"
    MODEL = "k2p5"


class ZhipuCodingProvider(AnthropicCompatProvider):
    """智谱 AI GLM Coding Plan - Anthropic 兼容接口"""
    BASE_URL = "https://open.bigmodel.cn/api/anthropic"
    API_KEY_ENV = "ZHIPU_API_KEY"
    MODEL = "glm-5"


PROVIDERS = {
    "anthropic": AnthropicProvider,
    "kimi": KimiProvider,
    "kimi-code": KimiCodeProvider,
    "qwen": QwenProvider,
    "openai": OpenAIProvider,
    "zhipu": ZhipuProvider,
    "zhipu-coding": ZhipuCodingProvider,
}


# ============ 工具执行 ============
def execute_tool(name: str, input_data: dict, confirm_tools: set) -> str:
    """执行单个工具调用

    Args:
        name: 工具名称 (read, write, edit, bash, glob, grep)
        input_data: 工具参数
        confirm_tools: 需要确认的工具集合

    Returns:
        工具执行结果字符串
    """
    if name in confirm_tools:
        print(f"\n\033[33m[Confirm]\033[0m Execute {name}?")
        print(f"  Input: {input_data}")
        try:
            if input("  [y/N]: ").strip().lower() != 'y':
                return "Operation cancelled by user"
        except (EOFError, KeyboardInterrupt):
            print()
            return "Operation cancelled by user"

    try:
        match name:
            case "read":
                path = Path(input_data["path"])
                return path.read_text(encoding="utf-8") if path.exists() else f"Error: File not found: {path}"
            case "write":
                path = Path(input_data["path"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(input_data["content"], encoding="utf-8")
                return f"File written: {path}"
            case "edit":
                path = Path(input_data["path"])
                if not path.exists(): return f"Error: File not found: {path}"
                content = path.read_text(encoding="utf-8")
                if input_data["old_string"] not in content: return f"Error: String not found"
                path.write_text(content.replace(input_data["old_string"], input_data["new_string"], 1), encoding="utf-8")
                return f"File edited: {path}"
            case "bash":
                timeout = input_data.get("timeout", 30)
                try:
                    r = subprocess.run(input_data["command"], shell=True, capture_output=True, text=True, timeout=timeout)
                    return f"Exit: {r.returncode}\n{r.stdout}{r.stderr}"
                except subprocess.TimeoutExpired:
                    return f"Timeout after {timeout}s"
            case "glob":
                base = Path(input_data.get("path", "."))
                matches = [m for m in base.glob(input_data["pattern"]) if not any(p.startswith(".") or p == "node_modules" for p in m.parts)]
                return "\n".join(str(m) for m in matches) or "No files found"
            case "grep":
                import re as rx
                regex = rx.compile(input_data["pattern"], rx.IGNORECASE if input_data.get("ignore_case") else 0)
                results = []
                spath = Path(input_data["path"])
                def search(f):
                    try:
                        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                            if regex.search(line): results.append(f"{f}:{i}: {line.strip()}")
                    except: pass
                if spath.is_file(): search(spath)
                else:
                    for f in spath.rglob("*"):
                        if f.is_file() and not any(p.startswith(".") for p in f.parts): search(f)
                return "\n".join(results[:50]) or "No matches"
            case _:
                return f"Unknown tool: {name}"
    except Exception as e:
        return f"Error: {e}"


# ============ P2: 并行执行 ============
async def execute_tools_async(tool_calls: list, confirm_tools: set) -> list:
    """并行执行多个独立的工具调用"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [
            loop.run_in_executor(executor, execute_tool, tc["name"], tc["input"], confirm_tools)
            for tc in tool_calls
        ]
        return await asyncio.gather(*tasks)


def execute_tools_parallel(tool_calls: list, confirm_tools: set) -> list:
    """同步包装: 并行执行多个工具"""
    return asyncio.run(execute_tools_async(tool_calls, confirm_tools))


def run_subagent(task: str, provider_name: str, thinking: bool = False, max_rounds: int = 5) -> str:
    """运行子 Agent（简化版，用于并行任务）

    Args:
        task: 子任务描述
        provider_name: Provider 名称
        thinking: 是否启用 thinking mode
        max_rounds: 最大轮数

    Returns:
        子 Agent 的最终文本结果
    """
    try:
        provider = PROVIDERS[provider_name]()
    except Exception as e:
        return f"[SubAgent Error] Failed to init provider: {e}"

    messages = [{"role": "user", "content": task}]
    sub_system = SYSTEM_PROMPT + "\n\nYou are a sub-agent working on a specific task. Focus only on your assigned task and provide a concise summary when done."

    for _ in range(max_rounds):
        try:
            text_blocks, tool_blocks = provider.stream(messages, TOOLS, sub_system, thinking)

            # 构建 assistant content
            assistant_content = []
            for b in text_blocks:
                assistant_content.append({"type": "text", "text": b["text"]})
            for b in tool_blocks:
                assistant_content.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]})
            messages.append({"role": "assistant", "content": assistant_content})

            if not tool_blocks:
                # 返回最终文本
                return text_blocks[-1]["text"] if text_blocks else "Task completed (no output)"

            # 执行工具（子 agent 不需要确认）
            tool_results = []
            for tc in tool_blocks:
                result = execute_tool(tc["name"], tc["input"], set())
                tool_results.append({"type": "tool_result", "tool_use_id": tc["id"], "content": result})

            messages.append({"role": "user", "content": tool_results})

        except Exception as e:
            return f"[SubAgent Error] {e}"

    return "[SubAgent] Max iterations reached"


async def run_parallel_agents_async(tasks: list, provider_name: str, thinking: bool = False) -> list:
    """并行运行多个子 Agent

    Args:
        tasks: 任务列表
        provider_name: Provider 名称
        thinking: 是否启用 thinking mode

    Returns:
        每个任务的结果列表
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            loop.run_in_executor(executor, run_subagent, task, provider_name, thinking)
            for task in tasks
        ]
        return await asyncio.gather(*futures)


def run_team(tasks: list, provider_name: str, thinking: bool = False) -> list:
    """运行 Agent Team（多个子 Agent 并行）

    Args:
        tasks: 任务列表，每个元素是一个任务描述字符串
        provider_name: Provider 名称
        thinking: 是否启用 thinking mode

    Returns:
        每个任务的结果列表
    """
    print(f"\n\033[36m[Kodax Team]\033[0m Starting {len(tasks)} parallel agents...")
    results = asyncio.run(run_parallel_agents_async(tasks, provider_name, thinking))
    return results


# ============ Token 估算 & 压缩 ============
def estimate_tokens(messages: list) -> int:
    """估算消息列表的 token 数量

    使用简单的字符数/4 作为估算。
    """
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
                    elif block.get("type") in ("tool_result", "tool_use"):
                        total += len(str(block.get("content", block.get("input", "")))) // 4
    return total


def compact_messages(messages: list, max_tokens: int = 100000) -> list:
    """压缩消息列表，保持上下文在 token 限制内

    当消息超过 max_tokens 时，保留最近 10 条消息，
    并将更早的消息压缩为摘要。
    """
    if estimate_tokens(messages) <= max_tokens:
        return messages
    recent = messages[-10:]
    older = messages[:-10]
    summary_lines = []
    for msg in older:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) < 200:
            summary_lines.append(f"- {role}: {content[:100]}")
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    summary_lines.append(f"- Tool: {block.get('name')}")
    summary = "\n".join(summary_lines[-30:])
    return [{"role": "user", "content": f"[对话历史摘要]\n{summary}"}] + recent


# ============ 会话管理 ============
@dataclass
class Session:
    """会话管理类

    支持会话持久化，以 JSONL 格式存储在 ~/.kodax/sessions/ 目录。
    格式：第一行为元数据，后续为消息列表。
    """
    id: str
    messages: list
    title: str = ""

    def _extract_title(self, content) -> str:
        """从消息内容提取标题"""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # 提取文本块
            texts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
            text = " ".join(texts)
        else:
            text = str(content)
        # 截取前 50 字符作为标题
        title = text.strip()[:50]
        return title + ("..." if len(text) > 50 else "")

    @classmethod
    def load(cls, session_id: str) -> "Session":
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
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
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSIONS_DIR / f"{self.id}.jsonl"

        # 自动生成标题
        if not self.title and self.messages:
            for msg in self.messages:
                if msg.get("role") == "user":
                    self.title = self._extract_title(msg.get("content", ""))
                    break

        with open(path, "w", encoding="utf-8") as f:
            # 第一行：元数据
            meta = {"_type": "meta", "title": self.title, "id": self.id}
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            # 后续：消息
            for msg in self.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    @staticmethod
    def list_all() -> list[dict]:
        """返回会话列表，包含 id, title, msg_count"""
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
                        "msg_count": len(lines) - 1  # 减去元数据行
                    })
                else:
                    # 旧格式，无元数据
                    sessions.append({
                        "id": f.stem,
                        "title": "",
                        "msg_count": len(lines)
                    })
            except:
                continue
        return sessions[:10]


# ============ Skill 系统 ============
def load_skills() -> dict:
    """动态加载 Skill

    支持:
    1. .py 文件: 查找 skill_ 前缀函数，提取 docstring 作为描述
    2. .md 文件: 纯提示词 skill，文件内容作为系统提示

    Returns:
        {skill_name: {"func": function, "desc": description}} 字典
    """
    skills = {}
    if not SKILLS_DIR.exists():
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        return skills

    # 加载 .py 文件
    for sf in SKILLS_DIR.rglob("*.py"):
        try:
            spec = importlib.util.spec_from_file_location(sf.stem, sf)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for name, func in vars(module).items():
                if name.startswith("skill_") and callable(func):
                    skill_name = name[6:]
                    # 提取 docstring 第一行作为描述
                    desc = ""
                    if func.__doc__:
                        desc = func.__doc__.strip().split("\n")[0][:60]
                    skills[skill_name] = {"func": func, "desc": desc}
        except Exception as e:
            print(f"Warning: Failed to load skill {sf}: {e}")

    # 加载 .md 文件 (纯提示词 skill)
    for mf in SKILLS_DIR.rglob("*.md"):
        skill_name = mf.stem
        if skill_name in skills:
            continue  # .py 优先
        try:
            content = mf.read_text(encoding="utf-8").strip()
            # 提取第一行作为描述
            first_line = content.split("\n")[0].lstrip("# ").strip()
            desc = first_line[:60] or "(prompt skill)"
            # 创建提示词 skill
            def make_md_skill(prompt):
                def skill(agent, args: str) -> str:
                    full_prompt = prompt
                    if args:
                        full_prompt += f"\n\nContext: {args}"
                    return agent.call_llm([{"role": "user", "content": full_prompt}])
                return skill
            skills[skill_name] = {"func": make_md_skill(content), "desc": desc}
        except Exception as e:
            print(f"Warning: Failed to load skill {mf}: {e}")

    return skills


# ============ 参数解析 ============
def parse_args():
    parser = argparse.ArgumentParser(description="Kodax Agent - 极致轻量化 Coding Agent")
    parser.add_argument("prompt", nargs="*", help="Your coding task")
    parser.add_argument("--provider", choices=list(PROVIDERS.keys()), default="anthropic", help="LLM provider")
    parser.add_argument("--thinking", action="store_true", help="Enable thinking mode (Anthropic only)")
    parser.add_argument("--confirm", metavar="TOOLS", help="Tools requiring confirmation")
    parser.add_argument("--no-confirm", action="store_true", help="Disable all confirmations")
    parser.add_argument("--session", metavar="ID", help="Session ID (use 'resume', 'list', or specific ID)")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel tool execution (P2)")
    parser.add_argument("--team", metavar="TASKS", help="Run multiple sub-agents in parallel (comma-separated tasks)")
    return parser.parse_args()


# ============ 主循环 ============
def main():
    args = parse_args()
    user_prompt = " ".join(args.prompt)

    # 会话列表（不需要 prompt）
    if args.session == "list":
        sessions = Session.list_all()
        if sessions:
            print("Sessions:")
            for s in sessions:
                title = s["title"] or "(no title)"
                print(f"  {s['id']}  [{s['msg_count']} msgs]  {title}")
        else:
            print("No sessions found.")
        sys.exit(0)

    if not user_prompt:
        print("Kodax Agent - 极致轻量化 Coding Agent\n")
        print("Usage: uv run kodax_agent.py \"your task\"")
        print("       uv run kodax_agent.py /skill_name")
        print("\nOptions:")
        print("  --provider NAME    LLM provider (anthropic, kimi, kimi-code, qwen, zhipu, openai)")
        print("  --thinking         Enable thinking mode (Anthropic, Kimi Code, Zhipu Coding)")
        print("  --confirm TOOLS    Tools requiring confirmation")
        print("  --no-confirm       Disable all confirmations")
        print("  --session ID       Session management (resume, list, or ID)")
        print("  --parallel         Enable parallel tool execution (P2)")
        print("  --team TASKS       Run multiple sub-agents in parallel (comma-separated)")
        print("\nSkills:")
        skills = load_skills()
        if skills:
            for name, info in skills.items():
                desc = info["desc"] or ""
                if desc:
                    print(f"  /{name:<15} {desc}")
                else:
                    print(f"  /{name}")
        else:
            print("  (no skills installed in ~/.kodax/skills/)")
        sys.exit(0)

    # 会话管理
    session_id = None
    if args.session == "resume":
        sessions = Session.list_all()
        session_id = sessions[0] if sessions else None
    elif args.session:
        session_id = args.session

    session = Session.load(session_id) if session_id else Session(id=time.strftime("%Y%m%d_%H%M%S"), messages=[])

    # Skill 检查
    if user_prompt.startswith("/"):
        parts = user_prompt[1:].split(maxsplit=1)
        skill_name, skill_args = parts[0], parts[1] if len(parts) > 1 else ""
        skills = load_skills()
        if skill_name in skills:
            class AgentProxy:
                def __init__(self): self.messages, self.provider, self.thinking = session.messages, args.provider, args.thinking
                def execute_tool(self, name, data): return execute_tool(name, data, set())
                def call_llm(self, msgs):
                    provider = PROVIDERS[self.provider]()
                    texts, _ = provider.stream(msgs, TOOLS, SYSTEM_PROMPT, self.thinking)
                    return texts[0]["text"] if texts else ""
            result = skills[skill_name]["func"](AgentProxy(), skill_args)
            print(result)
            sys.exit(0)
        else:
            print(f"Unknown skill: {skill_name}")
            sys.exit(1)

    # 确认工具
    confirm_tools = set() if args.no_confirm else (set(args.confirm.split(",")) if args.confirm else DEFAULT_CONFIRM_TOOLS)

    # P2: Agent Team 模式
    if args.team:
        tasks = [t.strip() for t in args.team.split(",") if t.strip()]
        if not tasks:
            print("Error: No tasks specified for --team")
            sys.exit(1)

        print(f"\033[36m[Kodax Team]\033[0m Running {len(tasks)} parallel agents with {args.provider}")
        if args.thinking:
            print(f"\033[36m[Kodax Team]\033[0m Thinking mode enabled")
        print()

        results = run_team(tasks, args.provider, args.thinking)

        print("\n" + "=" * 50)
        print("\033[36m[Kodax Team]\033[0m Results:")
        print("=" * 50)
        for i, (task, result) in enumerate(zip(tasks, results), 1):
            print(f"\n\033[33m[Task {i}]\033[0m {task[:60]}{'...' if len(task) > 60 else ''}")
            print(f"\033[32m[Result]\033[0m {result[:500]}{'...' if len(result) > 500 else ''}")
        print("\n\033[32m[Kodax Team]\033[0m All tasks completed!")
        sys.exit(0)

    # 初始化 Provider
    try:
        provider = PROVIDERS[args.provider]()
    except KeyError:
        print(f"Unknown provider: {args.provider}")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to initialize provider: {e}")
        sys.exit(1)

    # 添加用户消息
    session.messages.append({"role": "user", "content": user_prompt})

    print(f"\033[36m[Kodax]\033[0m Provider: {args.provider} | Session: {session.id}")
    if args.parallel: print(f"\033[36m[Kodax]\033[0m Parallel mode enabled")
    if confirm_tools: print(f"\033[36m[Kodax]\033[0m Confirm: {', '.join(sorted(confirm_tools))}")
    print()

    iteration, max_iter = 0, 50

    while iteration < max_iter:
        iteration += 1
        try:
            # 压缩上下文
            messages = compact_messages(session.messages)

            # 流式调用
            text_blocks, tool_blocks = provider.stream(messages, TOOLS, SYSTEM_PROMPT, args.thinking)

            # 构建 assistant content
            assistant_content = []
            for b in text_blocks: assistant_content.append({"type": "text", "text": b["text"]})
            for b in tool_blocks: assistant_content.append({"type": "tool_use", "id": b["id"], "name": b["name"], "input": b["input"]})
            session.messages.append({"role": "assistant", "content": assistant_content})

            if not tool_blocks:
                print("\n\033[32m[Kodax]\033[0m Done!")
                break

            # 执行工具
            tool_results = []

            if args.parallel and len(tool_blocks) > 1:
                # P2: 并行执行工具
                print(f"\n\033[36m[Kodax Parallel]\033[0m Executing {len(tool_blocks)} tools in parallel...")
                for tc in tool_blocks:
                    print(f"\033[33m[Tool]\033[0m {tc['name']}({str(tc['input'])[:60]}...)")
                results = execute_tools_parallel(tool_blocks, confirm_tools)
                for tc, result in zip(tool_blocks, results):
                    print(f"\033[32m[Result]\033[0m {result[:200]}{'...' if len(result) > 200 else ''}")
                    tool_results.append({"type": "tool_result", "tool_use_id": tc["id"], "content": result})
            else:
                # 顺序执行工具
                for tc in tool_blocks:
                    print(f"\n\033[33m[Tool]\033[0m {tc['name']}({str(tc['input'])[:80]}...)")
                    result = execute_tool(tc["name"], tc["input"], confirm_tools)
                    print(f"\033[32m[Result]\033[0m {result[:300]}{'...' if len(result) > 300 else ''}\n")
                    tool_results.append({"type": "tool_result", "tool_use_id": tc["id"], "content": result})

            session.messages.append({"role": "user", "content": tool_results})
            session.save()

        except KeyboardInterrupt:
            print("\n\033[33m[Kodax]\033[0m Interrupted")
            break
        except Exception as e:
            print(f"\n\033[31m[Error]\033[0m {e}")
            break

    session.save()
    if iteration >= max_iter:
        print("\n\033[33m[Kodax]\033[0m Max iterations reached")


if __name__ == "__main__":
    main()
