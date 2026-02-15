# KodaXP 手动测试指南

本文档提供 KodaXP 所有功能的手动测试步骤。

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
uv run kodaxp.py --provider zhipu-coding "列出当前目录下的文件"

# 预期：Agent 调用 glob 工具，列出文件，流式输出结果
```

### 1.1 Plan Before Action（简单任务）

验证简单任务不需要正式计划：

```bash
# 简单只读任务应该直接执行
uv run kodaxp.py --provider zhipu-coding "读取 README.md 的前 10 行"

# 预期：Agent 直接执行，不需要先解释计划
```

### 1.2 Plan Before Action（复杂任务）

验证复杂任务会先思考再执行：

```bash
# 复杂任务应该先解释计划
uv run kodaxp.py --provider zhipu-coding --no-confirm "
创建一个 Python 脚本 calculate.py，包含加、减、乘、除四个函数，
每个函数都有类型注解和 docstring
"

# 预期 Agent 行为：
# 1. 先解释理解："我需要创建一个计算器脚本..."
# 2. 概述方法："我会创建包含四个函数的 Python 文件..."
# 3. 考虑潜在问题："需要处理除以零的情况..."
# 4. 然后执行
```

### 2. 确认机制

```bash
# 测试需要确认的操作（默认 bash, write, edit 需确认）
uv run kodaxp.py --provider zhipu-coding "创建一个测试文件 test_hello.txt，内容是 Hello World"

# 预期：
# 1. Agent 请求执行 write 工具
# 2. 显示 [Confirm] 提示，等待用户输入 y/N
# 3. 输入 y 后执行，输入 n 取消
```

```bash
# 测试禁用确认
uv run kodaxp.py --provider zhipu-coding --no-confirm "删除 test_hello.txt 文件"

# 预期：直接执行，无需确认
```

```bash
# 测试自定义确认列表
uv run kodaxp.py --provider zhipu-coding --confirm bash "查看当前时间"

# 预期：只有 bash 需要确认
```

### 3. 流式输出

```bash
# 测试流式输出效果
uv run kodaxp.py --provider zhipu-coding "写一首关于编程的短诗"

# 预期：文字逐字符/逐词显示，而非一次性输出
```

---

## P1 功能测试

### 4. 多模型支持

```bash
# 测试不同 Provider
uv run kodaxp.py --provider zhipu-coding "你好"           # 智谱 Coding (GLM-5)
uv run kodaxp.py --provider kimi-code "你好"              # Kimi Code (K2.5)
uv run kodaxp.py --provider zhipu "你好"                  # 智谱 SDK (GLM-4-plus)
uv run kodaxp.py --provider kimi "你好"                   # Kimi Moonshot

# 预期：不同 Provider 都能正常响应
```

### 5. Thinking Mode

```bash
# 测试 Thinking Mode (仅 anthropic, kimi-code, zhipu-coding 支持)
uv run kodaxp.py --provider zhipu-coding --thinking "计算 123 * 456 并解释步骤"

# 预期：
# 1. 显示灰色的 [Thinking] 块，包含思考过程
# 2. 然后显示正常回复
```

### 6. 会话管理

```bash
# 创建新会话
uv run kodaxp.py --provider zhipu-coding "记住我的名字是 Alice"

# 列出会话
uv run kodaxp.py --session list

# 预期输出：
# Sessions:
#   20260213_143000  [1 msgs]  记住我的名字是 Alice
```

```bash
# 恢复最近会话
uv run kodaxp.py --provider zhipu-coding --session resume "我的名字是什么？"

# 预期：Agent 能回答 "Alice"
```

```bash
# 恢复指定会话
uv run kodaxp.py --provider zhipu-coding --session 20260213_143000 "继续聊天"
```

### 7. Skill 系统

**创建测试 Skill（Linux/macOS）**:
```bash
mkdir -p ~/.kodaxp/skills
cat > ~/.kodaxp/skills/hello.py << 'EOF'
def skill_hello(agent, args: str) -> str:
    """打招呼"""
    name = args.strip() or "朋友"
    return f"你好，{name}！我是 KodaXP。"
