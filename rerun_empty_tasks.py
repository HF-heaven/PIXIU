#!/usr/bin/env python3
"""
重新运行空结果的任务
"""

import json
import sys
from pathlib import Path

# Add src to path
PIXIU_ROOT = Path(__file__).parent
sys.path.insert(0, str(PIXIU_ROOT / "src"))
sys.path.insert(0, str(PIXIU_ROOT / "src" / "financial-evaluation"))

from run_all_harbor_tasks import (
    scan_harbor_datasets,
    map_harbor_to_pixiu_task,
    create_filtered_task,
    normalize_id,
)
from evaluator import simple_evaluate
from tasks import TASK_REGISTRY

def find_empty_tasks(output_dir: Path) -> list[str]:
    """找出空结果的任务。"""
    empty_tasks = []
    
    for task_dir in output_dir.iterdir():
        if task_dir.is_dir():
            results_file = task_dir / "results.json"
            if results_file.exists():
                try:
                    data = json.loads(results_file.read_text())
                    if not data.get("results") or data["results"] == {}:
                        empty_tasks.append(task_dir.name)
                except:
                    pass
    
    return empty_tasks

def main():
    output_dir = Path("results/harbor_all_tasks_codex_gpt-5-mini")
    harbor_datasets_path = Path("/home/hefan/harbor/datasets/pixiu")
    
    # 找出空结果的任务
    empty_tasks = find_empty_tasks(output_dir)
    
    if not empty_tasks:
        print("✅ 没有空结果的任务")
        return
    
    print(f"找到 {len(empty_tasks)} 个空结果的任务:")
    for task in empty_tasks:
        print(f"  - {task}")
    
    # 扫描 Harbor 数据集
    print("\n📂 扫描 Harbor 数据集...")
    tasks_data = scan_harbor_datasets(harbor_datasets_path)
    
    # 重新运行空结果的任务
    print(f"\n🚀 重新运行空结果的任务...")
    
    for harbor_task_name in empty_tasks:
        if harbor_task_name not in tasks_data:
            print(f"⚠️  警告: {harbor_task_name} 不在 Harbor 数据集中，跳过")
            continue
        
        print(f"\n[{empty_tasks.index(harbor_task_name) + 1}/{len(empty_tasks)}] 处理: {harbor_task_name}")
        sample_ids = tasks_data[harbor_task_name]
        print(f"  样本数: {len(sample_ids)}")
        
        # 映射任务名
        pixiu_task_name = map_harbor_to_pixiu_task(harbor_task_name)
        if not pixiu_task_name:
            print(f"  ⚠️  警告: 无法映射任务名 {harbor_task_name}，跳过")
            continue
        
        if pixiu_task_name not in TASK_REGISTRY:
            print(f"  ⚠️  警告: PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到，跳过")
            continue
        
        print(f"  映射到: {pixiu_task_name}")
        
        # 创建过滤任务
        original_task_class = TASK_REGISTRY[pixiu_task_name]
        filtered_task_class = create_filtered_task(original_task_class, sample_ids, task_name=harbor_task_name)
        filtered_task = filtered_task_class()
        
        # 检查过滤后的样本数
        filtered_docs = list(filtered_task.test_docs())
        print(f"  过滤后样本数: {len(filtered_docs)}")
        
        if len(filtered_docs) == 0:
            print(f"  ⚠️  警告: 过滤后没有样本，跳过")
            continue
        
        # 运行评估
        task_output_dir = output_dir / harbor_task_name
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
                for task_name, task_results in results["results"].items():
                    print(f"  📊 {task_name} 指标:")
                    for metric, value in task_results.items():
                        if isinstance(value, (int, float)) and not metric.endswith("_stderr"):
                            print(f"     {metric}: {value:.4f}")
            
            print(f"  ✅ 完成！结果保存到: {output_file}")
            
        except Exception as e:
            print(f"  ❌ 评估失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

