#!/usr/bin/env python3
"""
运行单个 flare-cfa 任务，使用 Harbor 数据集中的相同样本
"""

import json
import sys
from pathlib import Path

# Add src to path
PIXIU_ROOT = Path(__file__).parent
sys.path.insert(0, str(PIXIU_ROOT / "src"))
sys.path.insert(0, str(PIXIU_ROOT / "src" / "financial-evaluation"))

from evaluator import simple_evaluate
from tasks import TASK_REGISTRY

# Harbor 任务目录
HARBOR_TASK_DIR = Path("/home/hefan/harbor/datasets/pixiu/flare-cfa")
OUTPUT_DIR = Path("/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini/flare-cfa")

def extract_sample_ids_from_harbor(harbor_task_dir: Path) -> list[str]:
    """从 Harbor 任务目录中提取样本 ID。"""
    if not harbor_task_dir.exists():
        return []
    
    sample_ids = []
    
    # 对于 flare-cfa，目录格式是 pixiu-cfa-cfa{数字}
    for task_subdir in harbor_task_dir.iterdir():
        if task_subdir.is_dir() and task_subdir.name.startswith("pixiu-cfa-"):
            # 提取 ID 部分: pixiu-cfa-cfa2 -> cfa2
            sample_id = task_subdir.name.replace("pixiu-cfa-", "")
            sample_ids.append(sample_id)
    
    return sorted(list(set(sample_ids)))  # 去重并排序


def normalize_id(doc_id, sample_id: str) -> bool:
    """检查文档 ID 是否匹配样本 ID。"""
    # 直接匹配
    if doc_id == sample_id:
        return True
    
    # 如果 doc_id 是整数，尝试从 sample_id 提取数字
    if isinstance(doc_id, int):
        import re
        numbers = re.findall(r'\d+', sample_id)
        if numbers:
            return doc_id == int(numbers[-1])
    
    # 如果都是字符串，尝试提取数字部分匹配
    if isinstance(doc_id, str):
        import re
        doc_numbers = re.findall(r'\d+', doc_id)
        sample_numbers = re.findall(r'\d+', sample_id)
        if doc_numbers and sample_numbers:
            return doc_numbers[-1] == sample_numbers[-1]
    
    return False


def create_filtered_task(task_class, sample_ids: list[str], task_name: str = ""):
    """创建过滤后的任务类，只包含指定的样本 ID。"""
    
    class FilteredTask(task_class):
        def test_docs(self):
            """过滤测试文档，只包含指定的样本 ID。"""
            all_docs = super().test_docs()
            filtered = []
            
            # 对于没有 id 字段的任务（如 flare-cfa），使用索引匹配
            if not all_docs or "id" not in all_docs[0]:
                # 从 sample_ids 提取索引
                # 例如: 'cfa468' -> 468, 'cfa1020' -> 1020
                import re
                indices = []
                for sid in sample_ids:
                    numbers = re.findall(r'\d+', sid)
                    if numbers:
                        # 取最后一个数字序列
                        indices.append(int(numbers[-1]))
                
                # 使用索引过滤
                filtered = [all_docs[i] for i in indices if i < len(all_docs)]
            else:
                # 使用 normalize_id 进行灵活的 ID 匹配
                filtered = [
                    doc for doc in all_docs 
                    if any(normalize_id(doc.get("id"), sid) for sid in sample_ids)
                ]
            
            return filtered
    
    # 复制类属性
    FilteredTask.__name__ = f"Filtered{task_class.__name__}"
    if hasattr(task_class, "DATASET_PATH"):
        FilteredTask.DATASET_PATH = task_class.DATASET_PATH
    if hasattr(task_class, "DATASET_NAME"):
        FilteredTask.DATASET_NAME = task_class.DATASET_NAME
    
    return FilteredTask


def main():
    print("=" * 60)
    print("运行 flare-cfa 任务")
    print("=" * 60)
    print()
    
    # 1. 提取样本 ID
    print("📂 提取样本 ID...")
    sample_ids = extract_sample_ids_from_harbor(HARBOR_TASK_DIR)
    
    if not sample_ids:
        print(f"❌ 未找到任何样本 ID", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ 找到 {len(sample_ids)} 个样本:")
    for sid in sample_ids:
        print(f"   {sid}")
    print()
    
    # 2. 映射任务名
    pixiu_task_name = "flare_cfa"
    if pixiu_task_name not in TASK_REGISTRY:
        print(f"❌ PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ 映射到 PIXIU 任务: {pixiu_task_name}")
    print()
    
    # 3. 创建过滤任务
    original_task_class = TASK_REGISTRY[pixiu_task_name]
    filtered_task_class = create_filtered_task(original_task_class, sample_ids, task_name="flare-cfa")
    filtered_task = filtered_task_class()
    
    # 4. 准备输出目录
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "results.json"
    
    # 5. 运行评估
    print("🚀 开始运行评估...")
    print(f"   模型: codex")
    print(f"   模型参数: model=gpt-5-mini")
    print(f"   输出目录: {OUTPUT_DIR}")
    print()
    
    try:
        results = simple_evaluate(
            model="codex",
            model_args="model=gpt-5-mini",
            tasks=[filtered_task],
            num_fewshot=0,
            limit=None,
            write_out=True,
            output_base_path=str(OUTPUT_DIR),
        )
        
        # 保存结果
        output_file.write_text(json.dumps(results, indent=2))
        
        # 打印主要指标
        if "results" in results:
            for task_name, task_results in results["results"].items():
                print(f"📊 {task_name} 指标:")
                for metric, value in task_results.items():
                    if isinstance(value, (int, float)) and not metric.endswith("_stderr"):
                        print(f"   {metric}: {value:.4f}")
        
        print()
        print(f"✅ 完成！结果保存到: {output_file}")
        
    except Exception as e:
        print(f"❌ 评估失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()





