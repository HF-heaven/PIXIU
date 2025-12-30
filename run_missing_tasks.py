#!/usr/bin/env python3
"""
运行缺失的 7 个 Harbor 任务
"""

import sys
from pathlib import Path

# Add src to path
PIXIU_ROOT = Path(__file__).parent
sys.path.insert(0, str(PIXIU_ROOT / "src"))
sys.path.insert(0, str(PIXIU_ROOT / "src" / "financial-evaluation"))

# 导入 run_all_harbor_tasks 中的函数
from run_all_harbor_tasks import (
    extract_sample_ids_from_harbor,
    map_harbor_to_pixiu_task,
    create_filtered_task,
    run_evaluation,
)

# 缺失的任务列表
MISSING_TASKS = [
    "en-forecasting-travelinsurance",
    "finben-finer-ord",
    "flare-causal20-sc",
    "flare-multifin-en",
    "flare-sm-acl",
    "flare-sm-bigdata",
    "flare-sm-cikm",
]

HARBOR_DATASETS_PATH = Path("/home/hefan/harbor/datasets/pixiu")
OUTPUT_DIR = PIXIU_ROOT / "results" / "harbor_all_tasks_codex_gpt-5-mini"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("==========================================")
    print("运行缺失的 7 个任务")
    print("==========================================")
    print("")
    
    for idx, task_name in enumerate(MISSING_TASKS, 1):
        print(f"[{idx}/{len(MISSING_TASKS)}] 处理: {task_name}")
        
        task_dir = HARBOR_DATASETS_PATH / task_name
        if not task_dir.exists():
            print(f"  ⚠️  警告: 任务目录不存在: {task_dir}")
            continue
        
        # 提取样本 ID
        sample_ids = extract_sample_ids_from_harbor(task_dir)
        if not sample_ids:
            print(f"  ⚠️  警告: 未找到样本 ID")
            continue
        
        print(f"  样本数: {len(sample_ids)}")
        
        # 映射任务名
        pixiu_task_name = map_harbor_to_pixiu_task(task_name)
        if not pixiu_task_name:
            print(f"  ⚠️  警告: 无法映射任务名")
            continue
        
        print(f"  映射到: {pixiu_task_name}")
        
        # 运行评估
        try:
            result = run_evaluation(
                harbor_task_name=task_name,
                pixiu_task_name=pixiu_task_name,
                sample_ids=sample_ids,
                model="codex",
                model_args="model=gpt-5-mini",
                output_dir=OUTPUT_DIR,
                write_out=True,
            )
            
            if result:
                print(f"  ✅ {task_name} 完成")
            else:
                print(f"  ❌ {task_name} 失败")
        except Exception as e:
            print(f"  ❌ {task_name} 出错: {e}")
            import traceback
            traceback.print_exc()
        
        print("")
    
    print("==========================================")
    print("所有任务完成！")
    print("==========================================")

if __name__ == "__main__":
    main()

