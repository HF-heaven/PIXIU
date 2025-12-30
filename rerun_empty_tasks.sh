#!/bin/bash
# 重新运行空结果的任务

set -euo pipefail

echo "=========================================="
echo "重新运行空结果的任务"
echo "=========================================="
echo ""

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

# 切换到 PIXIU 目录
cd /home/hefan/PIXIU

# 运行修复脚本
python rerun_empty_tasks.py

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="

