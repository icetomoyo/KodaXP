# Kodax Agent 手动测试指南

本文档提供 Kodax Agent 所有功能的手动测试步骤。

---

## 前置条件

```bash
# 1. 安装依赖
uv sync

# 2. 配置至少一个 Provider 的 API Key
export ZHIPU_API_KEY=your-key        # 智谱 Coding (推荐，便宜)
export KIMI_API_KEY=your-key          # Kimi Code
export ANTHROPIC_API_KEY=your-key     # Anthropic Claude
```

---

## P0 功能测试

### 1. 基本功能

```bash
# 测试基本对话和工具调用
uv run kodax_agent.py --provider zhipu-coding "列出当前目录下的文件"

# 预期：Agent 调用 glob 工具，列出文件，流式输出结果
```

### 2. 确认机制

```bash
# 测试需要确认的操作（默认 bash, write, edit 需确认）
uv run kodax_agent.py --provider zhipu-coding "创建一个测试文件 test_hello.txt，内容是 Hello World"

# 预期：
# 1. Agent 请求执行 write 工具
# 2. 显示 [Confirm] 提示，等待用户输入 y/N
# 3. 输入 y 后执行，输入 n 取消
```

```bash
# 测试禁用确认
uv run kodax_agent.py --provider zhipu-coding --no-confirm "删除 test_hello.txt 文件"

# 预期：直接执行，无需确认
```

```bash
# 测试自定义确认列表
uv run kodax_agent.py --provider zhipu-coding --confirm bash "查看当前时间"

# 预期：只有 bash 需要确认
```

### 3. 流式输出

```bash
# 测试流式输出效果
uv run kodax_agent.py --provider zhipu-coding "写一首关于编程的短诗"

# 预期：文字逐字符/逐词显示，而非一次性输出
```

---

## P1 功能测试

### 4. 多模型支持

```bash
# 测试不同 Provider
uv run kodax_agent.py --provider zhipu-coding "你好"           # 智谱 Coding (GLM-5)
uv run kodax_agent.py --provider kimi-code "你好"              # Kimi Code (K2.5)
uv run kodax_agent.py --provider zhipu "你好"                  # 智谱 SDK (GLM-4-plus)
uv run kodax_agent.py --provider kimi "你好"                   # Kimi Moonshot

# 预期：不同 Provider 都能正常响应
```

### 5. Thinking Mode

```bash
# 测试 Thinking Mode (仅 anthropic, kimi-code, zhipu-coding 支持)
uv run kodax_agent.py --provider zhipu-coding --thinking "计算 123 * 456 并解释步骤"

# 预期：
# 1. 显示灰色的 [Thinking] 块，包含思考过程
# 2. 然后显示正常回复
```

### 6. 会话管理

```bash
# 创建新会话
uv run kodax_agent.py --provider zhipu-coding "记住我的名字是 Alice"

# 列出会话
uv run kodax_agent.py --session list

# 预期输出：
# Sessions:
#   20260213_143000  [1 msgs]  记住我的名字是 Alice
```

```bash
# 恢复最近会话
uv run kodax_agent.py --provider zhipu-coding --session resume "我的名字是什么？"

# 预期：Agent 能回答 "Alice"
```

```bash
# 恢复指定会话
uv run kodax_agent.py --provider zhipu-coding --session 20260213_143000 "继续聊天"
```

### 7. Skill 系统

**创建测试 Skill（Linux/macOS）**:
```bash
mkdir -p ~/.kodax/skills
cat > ~/.kodax/skills/hello.py << 'EOF'
def skill_hello(agent, args: str) -> str:
    """打招呼"""
    name = args.strip() or "朋友"
    return f"你好，{name}！我是 Kodax Agent。"
EOF
```

**创建测试 Skill（Windows）**:
```powershell
# 使用 Python 创建 skill 文件
uv run python -c "
from pathlib import Path
skills_dir = Path.home() / '.kodax' / 'skills'
skills_dir.mkdir(parents=True, exist_ok=True)
skill_content = '''def skill_hello(agent, args: str) -> str:
    \"\"\"打招呼\"\"\"
    name = args.strip() or \"朋友\"
    return f\"你好，{name}！我是 Kodax Agent。\"
'''
(skills_dir / 'hello.py').write_text(skill_content, encoding='utf-8')
print('Skill created!')
"
```

**测试 Skill**:
```bash
# Linux/macOS
uv run kodax_agent.py /hello
uv run kodax_agent.py /hello World

# Windows Git Bash（注意：使用双斜杠避免路径转换）
uv run kodax_agent.py //hello
uv run kodax_agent.py //hello World

# Windows PowerShell/CMD
uv run kodax_agent.py /hello
```

