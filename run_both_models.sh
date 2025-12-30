#!/bin/bash
# 运行 Codex 和 gpt-5-mini 两个模型的评估

set -euo pipefail

DATASET="${1:-en-fpb}"

echo "=========================================="
echo "PIXIU 评估 - Harbor 相同样本"
echo "运行两个模型: codex (gpt-5-mini) 和 ChatLM (gpt-5-mini)"
echo "=========================================="
echo ""

# 运行 Codex
echo ">>> 运行 Codex (gpt-5-mini)..."
bash run_harbor_samples.sh "$DATASET" codex gpt-5-mini

echo ""
echo "=========================================="
echo ">>> 运行 ChatLM (gpt-5-mini)..."
echo "=========================================="
echo ""

# 运行 ChatLM (gpt-5-mini) - 直接使用 gpt-5-mini 作为 model 名称
bash run_harbor_samples.sh "$DATASET" "gpt-5-mini" ""

echo ""
echo "=========================================="
echo "所有评估完成！"
echo "=========================================="

