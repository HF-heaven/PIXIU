# 快速开始 - 自动化评估

## 最简单的用法

只需要一行命令：

```bash
cd /home/hefan/PIXIU && bash auto_eval.sh en-fpb
```

## 完整流程说明

### 1. 确保 Harbor 任务已生成

首先确保 Harbor 中已经有生成的任务：

```bash
ls /home/hefan/harbor/datasets/pixiu/en-fpb/
# 应该看到类似 pixiu-fpb-fpb3891/ 这样的目录
```

### 2. 运行评估

```bash
cd /home/hefan/PIXIU
bash auto_eval.sh en-fpb
```

### 3. 查看结果

结果会保存在：
```
results/auto_eval_en-fpb/results.json
```

## 支持的参数

### Shell 脚本方式

```bash
# 基本用法
bash auto_eval.sh <task_name>

# 使用不同模型
bash auto_eval.sh en-fpb codex "model=gpt-4o"
```

### Python 脚本方式

```bash
# 基本用法
python auto_eval_harbor_task.py en-fpb

# 完整参数
python auto_eval_harbor_task.py en-fpb \
    --model codex \
    --model-args "model=gpt-5-mini" \
    --output-dir results/my_eval \
    --write-out
```

## 常见任务名

- `en-fpb` - Financial PhraseBank
- `flare-headlines` - Financial Headlines
- `flare-ner` - Named Entity Recognition
- `flare-finqa` - Financial QA
- `flare-tatqa` - Table-based QA

完整列表见 `AUTO_EVAL_README.md`