EOF
```

**创建测试 Skill（Windows）**:
```powershell
# 使用 Python 创建 skill 文件
uv run python -c "
from pathlib import Path
skills_dir = Path.home() / '.kodaxp' / 'skills'
skills_dir.mkdir(parents=True, exist_ok=True)
skill_content = '''def skill_hello(agent, args: str) -> str:
    \"\"\"打招呼\"\"\"
    name = args.strip() or \"朋友\"
    return f\"你好，{name}！我是 KodaXP。\"
'''
(skills_dir / 'hello.py').write_text(skill_content, encoding='utf-8')
print('Skill created!')
"
```

**测试 Skill**:
```bash
# Linux/macOS
uv run kodaxp.py /hello
uv run kodaxp.py /hello World

# Windows Git Bash（注意：使用双斜杠避免路径转换）
uv run kodaxp.py //hello
uv run kodaxp.py //hello World

# Windows PowerShell/CMD
uv run kodaxp.py /hello
```

**预期输出**:
```
你好，朋友！我是 KodaXP。
你好，World！我是 KodaXP。
```

> **注意**: 在 Windows Git Bash 中，`/hello` 会被解释为 Unix 路径并转换为 `C:/Program Files/Git/hello`。
> 使用 `//hello`（双斜杠）可以避免这个问题。

### 8. 上下文压缩

```bash
# 测试上下文压缩（需要较多消息触发）
# 创建一个长对话
uv run kodaxp.py --provider zhipu-coding --session compress_test "
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
uv run kodaxp.py --provider zhipu-coding "告诉我当前的 Git 分支和状态"

# 预期：Agent 能够直接回答当前分支，因为上下文已注入
```

```bash
# 在非 Git 目录测试
cd /tmp
uv run kodaxp.py --provider zhipu-coding "告诉我当前的 Git 分支"

# 预期：Agent 不会因为缺少 Git 信息而报错
```

### 12. 项目快照

```bash
# 新会话时自动获取项目结构
uv run kodaxp.py --provider zhipu-coding "描述这个项目的结构"

# 预期：Agent 能够基于注入的快照快速了解项目布局
```

```bash
# 恢复会话不会重复获取快照
uv run kodaxp.py --provider zhipu-coding --session resume "继续"

# 预期：不会重复注入项目结构信息
```

### 13. Todo 自追踪

```bash
# 测试多步骤任务追踪
uv run kodaxp.py --provider zhipu-coding "
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
uv run kodaxp.py --provider zhipu-coding --no-confirm "
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
uv run kodaxp.py --provider zhipu-coding "使用 undo 工具"

# 预期：返回 "No backups available. Nothing to undo."
```

---

## 长时间运行模式测试 (P1)

### 15. --init 初始化

```bash
# 测试长运行任务初始化
uv run kodaxp.py --provider zhipu-coding --init "构建一个简单的 TODO 应用"

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

### 15.1 Feature 粒度验证（简单任务）

验证 Agent 是否正确识别任务复杂度并生成合适数量的 features。

```bash
# 测试简单任务（单文件 HTML）
uv run kodaxp.py --provider zhipu-coding --init "创建一个游戏行业介绍的交互式HTML页面"

# 预期：feature_list.json 有 1-3 个 features
# 例如：
# 1. "Create interactive HTML page for game industry introduction (content, styles, interactions)"
# 而不是：
# 1. "Create HTML structure" (太细碎)
# 2. "Add CSS styles" (太细碎)
# 3. "Add JavaScript" (太细碎)
# ...

cat feature_list.json
# 检查 features 数量是否合理
```

### 15.2 Feature 粒度验证（中等任务）

```bash
# 测试中等任务（多页网站）
uv run kodaxp.py --provider zhipu-coding --init "创建一个包含首页、关于页、联系页的多页网站"

