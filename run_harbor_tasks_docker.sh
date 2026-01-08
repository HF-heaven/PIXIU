#!/bin/bash
# Run all Harbor tasks using Docker mode

set -euo pipefail

# Load nvm (ensure Codex CLI is available)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use default

# Activate conda environment
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# Set API key
export OPENAI_API_KEY="Your OpenAI API key"
export OPENAI_API_SECRET_KEY="${OPENAI_API_KEY}"

# Ensure Codex CLI is in PATH (nvm path)
export PATH="$PATH:$HOME/.nvm/versions/node/$(nvm current)/bin"

cd /home/hefan/PIXIU

# Set PYTHONPATH (using relative paths after cd)
export PYTHONPATH="$PWD:$PWD/src:$PWD/src/financial-evaluation:$PWD/src/metrics/BARTScore:${PYTHONPATH:-}"

OUTPUT_BASE_DIR="results/harbor_test_docker"
LIMIT=15

# All task mappings
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

# Task list
TASKS=(
    "en-fpb"
    "flare-headlines"
    "flare-ner"
    "flare-finqa"
    "flare-tatqa"
    "flare-fnxl"
    "flare-fsrl"
    "flare-ectsum"
    "flare-edtsum"
    "flare-fiqasa"
    "finben-fomc"
    "flare-cfa"
    "flare-german"
    "flare-australian"
    "flare-tsa"
    "flare-finred"
    "flare-cd"
    "flare-causal20-sc"
    "flare-mlesg"
    "flare-ma"
    "flare-multifin-en"
    "flare-sm-acl"
    "flare-sm-bigdata"
    "flare-sm-cikm"
    "cra-ccfraud"
    "cra-ccf"
    "taiwan"
    "en-forecasting-travelinsurance"
    "finben-finer-ord"
)

echo "=========================================="
echo "Running all Harbor tasks (Docker mode)"
echo "=========================================="
echo ""
echo "Output directory: $OUTPUT_BASE_DIR"
echo "Each task uses first $LIMIT samples"
echo "Total number of tasks: ${#TASKS[@]}"
echo ""

# Create output base directory
mkdir -p "$OUTPUT_BASE_DIR"

# Run each task
for harbor_task_name in "${TASKS[@]}"; do
    pixiu_task_name="${TASK_MAP[$harbor_task_name]}"
    task_output_dir="$OUTPUT_BASE_DIR/$harbor_task_name"
    results_json_path="$task_output_dir/results.json"
    
    echo "=========================================="
    echo "Running task: $harbor_task_name -> $pixiu_task_name"
    echo "Output directory: $task_output_dir"
    echo "=========================================="
    
    # Create task output directory
    mkdir -p "$task_output_dir"
    
    # Run evaluation command
    python src/eval.py \
        --model codex \
        --model_args "model=gpt-5-mini,harbor_mode=True" \
        --tasks "$pixiu_task_name" \
        --limit "$LIMIT" \
        --write_out \
        --output_base_path "$task_output_dir" \
        --no_cache \
        --output_path "$results_json_path" || {
        echo "⚠️  Task $harbor_task_name failed, continuing to next task..."
        continue
    }
    
    echo "✅ Task $harbor_task_name completed"
    echo ""
done

echo "=========================================="
echo "All tasks completed!"
echo "=========================================="

