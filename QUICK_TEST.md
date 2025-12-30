# Codex 小样本测试指南

## 快速测试

### 方法 1: 使用测试脚本（推荐）

```bash
# 在 pixiu_env 环境中
conda activate pixiu_env

# 基本用法（默认：flare_headlines，5 个样本，gpt-4o）
bash test_codex_eval.sh

# 指定任务和样本数
bash test_codex_eval.sh flare_headlines 10

# 指定任务、样本数和模型
bash test_codex_eval.sh flare_headlines 5 gpt-4o
```

### 方法 2: 直接使用命令行

```bash
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"

cd /home/hefan/PIXIU

# 测试 5 个样本
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 5

# 测试 10 个样本
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 10

# 测试其他任务
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_finqa \
  --limit 5
```

## 参数说明

- `--limit N`: 限制测试样本数为 N
  - `--limit 1`: 只测试 1 个样本（最快）
  - `--limit 5`: 测试 5 个样本（推荐用于快速验证）
  - `--limit 10`: 测试 10 个样本
  - 不指定 `--limit`: 运行完整数据集

- `--tasks <task_name>`: 指定要测试的任务
  - `flare_headlines`: 标题分类
  - `flare_finqa`: 金融问答
  - `flare_tatqa`: 表格问答
  - 等等...

- `--model_args model=<model_name>`: 指定 Codex 使用的模型
  - `gpt-4o` (推荐)
  - `gpt-4-turbo`
  - `gpt-4`

## 常用测试命令

```bash
# 最快测试（1 个样本）
python src/eval.py --model codex --model_args model=gpt-4o --tasks flare_headlines --limit 1

# 快速验证（5 个样本）
python src/eval.py --model codex --model_args model=gpt-4o --tasks flare_headlines --limit 5

# 小规模测试（10 个样本）
python src/eval.py --model codex --model_args model=gpt-4o --tasks flare_headlines --limit 10
```

## 结果输出

结果会显示在终端，也可以使用 `--output_path` 保存到文件：

```bash
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 5 \
  --output_path results/codex_test.json
```

## 注意事项

1. ⚠️ `--limit` 参数仅用于测试，完整评估结果不应使用 limit
2. 小样本测试主要用于验证配置是否正确
3. Codex CLI 调用可能需要一些时间，请耐心等待
4. 确保 API key 有足够的配额

