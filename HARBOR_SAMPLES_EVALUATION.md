# Harbor 相同样本评估结果

## 概述

在原始 PIXIU benchmark 中运行了与 Harbor `datasets/pixiu/en-fpb` 相同的 15 个样本。

## 样本列表

从 Harbor 提取的样本 ID：
- fpb3891, fpb3901, fpb3982, fpb3993, fpb4000
- fpb4013, fpb4040, fpb4199, fpb4247, fpb4300
- fpb4586, fpb4611, fpb4687, fpb4744, fpb4827

## 评估结果

### Codex (gpt-5-mini)

**结果文件**: `results/harbor_samples_en-fpb_codex_gpt-5-mini/results.json`

**指标**:
- Accuracy: 0.8667 (86.67%)
- Missing: 0.0
- F1 (Weighted): 0.8667
- Macro F1: 0.8968
- MCC: 0.7794

### GPT-5-mini (ChatLM)

**状态**: 评估失败

**错误**: API 返回 400 Bad Request，可能是模型名称 `gpt-5-mini` 无效。

**建议**: 
- 如果 `gpt-5-mini` 是有效的 OpenAI 模型，请检查 API key 和模型名称
- 或者使用其他有效的模型名称（如 `gpt-4o-mini`, `gpt-4o` 等）

## 使用方法

### 运行 Codex 评估

```bash
cd /home/hefan/PIXIU
bash run_harbor_samples.sh en-fpb codex gpt-5-mini
```

### 运行 ChatLM 评估

```bash
cd /home/hefan/PIXIU
export OPENAI_API_SECRET_KEY="$OPENAI_API_KEY"
bash run_harbor_samples.sh en-fpb "gpt-4o-mini" ""
```

## 脚本说明

- `run_specific_samples.py`: Python 脚本，从 Harbor 提取样本 ID 并运行评估
- `run_harbor_samples.sh`: Shell 脚本，封装了运行评估的命令
- `run_both_models.sh`: 运行两个模型的评估（需要修复 gpt-5-mini 的问题）

