#!/bin/bash
# 运行所有 29 个 PIXIU 任务，直接使用测试集的前 15 个样本（不 shuffle）

set -euo pipefail

# 加载 nvm（确保 Codex CLI 可用）
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use default

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"
export OPENAI_API_SECRET_KEY="${OPENAI_API_KEY}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU:/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

# 确保 Codex CLI 在 PATH 中（nvm 路径）
export PATH="$PATH:$HOME/.nvm/versions/node/$(nvm current)/bin"

cd /home/hefan/PIXIU

OUTPUT_BASE_DIR="results/harbor_all_tasks_codex_gpt-5-mini_noshuffle"
LIMIT=15

# 所有任务映射（从 run_all_harbor_tasks.py 中提取）
declare -A TASK_MAP=(
    ["en-fpb"]="flare_fpb"
    ["flare-fpb"]="flare_fpb"
    ["flare-headlines"]="flare_headlines"
    ["flare-ner"]="flare_ner"
    ["flare-finqa"]="flare_finqa"
    ["flare-tatqa"]="flare_tatqa"
    ["flare-fnxl"]="flare_fnxl"
    ["flare-fsrl"]="flare_fsrl"
    ["flare-ectsum"]="flare_ectsum"
    ["flare-edtsum"]="flare_edtsum"
    ["flare-fiqasa"]="flare_fiqasa"
    ["flare-fomc"]="flare_fomc"
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
    ["cra-taiwan"]="flare_cra_taiwan"
    ["taiwan"]="flare_cra_taiwan"
    ["en-forecasting-travelinsurance"]="flare_cra_travelinsurace"
    ["finben-finer-ord"]="flare_finer_ord"
    ["finben-fomc"]="flare_fomc"
)

# 获取唯一的任务列表（去除重复）
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
    # "flare-fomc"
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
    "cra-taiwan"
    # "en-forecasting-travelinsurance"
    # "finben-finer-ord"
)

echo "=========================================="
echo "运行所有 29 个 PIXIU 任务（不 shuffle，前 15 个样本）"
echo "=========================================="
echo ""
echo "输出目录: $OUTPUT_BASE_DIR"
echo "每个任务使用前 $LIMIT 个样本"
echo "总任务数: ${#TASKS[@]}"
echo ""

# 创建输出目录
mkdir -p "$OUTPUT_BASE_DIR"

# 运行每个任务
for harbor_task_name in "${TASKS[@]}"; do
    pixiu_task_name="${TASK_MAP[$harbor_task_name]}"
    task_output_dir="$OUTPUT_BASE_DIR/$harbor_task_name"
    
    echo "=========================================="
    echo "运行任务: $harbor_task_name -> $pixiu_task_name"
    echo "输出目录: $task_output_dir"
    echo "=========================================="
    
    # 通过环境变量传递参数
    export HARBOR_TASK_NAME="$harbor_task_name"
    export PIXIU_TASK_NAME="$pixiu_task_name"
    export TASK_OUTPUT_DIR="$task_output_dir"
    export TASK_LIMIT="$LIMIT"
    
    python3 << 'PYEOF'
import sys
import json
import os
from pathlib import Path

# 确保路径正确
PIXIU_ROOT = Path("/home/hefan/PIXIU")
sys.path.insert(0, str(PIXIU_ROOT))
sys.path.insert(0, str(PIXIU_ROOT / "src"))
sys.path.insert(0, str(PIXIU_ROOT / "src" / "financial-evaluation"))

from evaluator import simple_evaluate
from tasks import TASK_REGISTRY

pixiu_task_name = os.environ["PIXIU_TASK_NAME"]
harbor_task_name = os.environ["HARBOR_TASK_NAME"]
output_dir = Path(os.environ["TASK_OUTPUT_DIR"])
limit = int(os.environ["TASK_LIMIT"])

output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "results.json"

if pixiu_task_name not in TASK_REGISTRY:
    print(f"  ❌ 错误: PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到", file=sys.stderr)
    sys.exit(1)

# 直接使用原始任务类，不使用过滤
original_task_class = TASK_REGISTRY[pixiu_task_name]
task = original_task_class()

# 对于 ccfraud, ccf, taiwan 这三个任务，使用 validation 而不是 test
use_validation = harbor_task_name in ["cra-ccfraud", "cra-ccf", "cra-taiwan", "taiwan"]

