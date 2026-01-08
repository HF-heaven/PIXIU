#!/bin/bash
# 运行所有 Harbor 任务，使用 Docker 模式

set -euo pipefail

# 加载 nvm（确保 Codex CLI 可用）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use default

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="Your OpenAI API key"
export OPENAI_API_SECRET_KEY="${OPENAI_API_KEY}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU:/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

# 确保 Codex CLI 在 PATH 中（nvm 路径）
export PATH="$PATH:$HOME/.nvm/versions/node/$(nvm current)/bin"

cd /home/hefan/PIXIU

OUTPUT_BASE_DIR="results/harbor_test_docker"
LIMIT=15

# 所有任务映射
declare -A TASK_MAP=(
    ["en-fpb"]="flare_fpb"
    ["flare-headlines"]="flare_headlines"
    ["flare-ner"]="flare_ner"
    ["flare-finqa"]="flare_finqa"
    ["flare-tatqa"]="flare_tatqa"
    ["flare-fnxl"]="flare_fnxl"
    ["flare-fsrl"]="flare_fsrl"
    ["flare-ectsum"]="flare_ectsum"
    ["flare-edtsum"]="flare_edtsum"
    ["flare-fiqasa"]="flare_fiqasa"
    ["flare-cfa"]="flare_cfa"
    ["flare-german"]="flare_german"
    ["flare-australian"]="flare_australian"
    ["flare-tsa"]="flare_tsa"
    ["flare-finred"]="flare_finred"
    ["flare-cd"]="flare_cd"
    ["flare-causal20-sc"]="flare_causal20_sc"
    ["flare-mlesg"]="flare_mlesg"
    ["flare-ma"]="flare_ma"
    ["flare-multifin-en"]="flare_multifin_en"
    ["flare-sm-acl"]="flare_sm_acl"
    ["flare-sm-bigdata"]="flare_sm_bigdata"
    ["flare-sm-cikm"]="flare_sm_cikm"
    ["cra-ccfraud"]="flare_cra_ccfraud"
    ["cra-ccf"]="flare_cra_ccf"
    ["taiwan"]="flare_cra_taiwan"
    ["en-forecasting-travelinsurance"]="flare_cra_travelinsurace"
    ["finben-finer-ord"]="flare_finer_ord"
    ["finben-fomc"]="flare_fomc"
)

# 任务列表
TASKS=(
    # "en-fpb"
    # "flare-headlines"
    # "flare-ner"
    # "flare-finqa"
    # "flare-tatqa"
    # "flare-fnxl"
    # "flare-fsrl"
    # "flare-ectsum"
    # "flare-edtsum"
    # "flare-fiqasa"
    # "finben-fomc"
    # "flare-cfa"
    # "flare-german"
    # "flare-australian"
    # "flare-tsa"
    # "flare-finred"
    # "flare-cd"
    # "flare-causal20-sc"
    # "flare-mlesg"
    # "flare-ma"
    # "flare-multifin-en"
    # "flare-sm-acl"
    # "flare-sm-bigdata"
    # "flare-sm-cikm"
    # "cra-ccfraud"
    # "cra-ccf"
    # "taiwan"
    "en-forecasting-travelinsurance"
    # "finben-finer-ord"
)

echo "=========================================="
echo "运行所有 Harbor 任务（Docker 模式）"
echo "=========================================="
echo ""
echo "输出目录: $OUTPUT_BASE_DIR"
echo "每个任务使用前 $LIMIT 个样本"
echo "总任务数: ${#TASKS[@]}"
echo ""

# 创建输出基础目录
mkdir -p "$OUTPUT_BASE_DIR"

# 运行每个任务
for harbor_task_name in "${TASKS[@]}"; do
    pixiu_task_name="${TASK_MAP[$harbor_task_name]}"
    task_output_dir="$OUTPUT_BASE_DIR/$harbor_task_name"
    results_json_path="$task_output_dir/results.json"
    
    echo "=========================================="
    echo "运行任务: $harbor_task_name -> $pixiu_task_name"
    echo "输出目录: $task_output_dir"
    echo "=========================================="
    
    # 创建任务输出目录
    mkdir -p "$task_output_dir"
    
    # 运行评估命令
    python src/eval.py \
        --model codex \
        --model_args "model=gpt-5-mini,harbor_mode=True" \
        --tasks "$pixiu_task_name" \
        --limit "$LIMIT" \
        --write_out \
        --output_base_path "$task_output_dir" \
        --no_cache \
        --output_path "$results_json_path" || {
        echo "⚠️  任务 $harbor_task_name 运行失败，继续下一个任务..."
        continue
    }
    
    echo "✅ 任务 $harbor_task_name 完成"
    echo ""
done

echo "=========================================="
echo "所有任务运行完成！"
echo "=========================================="