**预期输出**:
```
你好，朋友！我是 Kodax Agent。
你好，World！我是 Kodax Agent。
```

> **注意**: 在 Windows Git Bash 中，`/hello` 会被解释为 Unix 路径并转换为 `C:/Program Files/Git/hello`。
> 使用 `//hello`（双斜杠）可以避免这个问题。

### 8. 上下文压缩

```bash
# 测试上下文压缩（需要较多消息触发）
# 创建一个长对话
uv run kodax_agent.py --provider zhipu-coding --session compress_test "
请执行以下步骤：
1. 创建文件 step1.txt 内容是 'Step 1 done'
2. 创建文件 step2.txt 内容是 'Step 2 done'
3. 创建文件 step3.txt 内容是 'Step 3 done'
4. 读取所有 step*.txt 文件
5. 总结你做了什么
"

# 预期：Agent 执行多个步骤，当消息过多时自动压缩上下文
# 控制台不会显示压缩信息，但功能在后台工作
```

---

## 上下文增强测试 (P1.5)

### 11. Git Context 自动注入

```bash
# 在 Git 仓库中测试
uv run kodax_agent.py --provider zhipu-coding "告诉我当前的 Git 分支和状态"

# 预期：Agent 能够直接回答当前分支，因为上下文已注入
```

```bash
# 在非 Git 目录测试
cd /tmp
uv run kodax_agent.py --provider zhipu-coding "告诉我当前的 Git 分支"

# 预期：Agent 不会因为缺少 Git 信息而报错
```

### 12. 项目快照

```bash
# 新会话时自动获取项目结构
uv run kodax_agent.py --provider zhipu-coding "描述这个项目的结构"

# 预期：Agent 能够基于注入的快照快速了解项目布局
```

```bash
# 恢复会话不会重复获取快照
uv run kodax_agent.py --provider zhipu-coding --session resume "继续"

# 预期：不会重复注入项目结构信息
```

### 13. Todo 自追踪

```bash
# 测试多步骤任务追踪
uv run kodax_agent.py --provider zhipu-coding "
请帮我完成以下任务：
1. 创建 test_todo.txt 文件
2. 写入 'Hello Todo'
3. 读取并确认内容
4. 删除该文件
"

# 预期：Agent 会逐步执行并追踪进度
```

### 14. 简单 Undo

```bash
# 测试 Undo 功能
uv run kodax_agent.py --provider zhipu-coding --no-confirm "
1. 创建 test_undo.txt，内容是 'Original Content'
2. 修改 test_undo.txt 为 'Modified Content'
3. 使用 undo 工具撤销修改
4. 读取 test_undo.txt 确认内容
"

# 预期：
# 1. 文件创建成功
# 2. 内容修改成功
# 3. undo 执行后恢复为 'Original Content'
```

```bash
# 测试 Undo 无备份情况
uv run kodax_agent.py --provider zhipu-coding "使用 undo 工具"

# 预期：返回 "No backups available. Nothing to undo."
```

---

## 长时间运行模式测试 (P1)

### 15. --init 初始化

```bash
# 测试长运行任务初始化
uv run kodax_agent.py --provider zhipu-coding --init "构建一个简单的 TODO 应用"

# 预期：
# 1. Agent 创建 feature_list.json（包含所有功能，每个 passes: false）
# 2. Agent 创建 PROGRESS.md
# 3. Agent 创建 init.sh（如果适用）
# 4. Agent 执行初始 git commit
```

```bash
# 检查创建的文件
ls feature_list.json PROGRESS.md init.sh

# 预期：三个文件都存在
```

### 16. 长运行模式自动检测

```bash
# 在有 feature_list.json 的目录运行
uv run kodax_agent.py --provider zhipu-coding "继续开发"

# 预期：
# 1. 显示 "[Kodax] Long-running mode enabled"
# 2. Agent 自动读取 feature_list.json 和 PROGRESS.md
# 3. Agent 选择一个未完成的功能开始工作
# 4. Agent 结束前更新 PROGRESS.md
```

### 17. 长运行模式提示词

验证 Agent 是否遵循长运行模式的标准流程：

```bash
# 预期 Agent 行为：
# 1. 执行 pwd 确认工作目录
# 2. 读取 git logs 了解最近工作
# 3. 读取 PROGRESS.md
# 4. 读取 feature_list.json
# 5. 选择一个 passes: false 的功能
# 6. 实现功能
# 7. 结束前 git commit + 更新 PROGRESS.md
```

### 18. --max-iter 参数

