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

# Batch run: multiple output base dirs (trail4, trail5, trail6)
OUTPUT_BASE_DIRS=(
    "results/harbor_test_docker_trail1"
    "results/harbor_test_docker_trail2"
    "results/harbor_test_docker_trail3"
)
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
echo "Output base dirs: ${OUTPUT_BASE_DIRS[*]}"
echo "Each task uses first $LIMIT samples"
echo "Total number of tasks per run: ${#TASKS[@]}"
echo ""

# Run for each output base directory
for OUTPUT_BASE_DIR in "${OUTPUT_BASE_DIRS[@]}"; do
    echo ""
    echo "########## Run: $OUTPUT_BASE_DIR ##########"
    mkdir -p "$OUTPUT_BASE_DIR"

    for harbor_task_name in "${TASKS[@]}"; do
        pixiu_task_name="${TASK_MAP[$harbor_task_name]}"
        task_output_dir="$OUTPUT_BASE_DIR/$harbor_task_name"
        results_json_path="$task_output_dir/results.json"

        echo "=========================================="
        echo "Running task: $harbor_task_name -> $pixiu_task_name"
        echo "Output directory: $task_output_dir"
        echo "=========================================="

        mkdir -p "$task_output_dir"
        echo "OpenAI API Key: $OPENAI_API_KEY"
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

    echo "✅ Run for $OUTPUT_BASE_DIR completed"
done

echo "=========================================="
echo "All runs completed!"
echo "=========================================="

