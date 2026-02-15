"""测试 kodaxp P1 + P2 功能"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')

from kodaxp import execute_tool, estimate_tokens, compact_messages, Session, load_skills, PROVIDERS
from kodaxp import execute_tools_parallel, run_subagent
from pathlib import Path
import tempfile
import os
import json

def test_tools():
    print("=" * 50)
    print("Testing tools")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        # read/write
        test_file = os.path.join(tmpdir, "test.txt")
        result = execute_tool("write", {"path": test_file, "content": "Hello"}, set())
        assert "written" in result.lower()
        result = execute_tool("read", {"path": test_file}, set())
        assert result == "Hello"
        print("  ✓ read/write")

        # edit
        result = execute_tool("edit", {"path": test_file, "old_string": "Hello", "new_string": "World"}, set())
        assert "edited" in result.lower()
        print("  ✓ edit")

        # glob
        result = execute_tool("glob", {"pattern": "*.txt", "path": tmpdir}, set())
        assert "test.txt" in result
        print("  ✓ glob")

        # grep
        result = execute_tool("grep", {"pattern": "World", "path": tmpdir}, set())
        assert "World" in result
        print("  ✓ grep")

        # bash
        result = execute_tool("bash", {"command": "echo test"}, set())
        assert "test" in result
        print("  ✓ bash")


def test_token_estimation():
    print("\n" + "=" * 50)
    print("Testing token estimation")
    print("=" * 50)

    # 简单消息
    messages = [{"role": "user", "content": "x" * 100}]
    tokens = estimate_tokens(messages)
    assert tokens == 25  # 100 / 4
    print(f"  Simple message: {tokens} tokens ✓")

    # 复杂消息
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "Hi there"}]}
    ]
    tokens = estimate_tokens(messages)
    print(f"  Complex message: {tokens} tokens ✓")


def test_compact():
    print("\n" + "=" * 50)
    print("Testing context compaction")
    print("=" * 50)

    # 创建大量消息
    messages = [{"role": "user", "content": "x" * 10000} for _ in range(20)]
    original_tokens = estimate_tokens(messages)
    print(f"  Before: {original_tokens} tokens")

    compressed = compact_messages(messages, max_tokens=10000)
    compressed_tokens = estimate_tokens(compressed)
    print(f"  After: {compressed_tokens} tokens")

    assert compressed_tokens < original_tokens
    print("  ✓ Compaction works")


def test_session():
    print("\n" + "=" * 50)
    print("Testing session management")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 修改 SESSIONS_DIR
        import kodaxp
        original_dir = kodaxp.SESSIONS_DIR
        kodaxp.SESSIONS_DIR = Path(tmpdir)

        try:
            # 测试带标题的会话
            session = kodaxp.Session(id="test_session", messages=[])
            session.messages.append({"role": "user", "content": "Hello World, this is a test message"})
            session.save()

            # 验证标题自动生成
            assert session.title == "Hello World, this is a test message", f"Expected title from first message, got: {session.title}"
            print("  ✓ Session title auto-generation")

            # 重新加载
            loaded = kodaxp.Session.load("test_session")
            assert len(loaded.messages) == 1
            assert loaded.messages[0]["content"] == "Hello World, this is a test message"
            assert loaded.title == "Hello World, this is a test message"
            print("  ✓ Session save/load with title")

            # 测试 list_all 返回 dict
            sessions = kodaxp.Session.list_all()
            assert len(sessions) == 1
            assert sessions[0]["id"] == "test_session"
            assert sessions[0]["title"] == "Hello World, this is a test message"
            assert sessions[0]["msg_count"] == 1
            print("  ✓ Session list_all returns dict with id, title, msg_count")

            # 测试长标题截断
            long_session = kodaxp.Session(id="long_session", messages=[])
            long_msg = "A" * 100  # 100 字符
            long_session.messages.append({"role": "user", "content": long_msg})
            long_session.save()
            assert len(long_session.title) == 53  # 50 字符 + "..."
            assert long_session.title.endswith("...")
            print("  ✓ Long title truncation (50 chars + ...)")

            # 测试 git_root 保存
            session_path = Path(tmpdir) / "test_session.jsonl"
            meta_line = session_path.read_text(encoding="utf-8").split("\n")[0]
            meta = json.loads(meta_line)
            assert "git_root" in meta, "git_root should be in session metadata"
            print("  ✓ Session saves git_root in metadata")

        finally:
            kodaxp.SESSIONS_DIR = original_dir


def test_providers():
    print("\n" + "=" * 50)
    print("Testing provider registry")
    print("=" * 50)

    expected = {"anthropic", "kimi", "kimi-code", "qwen", "openai", "zhipu", "zhipu-coding"}
    actual = set(PROVIDERS.keys())

    assert expected == actual, f"Expected {expected}, got {actual}"
    print(f"  Available providers: {', '.join(sorted(actual))}")
    print("  ✓ All providers registered")


def test_skills():
    print("\n" + "=" * 50)
    print("Testing skill system")
    print("=" * 50)

    skills = load_skills()
    print(f"  Loaded skills: {list(skills.keys()) or '(none)'}")
    print("  ✓ Skill loading works")


def test_parallel_execution():
    print("\n" + "=" * 50)
    print("Testing parallel tool execution (P2)")
    print("=" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试文件
        for i in range(3):
            test_file = os.path.join(tmpdir, f"test{i}.txt")
            execute_tool("write", {"path": test_file, "content": f"Content {i}"}, set())

        # 并行读取多个文件
        tool_calls = [
            {"name": "read", "input": {"path": os.path.join(tmpdir, "test0.txt")}, "id": "1"},
            {"name": "read", "input": {"path": os.path.join(tmpdir, "test1.txt")}, "id": "2"},
            {"name": "read", "input": {"path": os.path.join(tmpdir, "test2.txt")}, "id": "3"},
        ]

        results = execute_tools_parallel(tool_calls, set())
        assert len(results) == 3
        assert "Content 0" in results[0]
        assert "Content 1" in results[1]
        assert "Content 2" in results[2]
        print("  ✓ Parallel execution works")


def test_subagent():
    print("\n" + "=" * 50)
    print("Testing sub-agent (P2)")
    print("=" * 50)

    # 测试子 agent 函数存在（实际调用需要 API key）
    assert callable(run_subagent)
    print("  ✓ Sub-agent function available")


def test_promise_signals():
    print("\n" + "=" * 50)
    print("Testing promise signals (Ralph-Loop style)")
    print("=" * 50)

    from kodaxp import check_promise_signal

    # 测试 COMPLETE 信号
    signal, reason = check_promise_signal("Great work! <promise>COMPLETE</promise>")
    assert signal == "COMPLETE"
    assert reason == ""
    print("  ✓ COMPLETE signal detected")

    # 测试 BLOCKED 信号带原因
    signal, reason = check_promise_signal("I'm stuck: <promise>BLOCKED:Need API key</promise>")
    assert signal == "BLOCKED"
    assert reason == "Need API key"
    print("  ✓ BLOCKED signal with reason detected")

    # 测试 DECIDE 信号
    signal, reason = check_promise_signal("<promise>DECIDE:Which framework to use?</promise>")
    assert signal == "DECIDE"
    assert reason == "Which framework to use?"
    print("  ✓ DECIDE signal with reason detected")

    # 测试无信号
    signal, reason = check_promise_signal("This is normal output without any promise")
    assert signal == ""
    assert reason == ""
    print("  ✓ No signal in normal text")

    # 测试大小写不敏感
    signal, reason = check_promise_signal("<promise>complete</promise>")
    assert signal == "COMPLETE"
    print("  ✓ Case-insensitive detection")


if __name__ == "__main__":
    test_tools()
    test_token_estimation()
    test_compact()
    test_session()
    test_providers()
    test_skills()
    test_parallel_execution()
    test_subagent()
    test_promise_signals()

    print("\n" + "=" * 50)
    print("ALL P1 + P2 TESTS PASSED!")
    print("=" * 50)
