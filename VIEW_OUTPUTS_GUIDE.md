# 查看 PIXIU 中间输出指南

## 概述

PIXIU 支持输出每个样本的详细信息，包括：
- **模型输入 (Prompt)**: 发送给模型的完整 prompt
- **模型输出 (Raw)**: 模型的原始输出
- **预测值 (Pred)**: 处理后的预测值
- **真实值 (Gold)**: 真实标签
- **Metrics**: 各种评估指标（acc, f1, 等）

## 启用详细输出

### 方法 1: 使用 eval.py

```bash
cd /home/hefan/PIXIU
python src/eval.py \
    --model codex \
    --model_args "model=gpt-4o,harbor_mode=True" \
    --tasks en-fpb \
    --limit 5 \
    --write_out \
    --output_base_path results/my_experiment
```

### 方法 2: 使用 Python API

```python
from evaluator import simple_evaluate

results = simple_evaluate(
    model="codex",
    model_args="model=gpt-4o,harbor_mode=True",
    tasks=["en-fpb"],
    limit=5,
    write_out=True,
    output_base_path="results/my_experiment"
)
```

## 输出文件格式

运行后会在 `output_base_path` 目录下生成 `{task_name}_write_out_info.json` 文件，格式如下：

```json
{
  "0": {
    "doc_id": 0,
    "prompt_0": "完整的 prompt 文本...",
    "logit_0": "模型的原始输出...",
    "pred": "处理后的预测值",
    "gold": "真实标签",
    "truth": "真实标签（备用字段）",
    "acc": "1.0",
    "f1": "1.0",
    "missing": "0"
  },
  "1": {
    ...
  }
}
```

## 查看输出

### 使用 view_intermediate_outputs.py 脚本

#### 1. 查看所有样本

```bash
python view_intermediate_outputs.py results/my_experiment/en-fpb_write_out_info.json --all
```

#### 2. 查看前 N 个样本

```bash
python view_intermediate_outputs.py results/my_experiment/en-fpb_write_out_info.json --max 5
```

#### 3. 查看特定样本

```bash
python view_intermediate_outputs.py results/my_experiment/en-fpb_write_out_info.json --samples 0 1 2
```

#### 4. 查看摘要统计

```bash
python view_intermediate_outputs.py results/my_experiment/en-fpb_write_out_info.json --summary
```

### 输出示例

```
================================================================================
Sample ID: 0
================================================================================

[Model Input / Prompt]:
--------------------------------------------------------------------------------
You are given a financial task instance in /tmp/pixiu_codex_xxx/tests/data/item.json.

**Important**: You are currently in the /app directory...
- Read the JSON file at /tmp/pixiu_codex_xxx/tests/data/item.json...
- Write your final answer as plain text to /tmp/pixiu_codex_xxx/app/answer.txt.

[Model Output (Raw)]:
--------------------------------------------------------------------------------
Positive

[Prediction (Processed)]:
--------------------------------------------------------------------------------
positive

[Gold Label]:
--------------------------------------------------------------------------------
positive

[Metrics]:
--------------------------------------------------------------------------------
  acc: 1.0
  f1: 1.0
  missing: 0
```

## 直接查看 JSON 文件

你也可以直接查看 JSON 文件：

```bash
# 使用 jq (如果已安装)
cat results/my_experiment/en-fpb_write_out_info.json | jq '.["0"]'

# 或使用 Python
python3 << 'EOF'
import json
with open('results/my_experiment/en-fpb_write_out_info.json') as f:
    data = json.load(f)
    sample = data['0']
    print("Prompt:", sample['prompt_0'][:200] + "...")
    print("Output:", sample['logit_0'])
    print("Pred:", sample.get('pred', 'N/A'))
    print("Gold:", sample.get('gold', sample.get('truth', 'N/A')))
EOF
```

## 字段说明

- **doc_id**: 文档 ID
- **prompt_0**: 发送给模型的完整 prompt（包含 instruction、few-shot examples、当前问题）
- **logit_0**: 模型的原始输出（未处理）
- **pred**: 处理后的预测值（从 logit_0 中提取，匹配 choices）
- **gold/truth**: 真实标签
- **acc**: 准确率（1.0 = 正确，0.0 = 错误）
- **missing**: 是否缺失预测（1 = 缺失，0 = 不缺失）
- **f1, macro_f1, mcc**: 其他评估指标

## 注意事项

1. **Harbor 模式**: 如果使用 `harbor_mode=True`，prompt 会是 Harbor 的 instruction.md 模板
2. **文件路径**: 输出文件保存在 `output_base_path` 目录下
3. **文件命名**: 文件名为 `{task_name}_write_out_info.json`
4. **内存使用**: 如果样本很多，JSON 文件可能很大，建议使用 `--max` 限制查看数量

## 故障排除

### 问题 1: 找不到 pred 字段

如果 JSON 文件中没有 `pred` 字段，可能是：
- 使用了旧版本的代码（需要更新 evaluator.py）
- 任务类型不支持 pred 提取

**解决方案**: 确保使用最新代码，pred 会从 `process_results` 的 metrics 中提取。

### 问题 2: 输出文件为空

检查：
- `write_out=True` 是否设置
- `output_base_path` 目录是否存在且有写权限
- 是否有错误信息

### 问题 3: prompt_0 显示 Harbor 路径

这是正常的。如果使用 `harbor_mode=True`，prompt 会包含 Harbor instruction 和临时文件路径。

## 高级用法

### 批量查看多个任务

```bash
for task in en-fpb flare-cfa flare-headlines; do
    echo "=== $task ==="
    python view_intermediate_outputs.py results/my_experiment/${task}_write_out_info.json --summary
done
```

### 提取所有错误的样本

```python
import json

with open('results/my_experiment/en-fpb_write_out_info.json') as f:
    data = json.load(f)
    
errors = []
for doc_id, sample in data.items():
    if sample.get('acc') == '0.0':
        errors.append({
            'doc_id': doc_id,
            'pred': sample.get('pred'),
            'gold': sample.get('gold', sample.get('truth')),
            'output': sample.get('logit_0', '')[:100]
        })

print(f"Found {len(errors)} errors")
for err in errors[:5]:  # 显示前5个
    print(err)
```

