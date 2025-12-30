#!/bin/bash
# 直接运行缺失的 7 个任务

set -euo pipefail

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"
export OPENAI_API_SECRET_KEY="${OPENAI_API_KEY}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

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

# 创建一个临时的 Python 脚本
cat > /tmp/run_single_missing_task.py << 'PYEOF'
import sys
import json
from pathlib import Path

# Add src to path
PIXIU_ROOT = Path("/home/hefan/PIXIU")
sys.path.insert(0, str(PIXIU_ROOT))
sys.path.insert(0, str(PIXIU_ROOT / "src"))
sys.path.insert(0, str(PIXIU_ROOT / "src" / "financial-evaluation"))

from evaluator import simple_evaluate
from tasks import TASK_REGISTRY
from run_all_harbor_tasks import (
    extract_sample_ids_from_harbor,
    map_harbor_to_pixiu_task,
    create_filtered_task,
)

task_name = sys.argv[1]
harbor_datasets_path = Path("/home/hefan/harbor/datasets/pixiu")
output_dir = Path("/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini")
output_dir.mkdir(parents=True, exist_ok=True)

task_dir = harbor_datasets_path / task_name
if not task_dir.exists():
    print(f"  ⚠️  警告: 任务目录不存在: {task_dir}", file=sys.stderr)
    sys.exit(1)

sample_ids = extract_sample_ids_from_harbor(task_dir)
if not sample_ids:
    print(f"  ⚠️  警告: 未找到样本 ID", file=sys.stderr)
    sys.exit(1)

print(f"  样本数: {len(sample_ids)}")

pixiu_task_name = map_harbor_to_pixiu_task(task_name)
if not pixiu_task_name:
    print(f"  ⚠️  警告: 无法映射任务名", file=sys.stderr)
    sys.exit(1)

print(f"  映射到: {pixiu_task_name}")

if pixiu_task_name not in TASK_REGISTRY:
    print(f"  ⚠️  警告: PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到", file=sys.stderr)
    sys.exit(1)

# 创建过滤任务
original_task_class = TASK_REGISTRY[pixiu_task_name]
filtered_task_class = create_filtered_task(original_task_class, sample_ids, task_name=task_name)
filtered_task = filtered_task_class()

# 运行评估
task_output_dir = output_dir / task_name
task_output_dir.mkdir(parents=True, exist_ok=True)
output_file = task_output_dir / "results.json"

try:
    results = simple_evaluate(
        model="codex",
        model_args="model=gpt-5-mini",
        tasks=[filtered_task],
        num_fewshot=0,
        limit=None,
        write_out=True,
        output_base_path=str(task_output_dir),
    )
    
    # 保存结果
    output_file.write_text(json.dumps(results, indent=2))
    
    # 打印主要指标
    if "results" in results:
        for task_name_inner, task_results in results["results"].items():
            print(f"  📊 {task_name_inner} 指标:")
            for metric, value in task_results.items():
                if isinstance(value, (int, float)) and not metric.endswith("_stderr"):
                    print(f"     {metric}: {value:.4f}")
    
    print(f"  ✅ 完成！结果保存到: {output_file}")
    sys.exit(0)
    
except Exception as e:
    print(f"  ❌ 评估失败: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

TOTAL=${#MISSING_TASKS[@]}
CURRENT=0

for task_name in "${MISSING_TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/$TOTAL] 运行任务: $task_name"
    
    python /tmp/run_single_missing_task.py "$task_name" || {
        echo "  ❌ $task_name 失败"
    }
    
    echo ""
done

echo "=========================================="
echo "所有任务完成！"
echo "=========================================="