# 预期：feature_list.json 有 3-8 个 features
# 例如：
# 1. "Create shared layout, navigation and footer"
# 2. "Create home page with hero section"
# 3. "Create about page"
# 4. "Create contact page with form"
```

### 15.3 Feature 粒度验证（复杂任务）

```bash
# 测试复杂任务（完整应用）
uv run kodaxp.py --provider zhipu-coding --init "创建一个完整的待办事项应用，包含前端、后端API和数据库"

# 预期：feature_list.json 有 8-15 个 features
# 例如：
# 1. "Set up project structure and database schema"
# 2. "Create todo API - list and create endpoints"
# 3. "Create todo API - update and delete endpoints"
# 4. "Set up frontend project with routing"
# 5. "Create todo list page"
# 6. "Create add/edit todo functionality"
# 7. "Add user authentication (optional)"
# 8. "Add data persistence and error handling"
```

### 16. 长运行模式自动检测

```bash
# 在有 feature_list.json 的目录运行
uv run kodaxp.py --provider zhipu-coding "继续开发"

# 预期：
# 1. 显示 "[Kodax] Long-running mode enabled"
# 2. Agent 自动读取 feature_list.json 和 PROGRESS.md
# 3. Agent 选择一个未完成的功能开始工作
# 4. Agent 结束前更新 PROGRESS.md
```

### 17.1 Session 计划机制（新增）

验证 Agent 是否在执行前创建计划文件：

```bash
# 1. 初始化长运行任务
uv run kodaxp.py --provider zhipu-coding --init "构建用户认证系统"

# 2. 运行第一个 session
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 1

# 3. 检查是否创建了 .kodaxp 目录和 session_plan.md
ls -la .kodaxp/
cat .kodaxp/session_plan.md

# 预期 session_plan.md 内容结构：
# # Session Plan
#
# **Date**: 2026-02-15
# **Feature**: User authentication
#
# ## Understanding
# [Agent 的理解]
#
# ## Approach
# [Agent 的实现方案]
#
# ## Steps
# 1. ...
# 2. ...
#
# ## Considerations
# - ...
#
# ## Risks
# - ...
```

### 17.2 PROGRESS.md 计划摘要

验证 PROGRESS.md 是否包含计划摘要：

```bash
# 检查 PROGRESS.md 是否包含计划摘要
cat PROGRESS.md

# 预期内容结构：
# ## Session 1 - 2026-02-15
#
# ### Plan
# Implement user authentication with JWT tokens
#
# ### Completed
# - Created user model
# - Added login/logout routes
#
# ### Notes
# - Used bcrypt for password hashing
# - Tested all endpoints with curl
```

### 17.3 跨 Session 连续性

验证计划机制是否保持跨 session 的连续性：

```bash
# 1. 运行多个 sessions
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 3

# 2. 检查 PROGRESS.md 是否包含所有 sessions 的计划摘要
cat PROGRESS.md

# 3. 检查 .kodaxp/session_plan.md 是否是最新 session 的计划
cat .kodaxp/session_plan.md

# 预期：
# - PROGRESS.md 包含 Session 1, 2, 3 的计划摘要
# - session_plan.md 是 Session 3 的完整计划
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
uv run kodaxp.py --provider zhipu-coding --max-iter 5 "列出当前目录下的所有文件"

# 预期：Agent 在最多 5 次迭代内完成任务
```

```bash
# 测试低迭代限制（可能无法完成复杂任务）
uv run kodaxp.py --provider zhipu-coding --max-iter 2 "创建 10 个测试文件"

# 预期：Agent 在 2 次迭代后停止（可能未完成）
```

### 19. --auto-continue 模式

```bash
# 1. 首先初始化长运行项目
uv run kodaxp.py --provider zhipu-coding --init "构建简单的 TODO 应用"

# 2. 检查创建的文件
ls feature_list.json PROGRESS.md

# 3. 运行 auto-continue（带限制，防止无限运行）
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 3 --max-hours 0.5

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
uv run kodaxp.py --provider zhipu-coding --auto-continue

