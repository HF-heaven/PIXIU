# PIXIU Codex Harbor Mode

## 概述

PIXIU 的 CodexLM 现在支持 Harbor 兼容模式（`harbor_mode=True`），确保在相同的 agent 和 model 下，模型输出与 Harbor 完全一致。

## 实现原理

Harbor 模式完全模拟 Harbor 的执行方式：

1. **相同的 Instruction**: 使用 Harbor 的 `instruction.md` 模板
2. **相同的文件结构**: 创建临时目录，包含 `tests/data/item.json` 和 `app/answer.txt`
3. **相同的执行环境**: Codex 在 `app/` 目录中执行，读取 `tests/data/item.json`，写入 `app/answer.txt`
4. **相同的输出读取**: 从 `app/answer.txt` 读取答案，而不是从 stdout 解析

## 使用方法

### 1. 通过 model_args 启用

```python
from evaluator import simple_evaluate

results = simple_evaluate(
    model="codex",
    model_args="model=gpt-4o,harbor_mode=True",  # 启用 Harbor 模式
    tasks=["en-fpb"],
    limit=5
)
```

### 2. 直接创建 CodexLM 实例

```python
from codexlm import CodexLM

lm = CodexLM(model="gpt-4o", harbor_mode=True)
```

## 工作流程

### Harbor 模式执行流程

```
1. 创建临时目录结构:
   /tmp/pixiu_codex_<uuid>/
   ├── app/              # 工作目录
   │   └── answer.txt    # Agent 写入的答案
   └── tests/
       └── data/
           └── item.json  # 任务数据

2. 构建 item.json (从 doc 对象):
   {
     "id": "...",
     "query": "...",
     "choices": [...],
     "dataset": "...",
     "split": "test"
   }

3. 读取 Harbor instruction.md:
   "You are given a financial task instance in `/tests/data/item.json`.
    ...
    - Write your final answer as plain text to `/app/answer.txt`."

4. 执行 Codex CLI:
   - 工作目录: app/
   - Instruction: 使用 Harbor 模板（路径已调整为绝对路径）

5. 读取答案:
   - 从 app/answer.txt 读取
   - 如果不存在，fallback 到 stdout 解析

6. 清理临时目录
```

## 关键实现细节

### 1. 路径处理

Harbor instruction 使用绝对路径 `/tests/data/item.json` 和 `/app/answer.txt`。在本地环境中，这些路径会被替换为临时目录的绝对路径：

```python
instruction_modified = instruction.replace(
    "/tests/data/item.json",
    str(data_dir / "item.json")  # 例如: /tmp/pixiu_codex_xxx/tests/data/item.json
).replace(
    "/app/answer.txt",
    str(app_dir / "answer.txt")  # 例如: /tmp/pixiu_codex_xxx/app/answer.txt
)
```

### 2. Doc 信息传递

在 `evaluator.py` 中，每个 request 对应的 doc 信息通过 `lm._request_docs` 列表传递：

```python
if reqtype == "greedy_until" and hasattr(lm, 'harbor_mode') and lm.harbor_mode:
    request_docs = [doc for req, (i, task_name, doc, ...) in filtered_reqs]
    lm._request_docs = request_docs
```

### 3. item.json 格式

`_build_item_json()` 方法将 PIXIU 的 doc 对象转换为 Harbor 格式的 item.json，包含：
- `id`: doc["id"]
- `query`: doc["query"] 或 doc["text"]
- `choices`: doc["choices"] (分类任务)
- `tokens`, `labels`: (序列标注任务)
- `relations`: (关系抽取任务)
- `expected_score`, `score_range`: (回归任务)
- `label_type`: (如果有)
- `dataset`, `split`: 数据集信息

## 调试

启用调试模式：

```bash
export CODEX_DEBUG=true
```

或者在代码中：

```python
lm = CodexLM(model="gpt-4o", harbor_mode=True)
lm._debug_mode = True
```

调试信息包括：
- 临时目录路径
- item.json 内容
- 修改后的 instruction
- Codex CLI 的返回码和输出
- answer.txt 读取结果

## 兼容性

- **向后兼容**: `harbor_mode=False` (默认) 时，行为与原来完全一致
- **接口兼容**: `greedy_until()` 接口不变，仍然返回字符串列表
- **Fallback**: 如果 `answer.txt` 不存在，会 fallback 到原有的 stdout 解析逻辑

## 注意事项

1. **临时目录**: 每次请求都会创建临时目录，使用后自动清理
2. **并发安全**: 使用 UUID 确保临时目录名称唯一
3. **路径权限**: 确保 `/tmp` 目录可写
4. **Codex CLI**: 需要安装并配置 Codex CLI (`npm install -g @openai/codex@latest`)

## 测试

运行测试：

```bash
cd /home/hefan/PIXIU
python src/eval.py \
    --model codex \
    --model_args "model=gpt-4o,harbor_mode=True" \
    --tasks en-fpb \
    --limit 1 \
    --num_fewshot 0
```

## 文件修改清单

1. **`/home/hefan/PIXIU/src/codexlm.py`**:
   - 添加 `harbor_mode` 参数
   - 实现 `_load_harbor_instruction()`
   - 实现 `_build_item_json()`
   - 实现 `_call_codex_cli_harbor_mode()`
   - 修改 `greedy_until()` 支持 Harbor 模式

2. **`/home/hefan/PIXIU/src/evaluator.py`**:
   - 解析 `model_args` 中的 `harbor_mode` 参数
   - 在调用 `greedy_until()` 前设置 `lm._request_docs`

## 验证一致性

要验证 Harbor 模式和原始模式的一致性：

1. 运行相同的任务和样本
2. 比较输出结果
3. 检查 `answer.txt` 的内容
4. 验证 metrics 是否一致

