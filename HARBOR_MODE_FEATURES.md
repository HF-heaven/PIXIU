# PIXIU Codex Harbor 模式功能说明

## 功能概览

PIXIU 的 Codex 在 Harbor 模式下完全支持以下三个核心功能：

### ✅ 1. 读取 item.json

**实现位置**: `codexlm.py:146-178` (`_build_item_json`)

**功能**:
- 从 PIXIU 的 `doc` 对象构建 Harbor 格式的 `item.json`
- 包含任务的所有必要信息：query, choices, id, label_type 等
- 写入到临时目录的 `tests/data/item.json`

**代码流程**:
```python
# 在 _call_codex_cli_harbor_mode() 中
item_data = self._build_item_json(doc)
(data_dir / "item.json").write_text(
    json.dumps(item_data, ensure_ascii=False, indent=2)
)
```

**item.json 格式示例**:
```json
{
  "id": "taiwan000000",
  "query": "Predict whether the company will face bankruptcy...",
  "choices": ["no", "yes"],
  "dataset": "pixiu",
  "split": "test"
}
```

### ✅ 2. 调用模型 (Codex CLI)

**实现位置**: `codexlm.py:180-256` (`_call_codex_cli_harbor_mode`)

**功能**:
- 使用 Harbor 的 `instruction.md` 作为 prompt
- 调用 Codex CLI 执行任务
- Agent 读取 `item.json`，处理任务，写入 `answer.txt`

**代码流程**:
```python
# 1. 加载 Harbor instruction
instruction = self._load_harbor_instruction()

# 2. 修改路径为临时目录的绝对路径
instruction_modified = instruction.replace(
    "/tests/data/item.json",
    str(data_dir / "item.json")
).replace(
    "/app/answer.txt",
    str(app_dir / "answer.txt")
)

# 3. 执行 Codex CLI
cmd = [
    "codex", "exec",
    "--dangerously-bypass-approvals-and-sandbox",
    "--skip-git-repo-check",
    "--model", self.model,
    "--json",
    "--",
    instruction_modified
]

result = subprocess.run(
    cmd,
    cwd=str(app_dir),  # 工作目录设置为 app_dir
    capture_output=True,
    text=True,
    env=env,
    timeout=300,
)
```

**Instruction 内容**:
```
You are given a financial task instance in `/tests/data/item.json`.
- Read the JSON file at `/tests/data/item.json` to understand the query and available choices.
- Decide on the single best label according to the task description.
- Write your final answer as plain text to `/app/answer.txt`.
```

### ✅ 3. 根据 answer.txt 进行评估

**实现位置**: 
- `codexlm.py:274-296` (读取 answer.txt)
- `evaluator.py:413` (调用 process_results 评估)

**功能**:
- 从 `app/answer.txt` 读取 Agent 的答案
- 将答案传递给 `task.process_results()` 进行评估
- 计算 acc, f1, mcc 等指标

**代码流程**:
```python
# 1. 读取 answer.txt
answer_path = app_dir / "answer.txt"
if answer_path.exists():
    answer = answer_path.read_text().strip()
    return answer  # 返回给 evaluator

# 2. Evaluator 接收答案
resps = getattr(lm, reqtype)([req.args for req in reqs])
# resps[0] 包含从 answer.txt 读取的答案

# 3. 调用 task.process_results() 进行评估
metrics = task.process_results(doc, requests)
# 例如，对于分类任务：
# - 从 requests[0] 提取预测值（来自 answer.txt）
# - 与 doc["gold"] 比较
# - 计算 acc, f1, mcc 等指标
```

**评估流程**:
1. `task.process_results(doc, requests)` 接收模型输出
2. 提取预测值（从 answer.txt 读取的答案）
3. 与真实标签 `doc["gold"]` 比较
4. 计算各种指标（acc, f1, macro_f1, mcc 等）

## 完整工作流程

```
1. Evaluator 调用 CodexLM.greedy_until()
   ↓
2. CodexLM 创建临时目录结构
   /tmp/pixiu_codex_xxx/
   ├── app/
   │   └── answer.txt  (Agent 写入)
   └── tests/
       └── data/
           └── item.json  (从 doc 构建)
   ↓
3. 构建 item.json (读取功能)
   - 从 doc 对象提取信息
   - 写入 tests/data/item.json
   ↓
4. 调用 Codex CLI (调 model 功能)
   - 使用 Harbor instruction.md
   - Agent 读取 item.json
   - Agent 处理任务
   - Agent 写入 answer.txt
   ↓
5. 读取 answer.txt
   - 从 app/answer.txt 读取答案
   - 返回给 evaluator
   ↓
6. 评估 (eval 功能)
   - task.process_results() 处理答案
   - 计算 metrics (acc, f1, mcc 等)
   ↓
7. 清理临时目录
```

## 使用示例

### 启用 Harbor 模式

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

### 检查功能

生成的 `*_write_out_info.json` 文件包含：
- `prompt_0`: Harbor instruction（Agent 看到的）
- `logit_0`: 从 answer.txt 读取的答案
- `pred`: 处理后的预测值
- `gold`: 真实标签
- `acc`, `f1`, `mcc`: 评估指标

## 验证功能

### 1. 验证读取功能

检查临时目录中的 `item.json`:
```bash
# 启用调试模式
export CODEX_DEBUG=true

# 运行评估，查看调试输出
python src/eval.py --model codex --model_args "model=gpt-5-mini,harbor_mode=True" --tasks flare-cra-taiwan --limit 1
```

调试输出会显示：
```
[DEBUG] Harbor mode: item.json content:
{
  "id": "...",
  "query": "...",
  "choices": [...]
}
```

### 2. 验证调 model 功能

检查 Codex CLI 是否被正确调用：
- 查看调试输出中的 `instruction (with absolute paths)`
- 检查 Codex CLI 的返回码（应该是 0）
- 查看 stdout 输出

### 3. 验证 eval 功能

检查 `*_write_out_info.json`:
```bash
python view_intermediate_outputs.py results/harbor_test/flare-cra-taiwan_write_out_info.json --max 1
```

应该看到：
- `logit_0`: Agent 写入 answer.txt 的答案
- `pred`: 处理后的预测值
- `gold`: 真实标签
- `acc`: 准确率（0.0 或 1.0）

## 总结

✅ **读取 item.json**: 完全实现
- 从 doc 构建 item.json
- 写入到 tests/data/item.json
- Agent 可以读取

✅ **调 model**: 完全实现
- 使用 Harbor instruction.md
- 调用 Codex CLI
- Agent 处理任务并写入 answer.txt

✅ **根据 answer.txt eval**: 完全实现
- 从 answer.txt 读取答案
- 传递给 task.process_results()
- 计算评估指标

所有三个功能都已完整实现，PIXIU 的 Codex 在 Harbor 模式下可以完全按照 Harbor 的方式工作！