# 预期输出：
# [Error] --auto-continue requires a long-running project.
#        Run 'kodaxp.py --init "your task"' first.
```

### 21. --auto-continue 安全阀

```bash
# 测试最大会话数限制
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 1

# 预期：运行 1 个 session 后显示 "[Kodax] Max sessions reached (1)"
```

```bash
# 测试最大小时数限制
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-hours 0.01

# 预期：约 36 秒后显示 "[Kodax] Max hours reached (0.01h)"
```

```bash
# 测试所有功能完成后的自动停止
# 1. 手动修改 feature_list.json，将所有 passes 设为 true
# 2. 运行 auto-continue
uv run kodaxp.py --provider zhipu-coding --auto-continue

# 预期：显示 "[Kodax] All features completed! (N/N)"
```

### 22. Promise 信号系统 (Ralph-Loop 风格)

Agent 可以通过特殊信号与 auto-continue 循环通信。

```bash
# 测试 Promise COMPLETE 信号
# Agent 完成所有功能时应输出:
# <promise>COMPLETE</promise>

uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 5

# 预期：如果 Agent 输出 <promise>COMPLETE</promise>，则显示:
# [Kodax Auto-Continue] Agent signaled COMPLETE
# 并退出循环
```

```bash
# 测试 Promise BLOCKED 信号
# Agent 遇到阻塞时应输出:
# <promise>BLOCKED:原因描述</promise>

# 预期：如果 Agent 输出 <promise>BLOCKED:Need API key</promise>，则显示:
# [Kodax Auto-Continue] Agent BLOCKED: Need API key
# Waiting for human intervention...
# 并退出循环
```

```bash
# 测试 Promise DECIDE 信号
# Agent 需要用户决策时应输出:
# <promise>DECIDE:问题</promise>

# 预期：如果 Agent 输出 <promise>DECIDE:Which framework?</promise>，则显示:
# [Kodax Auto-Continue] Agent needs decision: Which framework?
# 并退出循环等待用户输入
```

### 23. 增量开发测试 (--append 和 --overwrite)

测试在已完成的项目上添加新功能。

```bash
# 1. 第一次 init（创建初始项目）
uv run kodaxp.py --provider zhipu-coding --init "构建基础 TODO 应用"

# 2. 完成所有功能
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 20

# 3. 尝试第二次 init（无 --append 或 --overwrite）
uv run kodaxp.py --provider zhipu-coding --init "添加搜索功能"

# 预期输出：
# [Warning] feature_list.json already exists!
#   Current: X features (Y complete, Z pending)
#
#   Options:
#   --append      Add new features to existing list (recommended)
#   --overwrite   Start fresh (existing features will be lost)
#
#   Example:
#   uv run kodaxp.py --init "添加搜索功能" --append
```

```bash
# 4. 使用 --append 增量添加
uv run kodaxp.py --provider zhipu-coding --init "添加搜索功能" --append

# 预期：
# [Kodax] Appending to existing project (X features, Y complete)
# [Kodax] Adding new features for: 添加搜索功能
# Agent 使用 EDIT 工具追加新 features 到 feature_list.json

# 检查 feature_list.json：
# - 原有 features 应该保留（passes: true）
# - 新 features 应该添加在后面（passes: false）
```

```bash
# 5. 继续运行 --auto-continue
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 10

# 预期：
# - 只处理 passes: false 的新 features
# - 已完成的 features 不会被重复处理
```

```bash
# 6. 使用 --overwrite 完全重置
uv run kodaxp.py --provider zhipu-coding --init "全新项目" --overwrite

# 预期输出：
# [Warning] Overwriting existing feature_list.json (X features will be lost)
# [Kodax] Initializing fresh project: 全新项目

# 检查 feature_list.json：
# - 旧 features 全部丢失
# - 只有新项目的 features
```

### 24. 增量开发场景测试

测试不同场景下的增量开发。

```bash
# 场景 1：Bug 修复作为新 feature
uv run kodaxp.py --provider zhipu-coding --init "修复用户输入验证的 bug" --append

