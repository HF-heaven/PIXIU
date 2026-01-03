# PIXIU Codex Agent 详细信息使用指南

## 功能说明

PIXIU 的 Codex 在 Harbor 模式下现在可以保存详细的 agent 执行信息，就像 Harbor 一样。这些信息包括：

- ✅ **command-0/**: 创建 auth.json 的命令详情
- ✅ **command-1/**: 执行 Codex CLI 的命令详情
- ✅ **codex.txt**: Codex CLI 的完整 JSON 输出（包含所有 agent 交互）

## 启用方法

### 方法 1: 使用 write_out 参数（自动启用）

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

当 `write_out=True` 时，会自动启用 agent 详细信息保存，保存到 `output_base_path/agent_details/` 目录。

### 方法 2: 手动设置

```python
from codexlm import CodexLM

lm = CodexLM(model="gpt-5-mini", harbor_mode=True)
lm._save_agent_details = True
lm._agent_log_base_dir = "/path/to/agent_logs"
```

## 文件结构

```
results/harbor_test/
├── agent_details/
│   └── agent_<doc_id>/
│       ├── command-0/
│       │   ├── command.txt      # 创建 auth.json 的命令
│       │   ├── return-code.txt # 返回码
│       │   ├── stdout.txt      # 标准输出（如果有）
│       │   └── stderr.txt      # 标准错误（如果有）
│       ├── command-1/
│       │   ├── command.txt      # codex exec 命令（完整）
│       │   ├── return-code.txt  # 返回码
│       │   ├── stdout.txt       # Codex CLI 的完整 JSON 输出
│       │   └── stderr.txt       # 标准错误（如果有）
│       └── codex.txt            # Codex CLI 的完整输出（JSON 格式）
└── flare-cra-taiwan_write_out_info.json
```

## 查看 Agent 详细信息

### 使用 view_agent_details.py 脚本

```bash
# 查看特定样本的 agent 详细信息
python view_agent_details.py results/harbor_test/agent_details/agent_taiwan000000
```

输出包括：
- Command 0 和 Command 1 的详情
- Codex 输出的事件时间线
- Agent 的完整交互流程
- Token 使用情况
- 最终答案提取

### 直接查看文件

```bash
# 查看 codex.txt（完整的 Codex 交互）
cat results/harbor_test/agent_details/agent_*/codex.txt

# 查看执行的命令
cat results/harbor_test/agent_details/agent_*/command-1/command.txt

# 查看命令输出
cat results/harbor_test/agent_details/agent_*/command-1/stdout.txt
```

### 使用 Python 解析

```python
import json
from pathlib import Path

agent_dir = Path("results/harbor_test/agent_details/agent_taiwan000000")

# 读取 codex.txt 并解析事件
with open(agent_dir / "codex.txt") as f:
    for line in f:
        if line.strip():
            event = json.loads(line)
            event_type = event.get("type")
            
            if event_type == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    print(f"Agent: {item.get('text')}")
                elif item.get("type") == "command_execution":
                    print(f"Command: {item.get('command')}")
                    print(f"Output: {item.get('aggregated_output')}")
```

## Codex 输出格式

`codex.txt` 包含 JSON 格式的事件流，每个事件一行：

```json
{"type":"thread.started","thread_id":"..."}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"..."}}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"...","status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"...","aggregated_output":"...","exit_code":0,"status":"completed"}}
{"type":"turn.completed","usage":{"input_tokens":...,"output_tokens":...}}
```

### 事件类型

- **thread.started**: 线程开始
- **turn.started**: 轮次开始
- **turn.completed**: 轮次完成（包含 token 使用）
- **item.completed**: 项目完成
  - `agent_message`: Agent 的消息
  - `command_execution`: 命令执行结果
  - `reasoning`: Agent 的推理过程
- **item.started**: 项目开始

## 与 Harbor 的对比

### Harbor 的 agent 目录

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

### PIXIU 的 agent 目录

```
results/harbor_test/agent_details/agent_<doc_id>/
├── command-0/
│   ├── command.txt
│   ├── return-code.txt
│   ├── stdout.txt
│   └── stderr.txt  # 额外保存
├── command-1/
│   ├── command.txt
│   ├── return-code.txt
│   ├── stdout.txt
│   └── stderr.txt  # 额外保存
└── codex.txt
```

**相同点**:
- ✅ 相同的目录结构
- ✅ 相同的文件命名
- ✅ 相同的文件内容格式

**差异**:
- PIXIU 额外保存了 `stderr.txt`（如果存在）
- PIXIU 的 agent 目录按 doc_id 组织（`agent_<doc_id>`）

## 实际使用示例

### 运行评估并保存 agent 详细信息

```bash
cd /home/hefan/PIXIU
python src/eval.py \
    --model codex \
    --model_args "model=gpt-5-mini,harbor_mode=True" \
    --tasks flare-cra-taiwan \
    --limit 3 \
    --write_out \
    --output_base_path results/agent_test
```

### 查看所有样本的 agent 详细信息

```bash
# 列出所有 agent 目录
find results/agent_test/agent_details -type d -name "agent_*"

# 查看每个样本的 agent 交互
for agent_dir in results/agent_test/agent_details/agent_*/; do
    echo "=== $(basename $agent_dir) ==="
    python view_agent_details.py "$agent_dir"
    echo ""
done
```

### 提取关键信息

```bash
# 提取所有样本的最终答案
for agent_dir in results/agent_test/agent_details/agent_*/; do
    doc_id=$(basename $agent_dir | sed 's/agent_//')
    # 从 codex.txt 提取最后的 agent_message
    final_msg=$(grep -o '"type":"agent_message"[^}]*"text":"[^"]*"' "$agent_dir/codex.txt" | tail -1 | grep -o '"text":"[^"]*"' | cut -d'"' -f4)
    echo "$doc_id: $final_msg"
done
```

## 总结

现在 PIXIU 的 Codex 可以像 Harbor 一样保存详细的 agent 执行信息：

✅ **读取 item.json**: 从 doc 构建并保存到 `tests/data/item.json`
✅ **调 model**: 调用 Codex CLI，保存完整的命令和输出
✅ **根据 answer.txt eval**: 从 `app/answer.txt` 读取答案并评估
✅ **保存 agent 详细信息**: 保存所有命令、输出和交互流程

所有功能都已完整实现！