```bash
# 测试单次会话迭代限制
uv run kodax_agent.py --provider zhipu-coding --max-iter 5 "列出当前目录下的所有文件"

# 预期：Agent 在最多 5 次迭代内完成任务
```

```bash
# 测试低迭代限制（可能无法完成复杂任务）
uv run kodax_agent.py --provider zhipu-coding --max-iter 2 "创建 10 个测试文件"

# 预期：Agent 在 2 次迭代后停止（可能未完成）
```

### 19. --auto-continue 模式

```bash
# 1. 首先初始化长运行项目
uv run kodax_agent.py --provider zhipu-coding --init "构建简单的 TODO 应用"

# 2. 检查创建的文件
ls feature_list.json PROGRESS.md

# 3. 运行 auto-continue（带限制，防止无限运行）
uv run kodax_agent.py --provider zhipu-coding --auto-continue --max-sessions 3 --max-hours 0.5

# 预期：
# - 显示 "[Kodax] Auto-continue mode enabled"
# - 显示 feature 进度
# - 自动运行多个 session
# - 达到限制时显示停止原因
```

### 20. --auto-continue 依赖检查

```bash
# 在没有 feature_list.json 的目录运行 auto-continue
cd /tmp
uv run kodax_agent.py --provider zhipu-coding --auto-continue

# 预期输出：
# [Error] --auto-continue requires a long-running project.
#        Run 'kodax_agent.py --init "your task"' first.
```

### 21. --auto-continue 安全阀

```bash
# 测试最大会话数限制
uv run kodax_agent.py --provider zhipu-coding --auto-continue --max-sessions 1

# 预期：运行 1 个 session 后显示 "[Kodax] Max sessions reached (1)"
```

```bash
# 测试最大小时数限制
uv run kodax_agent.py --provider zhipu-coding --auto-continue --max-hours 0.01

# 预期：约 36 秒后显示 "[Kodax] Max hours reached (0.01h)"
```

```bash
# 测试所有功能完成后的自动停止
# 1. 手动修改 feature_list.json，将所有 passes 设为 true
# 2. 运行 auto-continue
uv run kodax_agent.py --provider zhipu-coding --auto-continue

# 预期：显示 "[Kodax] All features completed! (N/N)"
```

---

## P2 功能测试

### 9. 并行工具执行

```bash
# 测试并行读取多个文件
uv run kodax_agent.py --provider zhipu-coding --parallel "
读取 README.md, pyproject.toml, test_tools.py 这三个文件，
告诉我它们各自的用途
"

# 预期：
# 1. 显示 [Kodax Parallel] Executing 3 tools in parallel...
# 2. 同时显示 3 个 [Tool] 行
# 3. 工具并行执行，提高效率
```

### 10. Agent Team

```bash
# 测试多个子 Agent 并行执行
uv run kodax_agent.py --provider zhipu-coding --team "
分析 README.md 的内容结构,
检查 pyproject.toml 的依赖配置,
查看 kodax_agent.py 的代码行数
"

# 预期：
# 1. 显示 [Kodax Team] Running 3 parallel agents...
# 2. 三个子 Agent 同时工作
# 3. 最后汇总显示每个任务的结果
```

```bash
# Agent Team + Thinking Mode
uv run kodax_agent.py --provider zhipu-coding --thinking --team "
分析项目的整体架构,
评估代码质量
"
```

---

## 综合测试场景

### 场景 1：代码分析

```bash
uv run kodax_agent.py --provider zhipu-coding --parallel "
分析 kodax_agent.py 的整体结构，
列出所有类和它们的功能，
统计代码行数
"
```

### 场景 2：文件操作

```bash
uv run kodax_agent.py --provider zhipu-coding "
1. 在 /tmp 目录创建 test_kodax 文件夹
2. 在里面创建 3 个测试文件
3. 用 grep 搜索包含特定内容的文件
4. 最后清理这些文件
"
```

### 场景 3：复杂任务

```bash
uv run kodax_agent.py --provider zhipu-coding --thinking --session complex_task "
帮我完成以下任务：
1. 分析 docs/DESIGN.md 的结构
2. 检查是否与实际代码实现一致
3. 如果有不一致的地方，指出并建议修改
"
```

---

## 错误处理测试

### 1. 无效 Provider

```bash
uv run kodax_agent.py --provider invalid "test"
# 预期：显示错误 "Unknown provider: invalid"
```

### 2. 缺少 API Key

```bash
# 临时取消环境变量
unset ZHIPU_API_KEY
uv run kodax_agent.py --provider zhipu-coding "test"
# 预期：显示初始化错误
```

### 3. 文件不存在

```bash
uv run kodax_agent.py --provider zhipu-coding "读取 /nonexistent/file.txt"
# 预期：Agent 报告文件不存在错误
```