# 预期：新 feature "Fix: user input validation bug" 被添加到列表
```

```bash
# 场景 2：重构作为新 feature
uv run kodaxp.py --provider zhipu-coding --init "重构数据库访问层" --append

# 预期：新 feature "Refactor: database access layer" 被添加到列表
```

```bash
# 场景 3：性能优化作为新 feature
uv run kodaxp.py --provider zhipu-coding --init "优化查询性能" --append

# 预期：新 feature "Optimize: query performance" 被添加到列表
```

---

## P2 功能测试

### 9. 并行工具执行

```bash
# 测试并行读取多个文件
uv run kodaxp.py --provider zhipu-coding --parallel "
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
uv run kodaxp.py --provider zhipu-coding --team "
分析 README.md 的内容结构,
检查 pyproject.toml 的依赖配置,
查看 kodaxp.py 的代码行数
"

# 预期：
# 1. 显示 [Kodax Team] Running 3 parallel agents...
# 2. 三个子 Agent 同时工作
# 3. 最后汇总显示每个任务的结果
```

```bash
# Agent Team + Thinking Mode
uv run kodaxp.py --provider zhipu-coding --thinking --team "
分析项目的整体架构,
评估代码质量
"
```

---

## 综合测试场景

### 场景 1：代码分析

```bash
uv run kodaxp.py --provider zhipu-coding --parallel "
分析 kodaxp.py 的整体结构，
列出所有类和它们的功能，
统计代码行数
"
```

### 场景 2：文件操作

```bash
uv run kodaxp.py --provider zhipu-coding "
1. 在 /tmp 目录创建 test_kodax 文件夹
2. 在里面创建 3 个测试文件
3. 用 grep 搜索包含特定内容的文件
4. 最后清理这些文件
"
```

### 场景 3：复杂任务

```bash
uv run kodaxp.py --provider zhipu-coding --thinking --session complex_task "
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
uv run kodaxp.py --provider invalid "test"
# 预期：显示错误 "Unknown provider: invalid"
```

### 2. 缺少 API Key

```bash
# 临时取消环境变量
unset ZHIPU_API_KEY
uv run kodaxp.py --provider zhipu-coding "test"
# 预期：显示初始化错误
```

### 3. 文件不存在

```bash
uv run kodaxp.py --provider zhipu-coding "读取 /nonexistent/file.txt"
# 预期：Agent 报告文件不存在错误
```

### 4. 无效会话

```bash
uv run kodaxp.py --provider zhipu-coding --session nonexistent_session "test"
# 预期：创建新会话或正常处理
```

---

## 会话管理改进测试 (P1.5)

### 18. Session 项目关联

```bash
# 1. 在 KodaXP 项目创建 session
cd /path/to/KodaXP
uv run kodaxp.py --provider zhipu-coding "记住项目名是 KodaX"

# 2. 查看创建的 session（应该显示）
uv run kodaxp.py --session list
# 预期：显示刚创建的 session
```

```bash
# 3. 切换到另一个 Git 项目
cd /path/to/other-project

# 4. 测试 --session list（应该不显示 KodaXP 的 session）
uv run kodaxp.py --session list
# 预期：No sessions found. 或只显示当前项目的 sessions
```

```bash
# 5. 直接指定 KodaXP session（应该警告项目不匹配）
uv run kodaxp.py --provider zhipu-coding --session <kodax_session_id> "test"

# 预期输出：
# [Warning] Session project mismatch:
#   Current:  /path/to/other-project
#   Session:  /path/to/KodaXP
#   Continuing anyway...
```

### 19. 子目录 Session 匹配

```bash
# 在项目子目录中测试（应该能正确匹配）
cd /path/to/KodaXP/src
uv run kodaxp.py --session list
# 预期：显示 KodaXP 项目的 sessions（因为 git_root 相同）
```

---

## Windows 环境兼容性测试 (P0)

### 23. 环境感知与跨平台命令测试

验证 Agent 是否能根据平台信息使用正确的命令。

```bash
# 测试环境上下文注入（Windows）
uv run kodaxp.py --provider zhipu-coding --no-confirm "
创建一个 test_env.txt 文件，然后移动到 test_folder 文件夹
"

