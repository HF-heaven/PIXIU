#!/bin/bash
# 运行单个 flare-cfa 任务，使用 Harbor 数据集中的相同样本

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

TASK_NAME="flare-cfa"
OUTPUT_DIR="results/harbor_all_tasks_codex_gpt-5-mini/flare-cfa"

echo "=========================================="
echo "运行 flare-cfa 任务"
echo "=========================================="
echo ""
echo "Harbor 数据集路径: /home/hefan/harbor/datasets/pixiu/flare-cfa"
echo "输出目录: $OUTPUT_DIR"
echo ""

# 直接使用 Python 运行，确保路径正确
python3 << PYEOF
import sys
import json
from pathlib import Path

# 确保路径正确
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

task_name = "$TASK_NAME"
harbor_datasets_path = Path("/home/hefan/harbor/datasets/pixiu")
output_dir = Path("/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini")
output_dir.mkdir(parents=True, exist_ok=True)

task_dir = harbor_datasets_path / task_name
if not task_dir.exists():
    print(f"  ❌ 错误: 任务目录不存在: {task_dir}", file=sys.stderr)
    sys.exit(1)

print(f"📂 提取样本 ID...")
sample_ids = extract_sample_ids_from_harbor(task_dir)
if not sample_ids:
    print(f"  ❌ 错误: 未找到样本 ID", file=sys.stderr)
    sys.exit(1)

print(f"✅ 找到 {len(sample_ids)} 个样本:")
for sid in sample_ids:
    print(f"   {sid}")
print()

pixiu_task_name = map_harbor_to_pixiu_task(task_name)
if not pixiu_task_name:
    print(f"  ❌ 错误: 无法映射任务名", file=sys.stderr)
    sys.exit(1)

print(f"✅ 映射到 PIXIU 任务: {pixiu_task_name}")
print()

if pixiu_task_name not in TASK_REGISTRY:
    print(f"  ❌ 错误: PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到", file=sys.stderr)
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
    print(f"🚀 开始运行评估...")
    print(f"   模型: codex")
    print(f"   模型参数: model=gpt-5-mini")
    print(f"   输出目录: {task_output_dir}")
    print()
    
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
            print(f"📊 {task_name_inner} 指标:")
            for metric, value in task_results.items():
                if isinstance(value, (int, float)) and not metric.endswith("_stderr"):
                    print(f"   {metric}: {value:.4f}")
    
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
    echo ""
    echo "=========================================="
    echo "✅ flare-cfa 任务完成！"
    echo "结果保存在: $OUTPUT_DIR"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "❌ flare-cfa 任务失败"
    echo "=========================================="
    exit 1
fi
