# PIXIU 中 Codex 的工作流程

## 概述

PIXIU 使用 Codex CLI 作为语言模型来执行金融任务。本文档说明 Codex 在 PIXIU 中的工作方式和配置。

## 工作流程

### 1. 初始化 CodexLM

**位置**: `/home/hefan/PIXIU/src/evaluator.py:78-94`

```python
if model == "codex":
    # 解析 model_args 获取模型名称和 harbor_mode
    args_dict = {}
    if model_args:
        for arg in model_args.split(","):
            if "=" in arg:
                k, v = arg.split("=", 1)
                args_dict[k.strip()] = v.strip()
    
    codex_model = args_dict.get("model", "gpt-4o")  # 默认模型
    harbor_mode = args_dict.get("harbor_mode", False)  # Harbor 模式开关
    lm = CodexLM(model=codex_model, harbor_mode=harbor_mode)
```

**CodexLM 类**: `/home/hefan/PIXIU/src/codexlm.py`

- 检查 `OPENAI_API_KEY` 环境变量
- 验证 Codex CLI 是否安装和可用
- 初始化模型参数

### 2. 构建 Prompt

**流程**: `evaluator.py` → `task.fewshot_context()` → `MODEL_PROMPT_MAP` → `task.construct_requests()`

#### 2.1 Task 定义

每个任务（如 `taiwan`）继承自 `Classification` 类，定义在 `/home/hefan/PIXIU/src/tasks/flare.py`:

```python
class taiwan(Classification):
    DATASET_PATH = "TheFinAI/cra-taiwan"
```

#### 2.2 doc_to_text() - 提取问题文本

**位置**: `flare.py:74-76`

```python
def doc_to_text(self, doc):
    return doc["query"]  # 返回任务的问题文本
```

例如，对于 `taiwan` 任务，`doc["query"]` 可能是：
```
"Predict whether the company will face bankruptcy based on the financial profile attributes provided in the following text. Respond with only 'no' or 'yes', and do not provide any additional information. \nFor instance, 'The client has attributes:  ROA(C) before interest and depreciation before interest: 0.499, ..., Net Income Flag: 1.000,  Equity to Liability: 0.044.' should be classified as 'no'. \nText: 'The client has attributes: Bankrupt?: 0.371, ...' \nAnswer:"
```

#### 2.3 fewshot_context() - 构建完整 Context

**位置**: `lm_eval/base.py` (继承的方法)

构建包含以下内容的完整 prompt：
- **Description**: 任务描述（如果有）
- **Few-shot examples**: 示例（如果 `num_fewshot > 0`）
- **Current question**: `doc_to_text(doc)` 的结果

#### 2.4 MODEL_PROMPT_MAP - 应用 Prompt 模板

**位置**: `/home/hefan/PIXIU/src/model_prompt.py`

```python
MODEL_PROMPT_MAP = {
    "no_prompt": no_prompt,      # 直接返回 ctx，不添加额外格式
    "finma_prompt": finma_prompt  # 添加 "Human: ... Assistant:" 格式
}
```

**应用位置**: `evaluator.py:277`

```python
ctx = MODEL_PROMPT_MAP[model_prompt](ctx)
```

默认使用 `"no_prompt"`，即直接使用 `fewshot_context` 构建的 prompt。

#### 2.5 construct_requests() - 创建请求

**位置**: `flare.py:57-69`

```python
def construct_requests(self, doc, ctx):
    cont_request = rf.greedy_until(ctx, {"until": None})
    return cont_request
```

创建一个 `greedy_until` 请求，使用完整的 `ctx` 作为 prompt。

### 3. 执行 Codex CLI

**位置**: `codexlm.py:342-487` (`_call_codex_cli` 方法)

#### 3.1 非 Harbor 模式（默认）

```python
def _call_codex_cli(self, instruction: str) -> str:
    cmd = [
        "codex", "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--skip-git-repo-check",
        "--model", self.model,  # 例如 "gpt-5-mini"
        "--json",
        "--",
        instruction  # 完整的 prompt
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # 解析 JSON 输出
    # Codex CLI 输出格式:
    # {"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"actual output"}}
    # {"type":"turn.completed","usage":{"input_tokens":...,"output_tokens":...}}
    
    # 提取 item.completed 中的 text 字段
    return parsed_output
```

#### 3.2 Harbor 模式（如果启用）

**位置**: `codexlm.py:189-287` (`_call_codex_cli_harbor_mode`)

1. 创建临时目录结构：
   ```
   /tmp/pixiu_codex_<uuid>/
   ├── app/              # 工作目录
   │   └── answer.txt    # Agent 写入的答案
   └── tests/
       └── data/
           └── item.json  # 任务数据
   ```

2. 构建 `item.json`（从 doc 对象）

3. 使用 Harbor 的 `instruction.md` 模板：
   ```
   You are given a financial task instance in /tests/data/item.json.
   - Read the JSON file at /tests/data/item.json...
   - Write your final answer as plain text to /app/answer.txt.
   ```

4. 执行 Codex CLI（工作目录设置为 `app/`）

5. 从 `answer.txt` 读取答案

### 4. 处理结果

**位置**: `evaluator.py:355-390`

```python
# 调用 greedy_until
resps = getattr(lm, reqtype)([req.args for req in reqs])

# 存储到 write_out_info
if write_out:
    write_out_info[task_name][doc_id][f"logit_{i}"] = resp
    write_out_info[task_name][doc_id]["truth"] = task.doc_to_target(doc)
```