# 预期（Windows）：
# 1. Context 显示 "Platform: Windows (use: dir, move, copy, del)"
# 2. Agent 使用 move 命令（而非 mv）
# 3. 文件成功移动

# 预期（Unix/Mac）：
# 1. Context 显示 "Platform: linux/darwin"
# 2. Agent 使用 mv 命令
```

```bash
# 测试错误识别与恢复
uv run kodaxp.py --provider zhipu-coding --no-confirm "
列出当前目录所有文件（使用 ls 命令）
"

# 预期（Windows）：
# 1. 如果 Agent 错误使用了 ls，会看到 "不是内部或外部命令" 错误
# 2. Agent 应该识别这是平台问题，改用 dir 命令
# 3. 不会尝试 "读文件→重写" 的错误方案

# 预期（Unix/Mac）：
# ls 命令正常工作
```

```bash
# 验证上下文注入
# 在新会话中，Agent 应该能看到平台信息
uv run kodaxp.py --provider zhipu-coding "
告诉我你运行在什么平台上
"

# 预期：Agent 能回答 "Windows" 或对应平台
```

### 24. UTF-8 编码测试

```bash
# 测试中文输出
uv run kodaxp.py --provider zhipu-coding --no-confirm "echo '测试中文输出'"

# 预期：输出包含 "测试中文输出"，没有 UnicodeDecodeError
```

```bash
# 测试中文 commit message
uv run kodaxp.py --provider zhipu-coding --no-confirm "
1. 创建 test_cn.txt，内容是 '测试'
2. git add test_cn.txt
3. git commit -m '添加测试文件'
"

# 预期：git commit 成功，没有 index.lock 错误，没有编码错误
```

### 25. Git 命令顺序执行测试

```bash
# 测试连续 git 命令不会触发 race condition
uv run kodaxp.py --provider zhipu-coding --parallel --no-confirm "
1. git add .
2. git status
3. git log --oneline -3
"

# 预期：
# 1. 没有 ".git/index.lock" 错误
# 2. bash 命令顺序执行
# 3. git status 等非 bash 命令可以并行
```

### 26. Thinking Mode 多轮测试

```bash
# 测试 kimi-code thinking mode 多轮工具调用
uv run kodaxp.py --provider kimi-code --thinking --no-confirm "
1. 读取 README.md
2. 总结主要内容
"

# 预期：
# 1. 没有 "thinking is enabled but reasoning_content is missing" 错误
# 2. 能正常执行多轮工具调用
# 3. 显示 [Thinking] 块
```

```bash
# 测试 zhipu-coding thinking mode
uv run kodaxp.py --provider zhipu-coding --thinking --no-confirm "
1. 列出当前目录文件
2. 找到所有 .md 文件
"

# 预期：同上
```

### 27. 跨平台路径测试

```bash
# 测试 Windows 路径处理
uv run kodaxp.py --provider zhipu-coding --no-confirm "
读取 C:/Works/Projects/KodaXP/README.md 的前 10 行
"

