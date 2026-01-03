# 查看 PIXIU Codex Agent 详细信息

## 概述

PIXIU 的 Codex 在 Harbor 模式下现在可以保存详细的 agent 执行信息，就像 Harbor 一样。这些信息包括：
- Codex CLI 的完整输出（JSON 格式）
- 每个命令的执行详情（command, stdout, stderr, return-code）

## 启用 Agent 详细信息保存

### 方法 1: 使用 write_out 参数（推荐）

```bash
cd /home/hefan/PIXIU
python src/eval.py \
    --model codex \
    --model_args "model=gpt-5-mini,harbor_mode=True" \
    --tasks flare-cra-taiwan \
    --limit 5 \
    --write_out \
    --output_base_path results/harbor_test
```

当 `write_out=True` 时，会自动启用 agent 详细信息保存。

### 方法 2: 手动设置

```python
from codexlm import CodexLM

lm = CodexLM(model="gpt-5-mini", harbor_mode=True)
lm._save_agent_details = True
lm._agent_log_base_dir = "/path/to/agent_logs"
```

## 保存的文件结构

Agent 详细信息保存在 `output_base_path/agent_details/` 目录下：

```
results/harbor_test/
├── agent_details/
│   └── agent_<doc_id>/
│       ├── command-0/
│       │   ├── command.txt      # 创建 auth.json 的命令
│       │   ├── return-code.txt  # 返回码
│       │   ├── stdout.txt       # 标准输出
│       │   └── stderr.txt       # 标准错误（如果有）
│       ├── command-1/
│       │   ├── command.txt      # codex exec 命令
│       │   ├── return-code.txt  # 返回码
│       │   ├── stdout.txt       # Codex CLI 的完整 JSON 输出
│       │   └── stderr.txt       # 标准错误（如果有）
│       └── codex.txt            # Codex CLI 的完整输出（JSON 格式）
└── flare-cra-taiwan_write_out_info.json
```

## 文件内容说明

### command-0/command.txt

创建 auth.json 的命令（Harbor 的第一个命令）：

```
cat >"$CODEX_HOME/auth.json" <<EOF
{
  "OPENAI_API_KEY": "${OPENAI_API_KEY}"
}
EOF
```

### command-1/command.txt

执行 Codex CLI 的命令：

```
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --model gpt-5-mini --json -- 'You are given a financial task instance in /tmp/pixiu_codex_xxx/tests/data/item.json...'
```

### command-1/stdout.txt 和 codex.txt

Codex CLI 的完整 JSON 输出，包含：

```json
{"type":"thread.started","thread_id":"..."}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"..."}}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"...","status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"...","aggregated_output":"...","exit_code":0,"status":"completed"}}
{"type":"turn.completed","usage":{"input_tokens":...,"output_tokens":...}}
```

## 查看 Agent 详细信息

### 1. 查看特定样本的 agent 日志

```bash
# 查看第一个样本的 agent 详细信息
ls -la results/harbor_test/agent_details/agent_*/

# 查看 codex.txt（完整的 Codex 交互）
cat results/harbor_test/agent_details/agent_*/codex.txt

# 查看执行的命令
cat results/harbor_test/agent_details/agent_*/command-1/command.txt

# 查看命令输出
cat results/harbor_test/agent_details/agent_*/command-1/stdout.txt
```

### 2. 使用 Python 脚本查看

```python
import json
from pathlib import Path

agent_dir = Path("results/harbor_test/agent_details/agent_taiwan000000")

# 读取 codex.txt
with open(agent_dir / "codex.txt") as f:
    for line in f:
        if line.strip():
            event = json.loads(line)
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    print(f"Agent message: {item.get('text')}")
                elif item.get("type") == "command_execution":
                    print(f"Command: {item.get('command')}")
                    print(f"Output: {item.get('aggregated_output')}")
                    print(f"Exit code: {item.get('exit_code')}")
```

### 3. 查看所有样本的 agent 交互

```bash
# 列出所有 agent 目录
find results/harbor_test/agent_details -type d -name "agent_*"

# 查看每个样本的最终答案（从 codex.txt 中提取）
for agent_dir in results/harbor_test/agent_details/agent_*/; do
    echo "=== $(basename $agent_dir) ==="
    # 提取最后的 agent_message
    grep -o '"type":"agent_message"[^}]*"text":"[^"]*"' "$agent_dir/codex.txt" | tail -1
done
```

## 与 Harbor 的对比

### Harbor 的 agent 目录结构

```
harbor/jobs/1228_logs/pixiu-taiwan-parity/pixiu-taiwan-taiwan000000__BdLkWrP/agent/
├── command-0/
│   ├── command.txt
│   ├── return-code.txt
│   └── stdout.txt
├── command-1/
│   ├── command.txt
│   ├── return-code.txt
│   └── stdout.txt
└── codex.txt
```

### PIXIU 的 agent 目录结构

```
results/harbor_test/agent_details/agent_<doc_id>/
├── command-0/
│   ├── command.txt
│   ├── return-code.txt
│   ├── stdout.txt
│   └── stderr.txt
├── command-1/
│   ├── command.txt
│   ├── return-code.txt
│   ├── stdout.txt
│   └── stderr.txt
└── codex.txt
```

**相同点**:
- ✅ 相同的目录结构
- ✅ 相同的文件命名
- ✅ 相同的文件内容格式

**差异**:
- PIXIU 额外保存了 `stderr.txt`（如果存在）
- PIXIU 的 agent 目录按 doc_id 组织（`agent_<doc_id>`）

## 清理临时目录

默认情况下，如果 `save_agent_details=True`，临时目录会被保留以便检查。要清理：

```bash
# 清理所有临时目录
rm -rf /tmp/pixiu_codex_*

# 或者只清理旧的（超过1小时）
find /tmp -name "pixiu_codex_*" -type d -mmin +60 -exec rm -rf {} +
```

## 注意事项

1. **磁盘空间**: 保存 agent 详细信息会占用更多磁盘空间
2. **临时目录**: 临时目录不会被自动清理（当 `save_agent_details=True` 时）
3. **并发执行**: 每个样本使用独立的临时目录，支持并发执行

## 示例：查看完整的 Agent 交互

```bash
# 查看某个样本的完整交互流程
agent_dir="results/harbor_test/agent_details/agent_taiwan000000"

echo "=== Command 0 (Auth) ==="
cat "$agent_dir/command-0/command.txt"
echo ""
cat "$agent_dir/command-0/stdout.txt"

echo ""
echo "=== Command 1 (Codex Exec) ==="
cat "$agent_dir/command-1/command.txt"
echo ""
echo "=== Codex Output ==="
cat "$agent_dir/codex.txt" | jq '.'  # 需要 jq 工具
```

## 总结

现在 PIXIU 的 Codex 可以像 Harbor 一样保存详细的 agent 执行信息，包括：
- ✅ 每个命令的详情
- ✅ Codex CLI 的完整 JSON 输出
- ✅ 命令的返回码和输出
- ✅ Agent 的完整交互流程

这些信息对于调试和分析 agent 行为非常有用！