**位置**: `evaluator.py:413` (`task.process_results`)

```python
metrics = task.process_results(doc, requests)
# 例如，对于分类任务：
# - 从 requests[0] 提取预测值
# - 与 doc["gold"] 比较
# - 计算 acc, f1, mcc 等指标
```

## 关键文件位置

### 代码文件

1. **CodexLM 实现**: `/home/hefan/PIXIU/src/codexlm.py`
   - `__init__()`: 初始化，检查 Codex CLI
   - `_call_codex_cli()`: 非 Harbor 模式执行
   - `_call_codex_cli_harbor_mode()`: Harbor 模式执行
   - `greedy_until()`: 主要接口，处理请求列表

2. **Evaluator**: `/home/hefan/PIXIU/src/evaluator.py`
   - `simple_evaluate()`: 主入口
   - 创建 CodexLM 实例
   - 构建 prompt 并调用模型
   - 处理结果

3. **Task 定义**: `/home/hefan/PIXIU/src/tasks/flare.py`
   - `doc_to_text()`: 提取问题文本
   - `construct_requests()`: 创建请求
   - `process_results()`: 处理模型输出

4. **Prompt 模板**: `/home/hefan/PIXIU/src/model_prompt.py`
   - `MODEL_PROMPT_MAP`: 定义不同的 prompt 格式

### Instruction 位置

#### 非 Harbor 模式

Instruction 由以下部分构建：
1. **Task description** (如果有 `description_dict`)
2. **Few-shot examples** (如果 `num_fewshot > 0`)
3. **Current question**: `task.doc_to_text(doc)`

**示例** (taiwan 任务):
```
Predict whether the company will face bankruptcy based on the financial profile attributes provided in the following text. Respond with only 'no' or 'yes', and do not provide any additional information. 
For instance, 'The client has attributes:  ROA(C) before interest and depreciation before interest: 0.499, ..., Net Income Flag: 1.000,  Equity to Liability: 0.044.' should be classified as 'no'. 
Text: 'The client has attributes: Bankrupt?: 0.371, ...' 
Answer:
```

#### Harbor 模式

Instruction 来自: `/home/hefan/harbor/adapters/pixiu/template/instruction.md`

```
You are given a financial task instance in `/tests/data/item.json`.

**Important**: You are currently in the `/app` directory, but the input file is located at the absolute path `/tests/data/item.json` (note the leading slash). Do not use relative paths like `tests/data/item.json`.

- Read the JSON file at `/tests/data/item.json` to understand the query and available choices.
- Decide on the single best label according to the task description.
- Write your final answer as plain text to `/app/answer.txt`.

Your answer must exactly match one of the allowed labels.
```

## 使用示例

### 命令行

```bash
python src/eval.py \
    --model codex \
    --model_args "model=gpt-5-mini" \
    --tasks flare-cra-taiwan \
    --limit 5 \
    --write_out \
    --output_base_path results/test
```

### Python API

```python
from evaluator import simple_evaluate

results = simple_evaluate(
    model="codex",
    model_args="model=gpt-5-mini",
    tasks=["flare-cra-taiwan"],
    limit=5,
    write_out=True,
    output_base_path="results/test"
)
```

### 启用 Harbor 模式

```bash
python src/eval.py \
    --model codex \
    --model_args "model=gpt-5-mini,harbor_mode=True" \
    --tasks flare-cra-taiwan \
    --limit 5
```

## 调试

### 启用调试模式

```bash
export CODEX_DEBUG=true
```

### 查看中间输出

生成的 `*_write_out_info.json` 文件包含：
- `prompt_0`: 完整的 prompt（发送给 Codex 的）
- `logit_0`: 模型的原始输出
- `pred`: 处理后的预测值
- `gold`: 真实标签

使用 `view_intermediate_outputs.py` 查看：
```bash
python view_intermediate_outputs.py results/test/flare-cra-taiwan_write_out_info.json --max 5
```

## 常见问题

### 1. 为什么 logit_0 是空的？

可能原因：
- Codex CLI 执行失败（检查错误日志）
- 输出解析失败（检查 Codex CLI 输出格式）
- 异常被捕获但只返回空字符串

**解决**: 启用 `CODEX_DEBUG=true` 查看详细日志

### 2. 如何修改 prompt 格式？

修改 `/home/hefan/PIXIU/src/model_prompt.py` 中的 `MODEL_PROMPT_MAP`，或修改任务的 `doc_to_text()` 方法。

### 3. Harbor 模式 vs 非 Harbor 模式的区别？

- **非 Harbor 模式**: 直接使用 PIXIU 的 prompt，从 stdout 解析输出
- **Harbor 模式**: 使用 Harbor 的 instruction.md，从 answer.txt 读取输出

## 总结

PIXIU 中 Codex 的工作流程：
1. **初始化**: 创建 CodexLM 实例，检查环境
2. **构建 Prompt**: Task → fewshot_context → MODEL_PROMPT_MAP → construct_requests
3. **执行**: 调用 Codex CLI，传入完整 prompt
4. **解析**: 从 JSON 输出中提取文本（或从 answer.txt 读取）
5. **处理**: task.process_results() 计算指标

Instruction 的位置取决于模式：
- **非 Harbor**: 由 Task 的 `doc_to_text()` 和 `fewshot_context()` 构建
- **Harbor**: 使用 `/home/hefan/harbor/adapters/pixiu/template/instruction.md`

