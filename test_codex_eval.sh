#!/bin/bash
# 小样本测试脚本 - Codex 评估

# 默认参数
TASK="${1:-flare_headlines}"  # 第一个参数：任务名称，默认 flare_headlines
LIMIT="${2:-5}"                # 第二个参数：测试样本数，默认 5
MODEL="${3:-gpt-4o}"          # 第三个参数：模型名称，默认 gpt-4o

echo "=========================================="
echo "Codex 小样本测试"
echo "=========================================="
echo "任务: $TASK"
echo "样本数: $LIMIT"
echo "模型: $MODEL"
echo "=========================================="
echo ""

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"

# 运行评估
cd /home/hefan/PIXIU
python src/eval.py \
  --model codex \
  --model_args "model=$MODEL" \
  --tasks "$TASK" \
  --limit "$LIMIT" \
  --output_path "results/codex_${TASK}_limit${LIMIT}.json" \
  --write_out \
  --output_base_path "results/codex_${TASK}_limit${LIMIT}_outputs"

echo ""
echo "=========================================="
echo "测试完成！"
echo "评估结果: results/codex_${TASK}_limit${LIMIT}.json"
echo "Agent 输出: results/codex_${TASK}_limit${LIMIT}_outputs/${TASK}_write_out_info.json"
echo ""
echo "查看 Agent 输出:"
echo "  cat results/codex_${TASK}_limit${LIMIT}_outputs/${TASK}_write_out_info.json | python -m json.tool | less"
echo "=========================================="

