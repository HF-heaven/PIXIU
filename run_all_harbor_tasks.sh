#!/bin/bash
# 批量运行所有 Harbor 任务在 PIXIU benchmark 中

set -euo pipefail

MODEL="${1:-codex}"
MODEL_NAME="${2:-gpt-5-mini}"

echo "=========================================="
echo "PIXIU 批量评估 - 所有 Harbor 任务"
echo "=========================================="
echo "模型类型: $MODEL"
echo "模型名称: $MODEL_NAME"
echo "=========================================="
echo ""

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

# 准备输出路径
OUTPUT_DIR="results/harbor_all_tasks_${MODEL}_${MODEL_NAME}"
mkdir -p "$OUTPUT_DIR"

# 运行评估
cd /home/hefan/PIXIU
python run_all_harbor_tasks.py \
  --harbor-datasets-path /home/hefan/harbor/datasets/pixiu \
  --model "$MODEL" \
  --model-args "model=$MODEL_NAME" \
  --output-dir "$OUTPUT_DIR" \
  --write-out \
  --summary-file "$OUTPUT_DIR/summary.json"

echo ""
echo "=========================================="
echo "评估完成！"
echo "结果目录: $OUTPUT_DIR"
echo "汇总文件: $OUTPUT_DIR/summary.json"
echo "=========================================="

