#!/bin/bash
# 重新运行失败的任务（ectsum 和 edtsum）

set -euo pipefail

echo "=========================================="
echo "重新运行失败的任务（ectsum 和 edtsum）"
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

# 验证 bert_score 已安装
echo "验证 bert_score 安装..."
python3 -c "import bert_score; print('✅ bert_score 已安装')" || {
    echo "❌ bert_score 未安装，正在安装..."
    pip install bert_score
}

# 运行修复脚本
echo ""
echo "开始重新运行失败的任务..."
python rerun_failed_tasks.py

echo ""
echo "=========================================="
echo "完成！"
echo "=========================================="