# 预期：正确读取文件，路径处理正常
```

---

## 测试检查清单

| 功能 | 测试命令 | 状态 |
|------|---------|------|
| 基本对话 | `uv run kodaxp.py "你好"` | ☐ |
| 确认机制 | `uv run kodaxp.py "创建文件"` | ☐ |
| 禁用确认 | `uv run kodaxp.py --no-confirm "..."` | ☐ |
| 流式输出 | 观察输出是否逐步显示 | ☐ |
| 等待指示器 | 观察 `[Assistant]` 后是否出现 `.....` | ☐ |
| Thinking Mode | `uv run kodaxp.py --thinking "..."` | ☐ |
| Session List | `uv run kodaxp.py --session list` | ☐ |
| Session Resume | `uv run kodaxp.py --session resume "..."` | ☐ |
| Session 项目过滤 | 跨项目 `--session list` 测试 | ☐ |
| Session 跨项目警告 | 跨项目 `--session <id>` 测试 | ☐ |
| 并行执行 | `uv run kodaxp.py --parallel "..."` | ☐ |
| Agent Team | `uv run kodaxp.py --team "..."` | ☐ |
| Skill 调用 | `uv run kodaxp.py /skill_name` | ☐ |
| 多 Provider | 切换不同 --provider 测试 | ☐ |
| Git Context | `uv run kodaxp.py "当前分支是什么"` | ☐ |
| 项目快照 | `uv run kodaxp.py "项目结构是什么"` | ☐ |
| Todo 追踪 | 多步骤任务测试 | ☐ |
| Undo | 修改后撤销测试 | ☐ |
| --max-iter | `uv run kodaxp.py --max-iter 5 "..."` | ☐ |
| --init | `uv run kodaxp.py --init "..."` | ☐ |
| --auto-continue | `uv run kodaxp.py --auto-continue` | ☐ |
| --auto-continue 依赖检查 | 无 feature_list.json 时运行 | ☐ |
| --auto-continue 安全阀 | --max-sessions / --max-hours 测试 | ☐ |
| Promise 信号 | Agent 主动发送 COMPLETE/BLOCKED/DECIDE | ☐ |
| **Windows UTF-8 编码** | 中文输出测试 | ☐ |
| **环境感知注入** | Agent 知道运行平台 | ☐ |
| **跨平台命令** | Windows 用 move 而非 mv | ☐ |
| **Git 顺序执行** | 并行模式下连续 git 命令 | ☐ |
| **Thinking 多轮调用** | kimi-code/zhipu-coding thinking 多工具 | ☐ |
| **错误信息增强** | 缺少参数时显示详细错误 | ☐ |
| **错误恢复指导** | 模型不重复同样的错误 | ☐ |
| **截断检测** | 大文件写入时自动检测缺失参数 | ☐ |
| **自动重试** | 检测截断后自动发送 follow-up 请求 | ☐ |
| **分级重试提示** | 根据重试次数动态调整提示强度 | ☐ |
| **分段写入引导** | 提示词引导 LLM 分段写入大文件 | ☐ |

---

## 错误处理增强测试 (P0)

### 27. 错误信息增强测试

测试改进后的错误信息是否清晰。

```bash
# 测试缺少 command 参数的错误信息
# 在对话中引导 Agent 犯错（或不提供参数）
uv run kodaxp.py --provider zhipu-coding --no-confirm "
尝试调用 bash 工具但不提供 command 参数，看看错误信息是什么
"

# 预期错误信息：
# [Tool Error] bash: Missing required parameter 'command'. Check tool schema and provide all required parameters.
```

```bash
# 测试 edit 工具缺少 new_string 参数
uv run kodaxp.py --provider zhipu-coding --no-confirm "
尝试编辑 test.txt 文件，只提供 path 和 old_string，不提供 new_string
"

# 预期错误信息：
# [Tool Error] edit: Missing required parameter 'new_string'. Check tool schema and provide all required parameters.
```

### 28. 错误恢复测试

测试模型是否能在收到错误后正确修复，而不是重复同样的错误。

```bash
# 测试长时间任务中的错误恢复
uv run kodaxp.py --provider zhipu-coding --auto-continue --max-sessions 3 "
执行一个多步骤任务，故意在某一步可能犯错，观察是否能自我修复
"

# 预期：
# 1. 模型收到错误后不重复同样的工具调用
# 2. 模型能根据错误信息修复问题
# 3. 任务能继续进行
```

### 29. 错误信息对比

| 场景 | 旧错误信息 | 新错误信息 |
|------|-----------|-----------|
| bash 缺少 command | `Error: 'command'` | `[Tool Error] bash: Missing required parameter 'command'. Check tool schema and provide all required parameters.` |
| edit 缺少 new_string | `Error: 'new_string'` | `[Tool Error] edit: Missing required parameter 'new_string'. Check tool schema and provide all required parameters.` |
| read 文件不存在 | `Error: File not found: /path` | `[Tool Error] read: File not found: /path` |
| edit 字符串未找到 | `Error: String not found` | `[Tool Error] edit: String not found` |

---

## 截断检测与自动重试测试 (P0)

### 30. 大文件写入截断检测

测试当 LLM 响应被截断导致工具参数缺失时，系统是否能自动重试。

```bash
# 测试大文件写入（可能触发截断）
uv run kodaxp.py --provider zhipu-coding --no-confirm "
创建一个包含 500 行 HTML 代码的文件 large_test.html
"

