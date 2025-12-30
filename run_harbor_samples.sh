#!/bin/bash
# 运行 Harbor 中生成的相同样本，使用 Codex 和 gpt-5-mini

set -euo pipefail

# 默认参数
DATASET="${1:-en-fpb}"
MODEL="${2:-codex}"
MODEL_NAME="${3:-gpt-5-mini}"

echo "=========================================="
echo "PIXIU 评估 - Harbor 相同样本"
echo "=========================================="
echo "数据集: $DATASET"
echo "模型类型: $MODEL"
echo "模型名称: $MODEL_NAME"
echo "=========================================="
echo ""

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"
# ChatLM also needs OPENAI_API_SECRET_KEY
export OPENAI_API_SECRET_KEY="${OPENAI_API_SECRET_KEY:-$OPENAI_API_KEY}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

# 准备输出路径
OUTPUT_DIR="results/harbor_samples_${DATASET}_${MODEL}_${MODEL_NAME}"
mkdir -p "$OUTPUT_DIR"

# 运行评估
cd /home/hefan/PIXIU
python run_specific_samples.py \
  --dataset "$DATASET" \
  --harbor-datasets-path /home/hefan/harbor/datasets/pixiu \
  --model "$MODEL" \
  --model-args "model=$MODEL_NAME" \
  --output-path "$OUTPUT_DIR/results.json" \
  --output-base-path "$OUTPUT_DIR" \
  --write-out

echo ""
echo "=========================================="
echo "评估完成！"
echo "结果文件: $OUTPUT_DIR/results.json"
echo "详细输出: $OUTPUT_DIR/"
echo "=========================================="

