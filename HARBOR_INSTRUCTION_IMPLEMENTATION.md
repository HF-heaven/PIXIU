# Harbor Instruction 实现说明

## 概述

PIXIU 的 Harbor 模式完全按照 Harbor 的 `instruction.md` 工作，确保在相同的 agent 和 model 下，模型输出完全一致。

## Harbor Instruction 格式

**位置**: `/home/hefan/harbor/adapters/pixiu/template/instruction.md`

```
You are given a financial task instance in `/tests/data/item.json`.

**Important**: You are currently in the `/app` directory, but the input file is located at the absolute path `/tests/data/item.json` (note the leading slash). Do not use relative paths like `tests/data/item.json`.

- Read the JSON file at `/tests/data/item.json` to understand the query and available choices.
- Decide on the single best label according to the task description.
- Write your final answer as plain text to `/app/answer.txt`.

Your answer must exactly match one of the allowed labels.
```

## PIXIU 实现

### 1. 目录结构

创建临时目录结构，模拟 Harbor 的容器环境：

```
/tmp/pixiu_codex_<uuid>/
├── app/              # 工作目录（agent 在此执行）
│   └── answer.txt    # Agent 写入的答案
└── tests/
    └── data/
        └── item.json  # 任务数据（从 doc 构建）
```

**代码位置**: `codexlm.py:180-188`

### 2. 构建 item.json

从 PIXIU 的 `doc` 对象构建 Harbor 格式的 `item.json`：

**代码位置**: `codexlm.py:146-178` (`_build_item_json`)

包含字段：
- `id`: doc["id"]
- `query`: doc["query"] 或 doc["text"]
- `choices`: doc["choices"] (分类任务)
- `dataset`: 数据集名称
- `split`: "test" 或 "validation"
- 其他任务特定字段（tokens, labels, relations 等）

### 3. 加载 Instruction

从 Harbor 模板目录读取 `instruction.md`：

**代码位置**: `codexlm.py:126-144` (`_load_harbor_instruction`)

```python
harbor_template_path = Path("/home/hefan/harbor/adapters/pixiu/template/instruction.md")
instruction = harbor_template_path.read_text()
```

### 4. 路径处理

由于 Harbor instruction 使用绝对路径（`/tests/data/item.json` 和 `/app/answer.txt`），在本地环境中需要将这些路径替换为临时目录的绝对路径：

**代码位置**: `codexlm.py:213-219`

```python
instruction_modified = instruction.replace(
    "/tests/data/item.json",
    str(data_dir / "item.json")  # 例如: /tmp/pixiu_codex_xxx/tests/data/item.json
).replace(
    "/app/answer.txt",
    str(app_dir / "answer.txt")  # 例如: /tmp/pixiu_codex_xxx/app/answer.txt
)
```

这样修改后的 instruction 会变成：
```
You are given a financial task instance in `/tmp/pixiu_codex_xxx/tests/data/item.json`.

**Important**: You are currently in the `/tmp/pixiu_codex_xxx/app` directory, but the input file is located at the absolute path `/tmp/pixiu_codex_xxx/tests/data/item.json`...

- Read the JSON file at `/tmp/pixiu_codex_xxx/tests/data/item.json`...
- Write your final answer as plain text to `/tmp/pixiu_codex_xxx/app/answer.txt`.
```

### 5. 执行 Codex CLI

**代码位置**: `codexlm.py:221-248`

```python
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
    cwd=str(app_dir),  # 工作目录设置为 app_dir（与 Harbor 一致）
    capture_output=True,
    text=True,
    env=env,
    timeout=300,
)
```

### 6. 读取答案

**代码位置**: `codexlm.py:266-296`

```python
answer_path = app_dir / "answer.txt"
if answer_path.exists():
    answer = answer_path.read_text().strip()
    return answer
else:
    # Fallback: 从 stdout 解析
    return self._parse_codex_output_from_stdout(result.stdout)
```

## 与 Harbor 的一致性

### 相同点

1. **相同的 Instruction**: 使用 Harbor 的 `instruction.md` 模板
2. **相同的文件结构**: `tests/data/item.json` 和 `app/answer.txt`
3. **相同的工作目录**: Codex 在 `app/` 目录中执行
4. **相同的执行方式**: 使用相同的 Codex CLI 命令和参数
5. **相同的输出读取**: 从 `app/answer.txt` 读取答案

### 差异

1. **路径格式**: 
   - Harbor: 容器内的绝对路径 `/tests/data/item.json`
   - PIXIU: 临时目录的绝对路径 `/tmp/pixiu_codex_xxx/tests/data/item.json`
   
   但功能等价，因为：
   - 都使用绝对路径
   - 都指向正确的文件位置
   - Agent 看到的是相同的指令结构

2. **环境**:
   - Harbor: Docker 容器环境
   - PIXIU: 本地临时目录

   但这不影响 Agent 的行为，因为：
   - 文件结构相同
   - 工作目录相同
   - Instruction 内容相同（除了路径值）

## 验证一致性

要验证 PIXIU 和 Harbor 的输出一致性：

1. **使用相同的模型**: `model=gpt-5-mini`
2. **使用相同的样本**: 确保 doc 内容一致
3. **启用 Harbor 模式**: `harbor_mode=True`
4. **比较输出**: 检查 `answer.txt` 的内容是否一致

## 使用示例

```bash
cd /home/hefan/PIXIU
python src/eval.py \
    --model codex \
    --model_args "model=gpt-5-mini,harbor_mode=True" \
    --tasks flare-cra-taiwan \
    --limit 5 \
    --write_out \
    --output_base_path results/harbor_mode_test
```

## 调试

启用调试模式查看详细信息：

```bash
export CODEX_DEBUG=true
```

调试信息包括：
- 临时目录路径
- item.json 内容
- 修改后的 instruction
- Codex CLI 的返回码和输出
- answer.txt 的读取结果

## 总结

PIXIU 的 Harbor 模式实现：
- ✅ 使用 Harbor 的原始 `instruction.md`
- ✅ 创建相同的目录结构
- ✅ 构建相同格式的 `item.json`
- ✅ 在相同的工作目录执行
- ✅ 从相同的位置读取答案

唯一的技术差异是路径值（容器路径 vs 临时目录路径），但这不影响 Agent 的行为和输出结果。

