#!/bin/bash
# 运行缺失的 7 个任务

set -euo pipefail

# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"
export OPENAI_API_SECRET_KEY="${OPENAI_API_KEY}"

# 设置 PYTHONPATH
export PYTHONPATH="/home/hefan/PIXIU/src:/home/hefan/PIXIU/src/financial-evaluation:/home/hefan/PIXIU/src/metrics/BARTScore:${PYTHONPATH:-}"

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

cd /home/hefan/PIXIU

echo "=========================================="
echo "运行缺失的 7 个任务"
echo "=========================================="
echo ""

TOTAL=${#MISSING_TASKS[@]}
CURRENT=0

for task_name in "${MISSING_TASKS[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/$TOTAL] 运行任务: $task_name"
    
    # 使用 run_all_harbor_tasks.py 但只运行指定的任务
    # 我们需要修改它来只运行指定的任务，或者直接调用 Python 函数
    python -c "
import sys
sys.path.insert(0, '/home/hefan/PIXIU/src')
sys.path.insert(0, '/home/hefan/PIXIU/src/financial-evaluation')

from run_all_harbor_tasks import (
    extract_sample_ids_from_harbor,
    map_harbor_to_pixiu_task,
    create_filtered_task,
    run_evaluation,
)
from pathlib import Path

task_name = '$task_name'
harbor_datasets_path = Path('/home/hefan/harbor/datasets/pixiu')
output_dir = Path('/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini')
output_dir.mkdir(parents=True, exist_ok=True)

task_dir = harbor_datasets_path / task_name
if not task_dir.exists():
    print(f'  ⚠️  警告: 任务目录不存在: {task_dir}')
    sys.exit(1)

sample_ids = extract_sample_ids_from_harbor(task_dir)
if not sample_ids:
    print(f'  ⚠️  警告: 未找到样本 ID')
    sys.exit(1)

print(f'  样本数: {len(sample_ids)}')

pixiu_task_name = map_harbor_to_pixiu_task(task_name)
if not pixiu_task_name:
    print(f'  ⚠️  警告: 无法映射任务名')
    sys.exit(1)

print(f'  映射到: {pixiu_task_name}')

try:
    result = run_evaluation(
        harbor_task_name=task_name,
        pixiu_task_name=pixiu_task_name,
        sample_ids=sample_ids,
        model='codex',
        model_args='model=gpt-5-mini',
        output_dir=output_dir,
        write_out=True,
    )
    if result:
        print(f'  ✅ {task_name} 完成')
    else:
        print(f'  ❌ {task_name} 失败')
        sys.exit(1)
except Exception as e:
    print(f'  ❌ {task_name} 出错: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" || {
        echo "  ❌ $task_name 失败"
    }
    
    echo ""
done

echo "=========================================="
echo "所有任务完成！"
echo "=========================================="

