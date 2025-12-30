#!/usr/bin/env python3
"""
批量运行所有 Harbor 任务在 PIXIU benchmark 中

读取 /home/hefan/harbor/datasets/pixiu 下所有任务，提取样本 ID，
然后在 PIXIU 中运行 Codex (gpt-5-mini) 评估。
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from collections import defaultdict

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
    "taiwan": "flare_cra_taiwan",
    "en-forecasting-travelinsurance": "flare_cra_travelinsurace",
    "finben-finer-ord": "flare_finer_ord",
    "finben-fomc": "flare_fomc",
}


def extract_sample_ids_from_harbor(harbor_task_dir: Path) -> list[str]:
    """从 Harbor 任务目录中提取样本 ID。"""
    if not harbor_task_dir.exists():
        return []
    
    sample_ids = []
    task_name = harbor_task_dir.name
    
    # 特殊处理的任务名映射（Harbor 任务名 -> 实际目录前缀）
    # 注意：对于需要保留完整 ID 的任务（如 flare-sm-acl），前缀应该只到任务名部分
    # 例如: pixiu-smacl-aclsm23404 -> 前缀应该是 "pixiu-smacl-"，提取的 ID 是 "aclsm23404"
    special_prefixes = {
        "en-forecasting-travelinsurance": ["pixiu-travel-travel"],
        "flare-causal20-sc": ["pixiu-causal20sc-causal20sc"],
        "flare-multifin-en": ["pixiu-multifin-multifineng"],
        "flare-sm-acl": ["pixiu-smacl-"],  # 修改：只到任务名部分，保留完整 ID (aclsm23404)
        "flare-sm-bigdata": ["pixiu-smbigdata-"],  # 修改：保留完整 ID (bigdatasm...)
        "flare-sm-cikm": ["pixiu-smcikm-"],  # 修改：保留完整 ID (cikmsm...)
        "finben-finer-ord": ["pixiu-finerord-finerord"],
    }
    
    # 尝试不同的前缀模式
    prefixes = []
    
    # 首先检查特殊映射
    if task_name in special_prefixes:
        prefixes.extend(special_prefixes[task_name])
    
    # 然后添加通用前缀
    prefixes.extend([
        f"pixiu-{task_name}-",
        f"pixiu-{task_name.replace('en-', '')}-",
        f"pixiu-{task_name.replace('flare-', '')}-",
        f"pixiu-{task_name.replace('finben-', '')}-",
        f"pixiu-{task_name.replace('cra-', '')}-",
    ])
    
    for task_subdir in harbor_task_dir.iterdir():
        if task_subdir.is_dir() and task_subdir.name.startswith("pixiu-"):
            matched = False
            for prefix in prefixes:
                if task_subdir.name.startswith(prefix):
                    sample_id = task_subdir.name.replace(prefix, "")
                    # 对于某些任务（如 flare-sm-acl），需要保留完整 ID（包括前缀）
                    # 例如: pixiu-smacl-aclsm23404 -> aclsm23404 (不是 23404)
                    sample_ids.append(sample_id)
                    matched = True
                    break
            
            # 如果都不匹配，尝试提取最后一个数字部分
            if not matched:
                import re
                # 尝试提取目录名中的 ID 部分（通常是最后一个数字序列）
                match = re.search(r'(\d+)$', task_subdir.name)
                if match:
                    sample_ids.append(match.group(1))
    
    return sorted(list(set(sample_ids)))  # 去重并排序


def map_harbor_to_pixiu_task(harbor_task_name: str) -> Optional[str]:
    """将 Harbor 任务名映射到 PIXIU 任务名。"""
    # 直接查找映射表
    if harbor_task_name in HARBOR_TO_PIXIU_TASK_MAP:
        return HARBOR_TO_PIXIU_TASK_MAP[harbor_task_name]
    
    # 尝试规范化名称
    normalized = harbor_task_name.lower().replace("_", "-")
    if normalized in HARBOR_TO_PIXIU_TASK_MAP:
        return HARBOR_TO_PIXIU_TASK_MAP[normalized]
    
    # 尝试推断
    if normalized.startswith("flare-"):
        pixiu_name = normalized.replace("-", "_")
        if pixiu_name in TASK_REGISTRY:
            return pixiu_name
    
    return None


def normalize_id(doc_id, sample_id: str) -> bool:
    """检查文档 ID 是否匹配样本 ID。
    
    支持多种匹配方式：
    1. 直接字符串匹配（优先）
    2. 整数匹配（如果 doc_id 是整数，sample_id 是字符串格式如 'ccf000586'）
    3. 提取数字部分匹配（仅当 doc_id 和 sample_id 格式相似时）
    
    注意：对于像 'aclsm23404' 这样的完整 ID，应该直接匹配，而不是提取数字部分。
    """
    # 直接匹配（最优先）
    if doc_id == sample_id:
        return True
    
    # 如果 doc_id 是整数，尝试从 sample_id 提取数字
    # 这种情况适用于：doc_id = 586, sample_id = 'ccf000586'
    if isinstance(doc_id, int):
        import re
        numbers = re.findall(r'\d+', sample_id)
        if numbers:
            # 取最后一个数字序列（通常是 ID 部分）
            extracted_num = int(numbers[-1])
            if doc_id == extracted_num:
                return True
    
    # 如果都是字符串，但格式不同，尝试提取数字部分比较
    # 这种情况适用于：doc_id = 'ccf586', sample_id = 'ccf000586'
    # 但不适用于：doc_id = 'aclsm23404', sample_id = 'aclsm23404'（应该已经通过直接匹配）
    if isinstance(doc_id, str) and sample_id:
        # 如果 doc_id 和 sample_id 的前缀相同，只比较数字部分
        # 例如: 'ccf586' vs 'ccf000586'
        import re
        # 提取前缀（非数字部分）
        doc_prefix = re.sub(r'\d+.*$', '', doc_id)
        sample_prefix = re.sub(r'\d+.*$', '', sample_id)
        
        # 如果前缀相同，比较数字部分
        if doc_prefix == sample_prefix and doc_prefix:
            doc_numbers = re.findall(r'\d+', doc_id)
            sample_numbers = re.findall(r'\d+', sample_id)
            if doc_numbers and sample_numbers:
                # 比较最后一个数字序列
                if doc_numbers[-1] == sample_numbers[-1]:
                    return True
    
    return False


def create_filtered_task(task_class, sample_ids: list[str], task_name: str = ""):
    """创建过滤后的任务类，只包含指定的样本 ID。
    
    Args:
        task_class: PIXIU 任务类
        sample_ids: Harbor 中提取的样本 ID 列表
        task_name: 任务名称（用于特殊处理，可选）
    """
    
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
                # 使用精确 ID 匹配（优先）或 normalize_id 进行灵活的 ID 匹配
                # 首先尝试精确匹配，如果失败再使用 normalize_id
                # 重要：按照 sample_ids 的顺序来排列过滤后的文档，而不是按照 all_docs 的顺序
                sample_ids_set = set(sample_ids)
                
                # 创建一个映射：sample_id -> doc
                doc_map = {}
                for doc in all_docs:
                    doc_id = doc.get("id")
                    if doc_id is None:
                        continue
                    
                    # 优先精确匹配
                    if doc_id in sample_ids_set:
                        doc_map[doc_id] = doc
                    else:
                        # 如果精确匹配失败，使用 normalize_id 进行灵活匹配
                        # 但要注意：对于像 'aclsm23404' 这样的 ID，不应该被解释为索引 23404
                        for sid in sample_ids:
                            if normalize_id(doc_id, sid):
                                doc_map[sid] = doc  # 使用 sample_id 作为 key
                                break
                
                # 按照 sample_ids 的顺序排列
                filtered = []
                for sid in sample_ids:
                    if sid in doc_map:
                        filtered.append(doc_map[sid])
                    else:
                        # 如果找不到，尝试通过 normalize_id 查找
                        for doc_id, doc in doc_map.items():
                            if normalize_id(doc_id, sid):
                                filtered.append(doc)
                                break
            
            return filtered
    
    # 复制类属性
    FilteredTask.__name__ = f"Filtered{task_class.__name__}"
    if hasattr(task_class, "DATASET_PATH"):
        FilteredTask.DATASET_PATH = task_class.DATASET_PATH
    if hasattr(task_class, "DATASET_NAME"):
        FilteredTask.DATASET_NAME = task_class.DATASET_NAME
    
    return FilteredTask


def scan_harbor_datasets(harbor_datasets_path: Path) -> dict[str, list[str]]:
    """扫描 Harbor 数据集目录，返回任务名到样本 ID 列表的映射。"""
    tasks_data = {}
    
    if not harbor_datasets_path.exists():
        print(f"Error: Harbor datasets path does not exist: {harbor_datasets_path}", file=sys.stderr)
        return tasks_data
    
    for task_dir in harbor_datasets_path.iterdir():
        if task_dir.is_dir():
            task_name = task_dir.name
            sample_ids = extract_sample_ids_from_harbor(task_dir)
            if sample_ids:
                tasks_data[task_name] = sample_ids
    
    return tasks_data


def main():
    parser = argparse.ArgumentParser(
        description="批量运行所有 Harbor 任务在 PIXIU benchmark 中",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--harbor-datasets-path",
        type=Path,
        default=Path("/home/hefan/harbor/datasets/pixiu"),
        help="Harbor datasets 目录路径",
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
        default=PIXIU_ROOT / "results" / "harbor_all_tasks",
        help="输出目录",
    )
    parser.add_argument(
        "--write-out",
        action="store_true",
        help="输出详细结果",
    )
    parser.add_argument(
        "--summary-file",
        type=Path,
        default=None,
        help="汇总结果文件路径（JSON 格式）",
    )
    
    args = parser.parse_args()
    
    # 1. 扫描 Harbor 数据集
    print("📂 扫描 Harbor 数据集...")
    tasks_data = scan_harbor_datasets(args.harbor_datasets_path)
    
    if not tasks_data:
        print(f"❌ 未找到任何任务", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ 找到 {len(tasks_data)} 个任务")
    for task_name, sample_ids in sorted(tasks_data.items()):
        print(f"   {task_name}: {len(sample_ids)} 个样本")
    
    # 2. 准备输出目录
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. 运行评估
    print(f"\n🚀 开始运行评估...")
    print(f"   模型: {args.model}")
    print(f"   模型参数: {args.model_args}")
    print(f"   输出目录: {args.output_dir}")
    print("")
    
    all_results = {}
    failed_tasks = []
    
    for task_idx, (harbor_task_name, sample_ids) in enumerate(sorted(tasks_data.items()), 1):
        print(f"[{task_idx}/{len(tasks_data)}] 处理: {harbor_task_name}")
        print(f"  样本数: {len(sample_ids)}")
        
        # 映射任务名
        pixiu_task_name = map_harbor_to_pixiu_task(harbor_task_name)
        if not pixiu_task_name:
            print(f"  ⚠️  警告: 无法映射任务名 {harbor_task_name}，跳过", file=sys.stderr)
            failed_tasks.append((harbor_task_name, "无法映射任务名"))
            continue
        
        if pixiu_task_name not in TASK_REGISTRY:
            print(f"  ⚠️  警告: PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到，跳过", file=sys.stderr)
            failed_tasks.append((harbor_task_name, f"PIXIU 任务未找到: {pixiu_task_name}"))
            continue
        
        print(f"  映射到: {pixiu_task_name}")
        
        # 创建过滤任务
        original_task_class = TASK_REGISTRY[pixiu_task_name]
        filtered_task_class = create_filtered_task(original_task_class, sample_ids, task_name=harbor_task_name)
        filtered_task = filtered_task_class()
        
        # 运行评估
        task_output_dir = args.output_dir / harbor_task_name
        task_output_dir.mkdir(parents=True, exist_ok=True)
        output_file = task_output_dir / "results.json"
        
        try:
            results = simple_evaluate(
                model=args.model,
                model_args=args.model_args if args.model_args else None,
                tasks=[filtered_task],
                num_fewshot=0,
                limit=None,
                write_out=args.write_out,
                output_base_path=str(task_output_dir) if args.write_out else None,
            )
            
            # 保存结果
            output_file.write_text(json.dumps(results, indent=2))
            all_results[harbor_task_name] = {
                "pixiu_task": pixiu_task_name,
                "sample_count": len(sample_ids),
                "results": results,
                "output_file": str(output_file),
            }
            
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
            failed_tasks.append((harbor_task_name, str(e)))
        
        print("")
    
    # 4. 保存汇总结果
    summary = {
        "total_tasks": len(tasks_data),
        "successful_tasks": len(all_results),
        "failed_tasks": len(failed_tasks),
        "model": args.model,
        "model_args": args.model_args,
        "results": all_results,
        "failed": failed_tasks,
    }
    
    if args.summary_file:
        summary_file = args.summary_file
    else:
        summary_file = args.output_dir / "summary.json"
    
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(json.dumps(summary, indent=2))
    
    # 5. 打印总结
    print("=" * 60)
    print("📊 评估总结")
    print("=" * 60)
    print(f"总任务数: {len(tasks_data)}")
    print(f"成功: {len(all_results)}")
    print(f"失败: {len(failed_tasks)}")
    print(f"汇总文件: {summary_file}")
    print("")
    
    if failed_tasks:
        print("失败的任务:")
        for task_name, error in failed_tasks:
            print(f"  - {task_name}: {error}")
    
    return summary


if __name__ == "__main__":
    main()

