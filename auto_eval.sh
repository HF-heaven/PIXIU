#!/bin/bash
# 便捷的 Shell 包装脚本，用于运行自动化评估

set -euo pipefail

TASK_NAME="${1:-}"
MODEL="${2:-codex}"
MODEL_ARGS="${3:-model=gpt-5-mini}"

if [ -z "$TASK_NAME" ]; then
    echo "用法: $0 <task_name> [model] [model_args]"
    echo ""
    echo "示例:"
    echo "  $0 en-fpb"
    echo "  $0 flare-headlines codex 'model=gpt-5-mini'"
    echo ""
    echo "可用的 Harbor 任务名:"
    echo "  - en-fpb"
    echo "  - flare-headlines"
    echo "  - flare-ner"
    echo "  - flare-finqa"
    echo "  - flare-tatqa"
    echo "  - ... (更多任务见 Harbor datasets/pixiu/)"
    exit 1
fi

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

# 运行评估
cd /home/hefan/PIXIU
python auto_eval_harbor_task.py \
    "$TASK_NAME" \
    --model "$MODEL" \
    --model-args "$MODEL_ARGS" \
    --write-out

echo ""
echo "=========================================="
echo "评估完成！"
echo "=========================================="

