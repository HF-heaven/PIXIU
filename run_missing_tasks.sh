#!/bin/bash
set -euo pipefail

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore"

# 设置 OpenAI API Key
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "Error: OPENAI_API_KEY environment variable is not set."
    exit 1
fi
export OPENAI_API_SECRET_KEY="${OPENAI_API_KEY}"

# 切换到 PIXIU 目录
cd /home/hefan/PIXIU

# 缺失的任务列表
MISSING_TASKS=(
    "en-forecasting-travelinsurance"
    "finben-finer-ord"
    "flare-causal20-sc"
    "flare-multifin-en"
    "flare-sm-acl"
    "flare-sm-bigdata"
    "flare-sm-cikm"
)

OUTPUT_DIR="results/harbor_all_tasks_codex_gpt-5-mini"

echo "=========================================="
echo "运行缺失的 7 个任务"
echo "=========================================="
echo ""

TOTAL=${#MISSING_TASKS[@]}
CURRENT=0

for task_name in "${MISSING_TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/$TOTAL] 运行任务: $task_name"
    
    # 运行评估
    if python auto_eval_harbor_task.py "$task_name" \
        --model codex \
        --model_args "model=gpt-5-mini" \
        --harbor_datasets_path /home/hefan/harbor/datasets/pixiu \
        --output_base_path "$OUTPUT_DIR" \
        --write_out; then
        echo "  ✅ $task_name 完成"
    else
        echo "  ❌ $task_name 失败"
    fi
    
    echo ""
done

echo "=========================================="
echo "所有任务完成！"
echo "=========================================="

