# 自动化评估脚本使用说明

## 概述

这个自动化流程可以让你只需输入任务名，就能自动：
1. 从 Harbor 的 `datasets/pixiu/<task_name>/` 提取样本 ID
2. 在 PIXIU 中运行对应的任务（使用 Codex gpt-5-mini）
3. 输出评估结果

## 快速开始

### 方法 1: 使用 Shell 脚本（推荐）

```bash
cd /home/hefan/PIXIU
bash auto_eval.sh en-fpb
```

### 方法 2: 直接使用 Python 脚本

```bash
cd /home/hefan/PIXIU
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:$PYTHONPATH"

python auto_eval_harbor_task.py en-fpb
```

## 详细用法

### 基本用法

```bash
# 评估 en-fpb 任务
python auto_eval_harbor_task.py en-fpb

# 评估 flare-headlines 任务
python auto_eval_harbor_task.py flare-headlines

# 使用自定义输出目录
python auto_eval_harbor_task.py en-fpb --output-dir results/my_eval

# 输出详细结果（包括每个样本的输出）
python auto_eval_harbor_task.py en-fpb --write-out
```

### 高级用法

```bash
# 使用不同的模型
python auto_eval_harbor_task.py en-fpb --model codex --model-args "model=gpt-4o"

# 指定 Harbor 数据集路径
python auto_eval_harbor_task.py en-fpb --harbor-datasets-path /path/to/harbor/datasets/pixiu
```

## 支持的任务

脚本会自动映射 Harbor 任务名到 PIXIU 任务名。支持的任务包括：

- `en-fpb` → `flare_fpb`
- `flare-headlines` → `flare_headlines`
- `flare-ner` → `flare_ner`
- `flare-finqa` → `flare_finqa`
- `flare-tatqa` → `flare_tatqa`
- `flare-fnxl` → `flare_fnxl`
- `flare-fsrl` → `flare_fsrl`
- `flare-ectsum` → `flare_ectsum`
- `flare-edtsum` → `flare_edtsum`
- `flare-fiqasa` → `flare_fiqasa`
- `flare-fomc` → `flare_fomc`
- `flare-cfa` → `flare_cfa`
- `flare-german` → `flare_german`
- `flare-australian` → `flare_australian`
- `flare-tsa` → `flare_tsa`
- `flare-finred` → `flare_finred`
- `flare-cd` → `flare_cd`
- `flare-causal20-sc` → `flare_causal20_sc`
- `flare-mlesg` → `flare_mlesg`
- `flare-ma` → `flare_ma`
- `flare-multifin-en` → `flare_multifin_en`
- `flare-sm-acl` → `flare_sm_acl`
- `flare-sm-bigdata` → `flare_sm_bigdata`
- `flare-sm-cikm` → `flare_sm_cikm`
- `cra-ccfraud` → `flare_cra_ccfraud`
- `cra-ccf` → `flare_cra_ccf`
- `cra-taiwan` → `flare_cra_taiwan`
- `en-forecasting-travelinsurance` → `flare_cra_travelinsurace`

## 输出结果

评估结果会保存在：
- **默认位置**: `results/auto_eval_<task_name>/results.json`
- **自定义位置**: 使用 `--output-dir` 指定的目录

结果文件包含：
- 各项指标（accuracy, f1, macro_f1, mcc 等）
- 配置信息（模型、参数等）
- 版本信息

如果使用 `--write-out`，还会生成：
- `Filtered<TaskName>_write_out_info.json`: 每个样本的详细输出

## 工作流程

1. **提取样本 ID**: 从 `harbor/datasets/pixiu/<task_name>/` 目录中扫描所有 `pixiu-*` 子目录，提取样本 ID
2. **映射任务名**: 将 Harbor 任务名映射到 PIXIU 任务注册表中的任务名
3. **创建过滤任务**: 创建一个只包含指定样本的过滤任务类
4. **运行评估**: 使用 Codex (gpt-5-mini) 运行评估
5. **保存结果**: 将结果保存为 JSON 文件

## 示例输出

```
📂 从 Harbor 提取样本: /home/hefan/harbor/datasets/pixiu/en-fpb
✅ 找到 15 个样本
   样本 ID: ['fpb3891', 'fpb3901', 'fpb3982', ...]

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

## 故障排除

### 1. 找不到 Harbor 任务目录

**错误**: `Harbor task directory not found`

**解决**: 确保 Harbor 任务已生成，路径为 `/home/hefan/harbor/datasets/pixiu/<task_name>/`

### 2. 找不到 PIXIU 任务

**错误**: `PIXIU task 'xxx' not found in registry`

**解决**: 检查任务名映射是否正确，或手动添加到 `HARBOR_TO_PIXIU_TASK_MAP`

### 3. 未找到样本

**错误**: `未找到任何样本`

**解决**: 检查 Harbor 任务目录中是否有 `pixiu-*` 子目录

### 4. 环境问题

如果遇到 `AttributeError: module 'torch.utils._pytree'` 等错误，这是环境依赖问题，不影响脚本逻辑。

## 文件说明

- `auto_eval_harbor_task.py`: 主评估脚本
- `auto_eval.sh`: Shell 包装脚本，自动设置环境
- `AUTO_EVAL_README.md`: 本说明文档