# 预期行为：
# 如果检测到工具参数缺失：
# 1. 显示 "[Kodax] Detected incomplete tool call(s): write: missing 'content'"
# 2. 显示 "[Kodax] Requesting completion (retry 1/2)..."
# 3. 自动发送 follow-up 请求让 LLM 补全
# 4. 最多重试 2 次
```

### 31. 截断重试成功场景

```bash
# 观察自动重试是否成功
uv run kodaxp.py --provider kimi-code --thinking --no-confirm "
创建一个较复杂的 HTML 文件，包含头部、导航栏、主要内容区域和页脚
"

# 预期：
# - 如果首次响应被截断，系统自动重试
# - 重试后 LLM 可能采用分段写入策略（先写结构，再用 edit 添加内容）
# - 最终文件创建成功
```

### 32. 截断重试耗尽场景

```bash
# 测试重试次数耗尽后的行为
# （需要人为触发，正常情况下不会发生）
# 当重试 2 次后仍然失败，系统会继续执行工具（返回错误信息）

# 预期：
# 显示 "[Kodax] Max retries reached for incomplete tool calls."
# 然后继续执行工具，返回错误信息给 LLM
```

### 33. 分段写入最佳实践验证

```bash
# 验证提示词引导是否生效
uv run kodaxp.py --provider zhipu-coding --no-confirm "
创建一个大型配置文件 config.yaml，包含数据库配置、缓存配置、日志配置等多个部分
"

# 预期行为（如果提示词引导生效）：
# 1. LLM 先写入基本结构/骨架
# 2. 然后使用 edit 逐步添加各部分配置
# 而不是一次性写入所有内容
```

### 34. 分级重试提示验证

测试改进后的 retry prompt 是否根据重试次数动态调整强度。

```bash
# 测试分级重试提示（需要观察 session 文件中的 retry_prompt）
uv run kodaxp.py --provider zhipu-coding --no-confirm "
创建一个非常大的 Python 文件，包含 10 个工具函数，每个函数都有完整的 docstring 和类型注解
"

# 预期行为：
# 第一次重试（retry 1/2）：
#   - 提示词较温和："Your previous response was truncated..."
#   - 建议 "keep it concise (under 50 lines)"
#
# 第二次重试（retry 2/2）：
#   - 提示词强烈："⚠️ CRITICAL: Your response was TRUNCATED again..."
#   - 具体限制："under 50 lines for write", "under 30 lines for edit"
#   - 警告："If your response is truncated again, the task will FAIL."
```

### 35. 截断检测日志

| 场景 | 预期日志 |
|------|---------|
| 检测到参数缺失 | `[Kodax] Detected incomplete tool call(s): write: missing 'content'` |
| 第一次重试 | `[Kodax] Requesting completion (retry 1/2)...` |
| 第二次重试 | `[Kodax] Requesting completion (retry 2/2)...` |
| 重试成功 | 继续正常执行工具 |
| 重试耗尽 | `[Kodax] Max retries reached for incomplete tool calls.` |

---

## 性能测试

### 响应时间

```bash
# 测试首次响应时间
time uv run kodaxp.py --provider zhipu-coding "你好"
# 预期：< 3 秒开始输出

# 测试并行效率
time uv run kodaxp.py --provider zhipu-coding --parallel "读取 README.md, pyproject.toml"
time uv run kodaxp.py --provider zhipu-coding "读取 README.md, pyproject.toml"
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