### 4. 无效会话

```bash
uv run kodax_agent.py --provider zhipu-coding --session nonexistent_session "test"
# 预期：创建新会话或正常处理
```

---

## 会话管理改进测试 (P1.5)

### 18. Session 项目关联

```bash
# 1. 在 KodaX 项目创建 session
cd /path/to/KodaX
uv run kodax_agent.py --provider zhipu-coding "记住项目名是 KodaX"

# 2. 查看创建的 session（应该显示）
uv run kodax_agent.py --session list
# 预期：显示刚创建的 session
```

```bash
# 3. 切换到另一个 Git 项目
cd /path/to/other-project

# 4. 测试 --session list（应该不显示 KodaX 的 session）
uv run kodax_agent.py --session list
# 预期：No sessions found. 或只显示当前项目的 sessions
```

```bash
# 5. 直接指定 KodaX session（应该警告项目不匹配）
uv run kodax_agent.py --provider zhipu-coding --session <kodax_session_id> "test"

# 预期输出：
# [Warning] Session project mismatch:
#   Current:  /path/to/other-project
#   Session:  /path/to/KodaX
#   Continuing anyway...
```

### 19. 子目录 Session 匹配

```bash
# 在项目子目录中测试（应该能正确匹配）
cd /path/to/KodaX/src
uv run kodax_agent.py --session list
# 预期：显示 KodaX 项目的 sessions（因为 git_root 相同）
```

---

## 测试检查清单

| 功能 | 测试命令 | 状态 |
|------|---------|------|
| 基本对话 | `uv run kodax_agent.py "你好"` | ☐ |
| 确认机制 | `uv run kodax_agent.py "创建文件"` | ☐ |
| 禁用确认 | `uv run kodax_agent.py --no-confirm "..."` | ☐ |
| 流式输出 | 观察输出是否逐步显示 | ☐ |
| Thinking Mode | `uv run kodax_agent.py --thinking "..."` | ☐ |
| Session List | `uv run kodax_agent.py --session list` | ☐ |
| Session Resume | `uv run kodax_agent.py --session resume "..."` | ☐ |
| Session 项目过滤 | 跨项目 `--session list` 测试 | ☐ |
| Session 跨项目警告 | 跨项目 `--session <id>` 测试 | ☐ |
| 并行执行 | `uv run kodax_agent.py --parallel "..."` | ☐ |
| Agent Team | `uv run kodax_agent.py --team "..."` | ☐ |
| Skill 调用 | `uv run kodax_agent.py /skill_name` | ☐ |
| 多 Provider | 切换不同 --provider 测试 | ☐ |
| Git Context | `uv run kodax_agent.py "当前分支是什么"` | ☐ |
| 项目快照 | `uv run kodax_agent.py "项目结构是什么"` | ☐ |
| Todo 追踪 | 多步骤任务测试 | ☐ |
| Undo | 修改后撤销测试 | ☐ |
| --max-iter | `uv run kodax_agent.py --max-iter 5 "..."` | ☐ |
| --init | `uv run kodax_agent.py --init "..."` | ☐ |
| --auto-continue | `uv run kodax_agent.py --auto-continue` | ☐ |
| --auto-continue 依赖检查 | 无 feature_list.json 时运行 | ☐ |
| --auto-continue 安全阀 | --max-sessions / --max-hours 测试 | ☐ |

---

## 性能测试

### 响应时间

```bash
# 测试首次响应时间
time uv run kodax_agent.py --provider zhipu-coding "你好"
# 预期：< 3 秒开始输出

# 测试并行效率
time uv run kodax_agent.py --provider zhipu-coding --parallel "读取 README.md, pyproject.toml"
time uv run kodax_agent.py --provider zhipu-coding "读取 README.md, pyproject.toml"
# 对比是否并行更快
```

---

## 常见问题排查

### 1. 认证错误

```
Error: Failed to initialize provider
```

**解决方案**：检查对应 Provider 的 API Key 是否正确设置。

### 2. 工具执行失败

```
Error: 'ToolUseBlock' object is not subscriptable
```

**解决方案**：这是已知 bug，已在 v0.1.0 修复。请确保使用最新版本。

### 3. 会话无法恢复

**解决方案**：确保会话 ID 正确，使用 `--session list` 查看可用会话。

---

## 测试报告模板

测试完成后，请记录：

```
测试日期：YYYY-MM-DD
测试人员：
Kodax 版本：v0.1.0
测试环境：Windows/macOS/Linux

测试结果：
- 通过的功能：
- 失败的功能：
- 发现的问题：

建议：
```
