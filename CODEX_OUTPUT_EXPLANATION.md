# Codex 输出格式说明

## 问题说明

你看到的 `"logit_0": "{\"type\": \"turn.completed\", \"usage\": {...}}"` 是 Codex CLI 输出的**元数据**，不是实际的 agent 输出。

## Codex CLI 输出格式

Codex CLI 会输出多行 JSON，包括：

1. **事件类型 JSON**（元数据）：
   ```json
   {"type":"thread.started","thread_id":"..."}
   {"type":"turn.started"}
   {"type":"turn.completed","usage":{"input_tokens":6473,"cached_input_tokens":6016,"output_tokens":11}}
   ```

2. **实际输出 JSON**（包含 agent 的回答）：
   ```json
   {"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"Yes"}}
   ```

## 实际输出位置

实际的 agent 输出在 `item.completed` 类型的 JSON 中的 `item.text` 字段。

例如：
```json
{
  "type": "item.completed",
  "item": {
    "id": "item_0",
    "type": "agent_message",
    "text": "Yes"  // ← 这里是实际输出
  }
}
```

## 已修复

我已经更新了 `src/codexlm.py` 中的解析逻辑，现在会：
1. 正确识别 `item.completed` 类型
2. 提取 `item.text` 字段作为实际输出
3. 忽略 `turn.completed` 等元数据事件

## 验证修复

重新运行评估，现在应该能看到实际的输出：

```bash
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"

# 重新运行测试
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 3 \
  --write_out \
  --output_base_path results/codex_outputs_fixed
```

现在 `logit_0` 应该包含实际的回答（如 "Yes" 或 "No"），而不是元数据 JSON。

## 查看修复后的输出

```bash
cat results/codex_outputs_fixed/flare_headlines_write_out_info.json | python -m json.tool
```

你应该能看到类似这样的输出：
```json
{
  "doc_id": 0,
  "prompt_0": "...",
  "logit_0": "Yes",  // ← 现在是实际输出，不是元数据
  "truth": "Yes"
}
```

