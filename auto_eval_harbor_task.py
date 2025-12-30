#!/usr/bin/env python3
"""
自动化评估脚本：从 Harbor 提取样本并在 PIXIU 中运行评估

用法:
    python auto_eval_harbor_task.py <task_name> [--model MODEL] [--output-dir OUTPUT_DIR]

示例:
    python auto_eval_harbor_task.py en-fpb
    python auto_eval_harbor_task.py flare-headlines --model codex --output-dir results/auto_eval
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add src to path
PIXIU_ROOT = Path(__file__).parent
sys.path.insert(0, str(PIXIU_ROOT / "src"))
sys.path.insert(0, str(PIXIU_ROOT / "src" / "financial-evaluation"))

from evaluator import simple_evaluate
from tasks import TASK_REGISTRY


# Harbor 任务名到 PIXIU 任务名的映射
HARBOR_TO_PIXIU_TASK_MAP = {
    "en-fpb": "flare_fpb",
    "flare-fpb": "flare_fpb",
    "flare-headlines": "flare_headlines",
    "flare-ner": "flare_ner",
    "flare-finqa": "flare_finqa",
    "flare-tatqa": "flare_tatqa",
    "flare-fnxl": "flare_fnxl",
    "flare-fsrl": "flare_fsrl",
    "flare-ectsum": "flare_ectsum",
    "flare-edtsum": "flare_edtsum",
    "flare-fiqasa": "flare_fiqasa",
    "flare-fomc": "flare_fomc",
    "flare-cfa": "flare_cfa",
    "flare-german": "flare_german",
    "flare-australian": "flare_australian",
    "flare-tsa": "flare_tsa",
    "flare-finred": "flare_finred",
    "flare-cd": "flare_cd",
    "flare-causal20-sc": "flare_causal20_sc",
    "flare-mlesg": "flare_mlesg",
    "flare-ma": "flare_ma",
    "flare-multifin-en": "flare_multifin_en",
    "flare-sm-acl": "flare_sm_acl",
    "flare-sm-bigdata": "flare_sm_bigdata",
    "flare-sm-cikm": "flare_sm_cikm",
    "cra-ccfraud": "flare_cra_ccfraud",
    "cra-ccf": "flare_cra_ccf",
    "cra-taiwan": "flare_cra_taiwan",
    "en-forecasting-travelinsurance": "flare_cra_travelinsurace",
}


def extract_sample_ids_from_harbor(harbor_task_dir: Path) -> list[str]:
    """从 Harbor 任务目录中提取样本 ID。
    
    Args:
        harbor_task_dir: Harbor 任务目录路径，例如 /home/hefan/harbor/datasets/pixiu/en-fpb/
    
    Returns:
        样本 ID 列表，例如 ['fpb3891', 'fpb3901', ...]
    """
    if not harbor_task_dir.exists():
        raise ValueError(f"Harbor task directory not found: {harbor_task_dir}")
    
    sample_ids = []
    task_name = harbor_task_dir.name
    
    # 尝试不同的前缀模式
    # 例如: pixiu-fpb-fpb3891, pixiu-headlines-headlines82163
    prefixes = [
        f"pixiu-{task_name}-",
        f"pixiu-{task_name.replace('en-', '')}-",  # en-fpb -> fpb
        f"pixiu-{task_name.replace('flare-', '')}-",  # flare-headlines -> headlines
    ]
    
    for task_subdir in harbor_task_dir.iterdir():
        if task_subdir.is_dir():
            for prefix in prefixes:
                if task_subdir.name.startswith(prefix):
                    sample_id = task_subdir.name.replace(prefix, "")
                    sample_ids.append(sample_id)
                    break
    
    return sorted(sample_ids)


def map_harbor_to_pixiu_task(harbor_task_name: str) -> str:
    """将 Harbor 任务名映射到 PIXIU 任务名。
    
    Args:
        harbor_task_name: Harbor 任务名，例如 "en-fpb", "flare-headlines"
    
    Returns:
        PIXIU 任务名，例如 "flare_fpb", "flare_headlines"
    """
    # 直接查找映射表
    if harbor_task_name in HARBOR_TO_PIXIU_TASK_MAP:
        return HARBOR_TO_PIXIU_TASK_MAP[harbor_task_name]
    
    # 尝试规范化名称
    normalized = harbor_task_name.lower().replace("_", "-")
    if normalized in HARBOR_TO_PIXIU_TASK_MAP:
        return HARBOR_TO_PIXIU_TASK_MAP[normalized]
    
    # 尝试推断：如果以 "flare-" 开头，转换为 "flare_"
    if normalized.startswith("flare-"):
        pixiu_name = normalized.replace("-", "_")
        if pixiu_name in TASK_REGISTRY:
            return pixiu_name
    
    # 尝试推断：如果是 "en-fpb"，转换为 "flare_fpb"
    if normalized == "en-fpb":
        return "flare_fpb"
    
    raise ValueError(
        f"Unknown Harbor task name: {harbor_task_name}\n"
        f"Available mappings: {list(HARBOR_TO_PIXIU_TASK_MAP.keys())}"
    )


def create_filtered_task(task_class, sample_ids: list[str]):
    """创建过滤后的任务类，只包含指定的样本 ID。"""
    
    class FilteredTask(task_class):
        def test_docs(self):
            """过滤测试文档，只包含指定的样本 ID。"""
            all_docs = super().test_docs()
            filtered = [doc for doc in all_docs if doc.get("id") in sample_ids]
            return filtered
    
    # 复制类属性
    FilteredTask.__name__ = f"Filtered{task_class.__name__}"
    if hasattr(task_class, "DATASET_PATH"):
        FilteredTask.DATASET_PATH = task_class.DATASET_PATH
    if hasattr(task_class, "DATASET_NAME"):
        FilteredTask.DATASET_NAME = task_class.DATASET_NAME
    
    return FilteredTask


def main():
    parser = argparse.ArgumentParser(
        description="从 Harbor 提取样本并在 PIXIU 中运行评估",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 评估 en-fpb 任务
  python auto_eval_harbor_task.py en-fpb
  
  # 评估 flare-headlines 任务，使用自定义输出目录
  python auto_eval_harbor_task.py flare-headlines --output-dir results/my_eval
  
  # 使用不同的模型
  python auto_eval_harbor_task.py en-fpb --model codex --model-args "model=gpt-4o"
        """
    )
    parser.add_argument(
        "task_name",
        type=str,
        help="Harbor 任务名（例如: en-fpb, flare-headlines）",
    )
    parser.add_argument(
        "--harbor-datasets-path",
        type=Path,
        default=Path("/home/hefan/harbor/datasets/pixiu"),
        help="Harbor datasets 目录路径（默认: /home/hefan/harbor/datasets/pixiu）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="codex",
        help="模型类型（默认: codex）",
    )
    parser.add_argument(
        "--model-args",
        type=str,
        default="model=gpt-5-mini",
        help="模型参数（默认: model=gpt-5-mini）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="输出目录（默认: results/auto_eval_<task_name>）",
    )
    parser.add_argument(
        "--write-out",
        action="store_true",
        help="输出详细结果",
    )
    
    args = parser.parse_args()
    
    # 1. 提取样本 ID
    harbor_task_dir = args.harbor_datasets_path / args.task_name
    print(f"📂 从 Harbor 提取样本: {harbor_task_dir}")
    
    try:
        sample_ids = extract_sample_ids_from_harbor(harbor_task_dir)
        print(f"✅ 找到 {len(sample_ids)} 个样本")
        if len(sample_ids) <= 10:
            print(f"   样本 ID: {sample_ids}")
        else:
            print(f"   样本 ID (前5个): {sample_ids[:5]} ... (共 {len(sample_ids)} 个)")
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not sample_ids:
        print(f"⚠️  警告: 未找到任何样本，退出", file=sys.stderr)
        sys.exit(1)
    
    # 2. 映射到 PIXIU 任务名
    print(f"\n🔄 映射任务名: {args.task_name} -> ", end="")
    try:
        pixiu_task_name = map_harbor_to_pixiu_task(args.task_name)
        print(f"{pixiu_task_name}")
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 3. 获取 PIXIU 任务类
    if pixiu_task_name not in TASK_REGISTRY:
        print(f"❌ 错误: PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到", file=sys.stderr)
        print(f"   可用任务: {sorted(list(TASK_REGISTRY.keys()))[:10]}...", file=sys.stderr)
        sys.exit(1)
    
    original_task_class = TASK_REGISTRY[pixiu_task_name]
    
    # 4. 创建过滤后的任务
    filtered_task_class = create_filtered_task(original_task_class, sample_ids)
    filtered_task = filtered_task_class()
    
    # 5. 准备输出目录
    if args.output_dir is None:
        output_dir = PIXIU_ROOT / "results" / f"auto_eval_{args.task_name}"
    else:
        output_dir = args.output_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "results.json"
    
    # 6. 运行评估
    print(f"\n🚀 运行评估...")
    print(f"   模型: {args.model}")
    print(f"   模型参数: {args.model_args}")
    print(f"   样本数: {len(sample_ids)}")
    print(f"   输出目录: {output_dir}")
    
    try:
        results = simple_evaluate(
            model=args.model,
            model_args=args.model_args if args.model_args else None,
            tasks=[filtered_task],
            num_fewshot=0,
            limit=None,
            write_out=args.write_out,
            output_base_path=str(output_dir) if args.write_out else None,
        )
        
        # 7. 保存结果
        output_file.write_text(json.dumps(results, indent=2))
        print(f"\n✅ 评估完成！")
        print(f"   结果文件: {output_file}")
        
        # 打印主要指标
        if "results" in results:
            for task_name, task_results in results["results"].items():
                print(f"\n📊 {task_name} 指标:")
                for metric, value in task_results.items():
                    if isinstance(value, (int, float)) and not metric.endswith("_stderr"):
                        print(f"   {metric}: {value:.4f}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ 评估失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

