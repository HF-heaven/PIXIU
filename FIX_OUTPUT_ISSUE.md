# 修复 Codex 输出提取问题

## 问题

你看到的 `"logit_0": "{\"type\": \"turn.completed\", \"usage\": {...}}"` 是元数据，不是实际的 agent 输出。

## 解决方案

代码已经修复，但可能需要：

### 1. 清除 Python 缓存

```bash
cd /home/hefan/PIXIU
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
```

### 2. 重新运行评估（不要使用缓存）

```bash
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"

# 使用 --no_cache 确保不使用缓存的旧结果
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 3 \
  --no_cache \
  --write_out \
  --output_base_path results/codex_outputs_new
```

### 3. 验证修复

运行测试脚本验证输出提取：

```bash
python test_codex_output_extraction.py
```

应该看到：
```
✓ SUCCESS: Extracted actual output, not metadata!
```

### 4. 如果仍然有问题

检查 Codex CLI 的实际输出格式：

```bash
codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  --model gpt-4o \
  --json \
  -- "Your test prompt here" | cat
```

查看是否有 `item.completed` 类型的 JSON。

## 代码逻辑

修复后的代码会：
1. 优先查找 `item.completed` 类型中的 `item.text` 字段
2. 如果找不到，尝试其他可能的字段（`text`, `content`, `message`, `output`）
3. 如果都找不到，返回原始输出并打印警告

## 验证

运行以下命令验证：

```bash
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"
python test_codex_output_extraction.py
```

如果看到 "✓ SUCCESS"，说明修复成功。然后重新运行评估。

