# 自动化评估流程总结

## ✅ 已完成的功能

### 1. 自动化脚本

- **`auto_eval_harbor_task.py`**: 主评估脚本
  - 自动从 Harbor 提取样本 ID
  - 自动映射任务名（Harbor → PIXIU）
  - 创建过滤任务（只包含 Harbor 中的样本）
  - 运行评估并保存结果

- **`auto_eval.sh`**: Shell 包装脚本
  - 自动设置环境变量
  - 激活 conda 环境
  - 设置 PYTHONPATH
  - 调用 Python 脚本

### 2. 任务名映射

支持 29+ 个 Harbor 任务到 PIXIU 任务的自动映射，包括：
- Classification: en-fpb, flare-headlines, flare-fiqasa, etc.
- QA: flare-finqa, flare-tatqa
- NER: flare-ner, flare-fnxl
- Summarization: flare-ectsum, flare-edtsum
- Regression: flare-tsa
- Relation Extraction: flare-finred, flare-cd
- 等等...

### 3. 样本提取

自动从 Harbor 任务目录中提取样本 ID，支持多种命名模式：
- `pixiu-<task_name>-<sample_id>/`
- `pixiu-<short_name>-<sample_id>/` (例如: pixiu-fpb-fpb3891)

## 📝 使用方法

### 最简单的方式

```bash
cd /home/hefan/PIXIU
bash auto_eval.sh en-fpb
```

### 完整参数

```bash
python auto_eval_harbor_task.py en-fpb \
    --model codex \
    --model-args "model=gpt-5-mini" \
    --output-dir results/my_eval \
    --write-out
```

## 📊 输出结果

### 结果文件

- **位置**: `results/auto_eval_<task_name>/results.json`
- **内容**: 
  - 各项指标（acc, f1, macro_f1, mcc 等）
  - 配置信息
  - 版本信息

### 详细输出（使用 --write-out）

- `Filtered<TaskName>_write_out_info.json`: 每个样本的详细输出

## 🔄 工作流程

```
输入: task_name (例如: "en-fpb")
  ↓
1. 从 /home/hefan/harbor/datasets/pixiu/<task_name>/ 提取样本 ID
  ↓
2. 映射任务名: en-fpb → flare_fpb
  ↓
3. 创建过滤任务（只包含提取的样本）
  ↓
4. 运行 Codex (gpt-5-mini) 评估
  ↓
5. 保存结果到 results/auto_eval_<task_name>/results.json
```

## ✨ 特性

1. **自动化**: 只需输入任务名，其他全自动
2. **智能映射**: 自动识别 Harbor 和 PIXIU 的任务名差异
3. **灵活提取**: 支持多种样本目录命名模式
4. **详细输出**: 可选择输出每个样本的详细信息
5. **易于扩展**: 可以轻松添加新的任务映射

## 📚 相关文档

- `AUTO_EVAL_README.md`: 详细使用说明
- `QUICK_START.md`: 快速开始指南
- `HARBOR_SAMPLES_EVALUATION.md`: Harbor 样本评估结果

## 🎯 示例

### 评估 en-fpb 任务

```bash
$ bash auto_eval.sh en-fpb

📂 从 Harbor 提取样本: /home/hefan/harbor/datasets/pixiu/en-fpb
✅ 找到 15 个样本
   样本 ID: ['fpb3891', 'fpb3901', ...]

🔄 映射任务名: en-fpb -> flare_fpb

🚀 运行评估...
   模型: codex
   模型参数: model=gpt-5-mini
   样本数: 15
   输出目录: results/auto_eval_en-fpb

✅ 评估完成！
   结果文件: results/auto_eval_en-fpb/results.json

📊 FilteredFPB 指标:
   acc: 0.8667
   f1: 0.8667
   macro_f1: 0.8968
   mcc: 0.7794
```

## 🔧 故障排除

如果遇到问题，请检查：

1. **Harbor 任务是否存在**: `ls /home/hefan/harbor/datasets/pixiu/<task_name>/`
2. **环境是否正确**: 确保在 `pixiu_env` conda 环境中
3. **API Key 是否设置**: `echo $OPENAI_API_KEY`
4. **任务名映射**: 查看 `AUTO_EVAL_README.md` 中的支持任务列表