if use_validation:
    if not task.has_validation_docs():
        print(f"  ❌ 错误: 任务 '{pixiu_task_name}' 没有 validation_docs", file=sys.stderr)
        sys.exit(1)
    # 临时修改任务类，使其强制使用 validation_docs
    # 通过让 has_test_docs 返回 False，simple_evaluate 会自动使用 validation_docs
    original_has_test_docs = task.has_test_docs
    original_test_docs = task.test_docs
    task.has_test_docs = lambda: False
    task.test_docs = task.validation_docs
    task_docs = task.validation_docs()
    print(f"📊 使用 validation 集，总样本数: {len(task_docs)}")
else:
    if not task.has_test_docs():
        print(f"  ❌ 错误: 任务 '{pixiu_task_name}' 没有 test_docs", file=sys.stderr)
        sys.exit(1)
    task_docs = task.test_docs()
    print(f"📊 使用 test 集，总样本数: {len(task_docs)}")

print(f"📊 将使用前 {limit} 个样本")
print()

# 显示前 15 个样本的 ID
print("前 15 个样本的 ID:")
sample_ids_list = []
for i in range(min(limit, len(task_docs))):
    doc = task_docs[i]
    if isinstance(doc, dict):
        doc_id = doc.get('id', f'index_{i}')
    else:
        doc_id = f'index_{i}'
    sample_ids_list.append(doc_id)
    print(f"  [{i:2d}] {doc_id}")
print()

try:
    print(f"🚀 开始运行评估...")
    print(f"   模型: codex")
    print(f"   模型参数: model=gpt-5-mini")
    print(f"   输出目录: {output_dir}")
    print(f"   样本限制: {limit}")
    print()
    
    results = simple_evaluate(
        model="codex",
        model_args="model=gpt-5-mini",
        tasks=[task],
        num_fewshot=0,
        limit=limit,  # 限制为前 15 个样本
        write_out=True,
        output_base_path=str(output_dir),
    )
    
    # 恢复原始的方法（如果需要）
    if use_validation:
        task.has_test_docs = original_has_test_docs
        task.test_docs = original_test_docs
    
    # 保存结果
    output_file.write_text(json.dumps(results, indent=2))
    
    # 打印主要指标
    if "results" in results:
        for task_name_inner, task_results in results["results"].items():
            print(f"📊 {task_name_inner} 指标:")
            for metric, value in task_results.items():
                if isinstance(value, (int, float)) and not metric.endswith("_stderr"):
                    print(f"   {metric}: {value:.4f}")
    
    # 检查详细输出文件，验证样本 ID
    write_out_file = output_dir / f"{task_name_inner}_write_out_info.json"
    if write_out_file.exists():
        import json
        from datasets import load_dataset
        
        with open(write_out_file) as f:
            write_out = json.load(f)
        
        # 从数据集中获取实际 ID（如果可能）
        try:
            # 尝试获取数据集名称（对于某些任务可能不同）
            ds = None
            split_name = "validation" if use_validation else "test"
            if hasattr(task, 'DATASET_PATH'):
                ds = load_dataset(task.DATASET_PATH, split=split_name)
            elif hasattr(task, 'DATASET_NAME') and task.DATASET_NAME:
                ds = load_dataset(task.DATASET_NAME, split=split_name)
            
            if ds is not None:
                print()
                print(f"📋 验证：实际评估的样本 ID (共 {len(write_out)} 个):")
                print("=" * 100)
                print(f"{'doc_id':<8} {'期望索引':<10} {'期望ID':<15} {'实际ID':<15} {'匹配':<6}")
                print("=" * 100)
                
                for i, result in enumerate(write_out):
                    doc_id = result.get('doc_id', i)
                    
                    # 获取实际 ID（从数据集中）
                    if doc_id < len(ds):
                        actual_doc = ds[doc_id]
                        actual_id = actual_doc.get('id', f'index_{doc_id}')
                    else:
                        actual_id = f'index_{doc_id}'
                    
                    # 检查是否匹配期望的 ID
                    if i < len(sample_ids_list):
                        expected_id = sample_ids_list[i]
                        match = "✓" if actual_id == expected_id else "✗"
                    else:
                        expected_id = "N/A"
                        match = "?"
                    
                    print(f"{doc_id:<8} {i:<10} {expected_id:<15} {actual_id:<15} {match:<6}")
                
                print("=" * 100)
        except Exception as e:
            print(f"  注意: 无法验证样本 ID: {e}")
    
    print()
    print(f"✅ 完成！结果保存到: {output_file}")
    sys.exit(0)
    
except Exception as e:
    print(f"  ❌ 评估失败: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF
    
    if [ $? -eq 0 ]; then
        echo "✅ $harbor_task_name 完成"
    else
        echo "❌ $harbor_task_name 失败"
    fi
    echo ""
done

echo "=========================================="
echo "✅ 所有任务完成！"
echo "结果保存在: $OUTPUT_BASE_DIR"
echo "=========================================="

