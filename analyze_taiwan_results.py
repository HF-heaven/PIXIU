#!/usr/bin/env python3
"""
分析 taiwan 任务的详细结果，显示每个样本的预测结果
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any

def extract_sample_ids_from_harbor(harbor_task_dir: Path) -> List[str]:
    """从 Harbor 任务目录中提取样本 ID。"""
    if not harbor_task_dir.exists():
        return []
    
    sample_ids = []
    
    # 对于 taiwan，目录格式是 pixiu-taiwan-taiwan{数字}
    for task_subdir in sorted(harbor_task_dir.iterdir()):
        if task_subdir.is_dir() and (task_subdir.name.startswith("pixiu-taiwan-") or task_subdir.name.startswith("taiwan")):
            # 提取 ID 部分
            if task_subdir.name.startswith("pixiu-taiwan-"):
                sample_id = task_subdir.name.replace("pixiu-taiwan-", "")
            else:
                sample_id = task_subdir.name
            sample_ids.append(sample_id)
    
    return sample_ids


def extract_predicted_answer(logit: str) -> str:
    """从模型输出中提取预测的答案（no 或 yes）。"""
    # 清理输出，转换为小写
    logit_lower = logit.lower().strip()
    
    # 尝试多种模式匹配
    patterns = [
        r'^(yes|no)\b',  # 开头就是 yes/no
        r'\b(yes|no)\b',  # 任何位置的 yes/no
        r'answer[:\s]*([yn]o|yes)',  # "answer: no" 或 "answer: yes"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, logit_lower)
        if match:
            result = match.group(1).lower()
            if result in ['yes', 'no']:
                return result
    
    # 如果都没匹配到，检查是否包含关键词
    if 'yes' in logit_lower and 'no' not in logit_lower[:logit_lower.find('yes')+3]:
        return 'yes'
    elif 'no' in logit_lower:
        return 'no'
    
    return "UNKNOWN"


def analyze_results():
    """分析 taiwan 任务的详细结果。"""
    
    # 文件路径
    harbor_task_dir = Path("/home/hefan/harbor/datasets/pixiu/taiwan")
    write_out_file = Path("/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini/taiwan/Filteredtaiwan_write_out_info.json")
    results_file = Path("/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini/taiwan/results.json")
    output_file = Path("/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini/taiwan/detailed_analysis.txt")
    
    # 1. 提取 Harbor 数据集中的样本 ID（按顺序）
    print("📂 提取样本 ID...")
    sample_ids = extract_sample_ids_from_harbor(harbor_task_dir)
    
    if not sample_ids:
        print(f"❌ 未找到样本 ID")
        return
    
    print(f"✅ 找到 {len(sample_ids)} 个样本")
    print()
    
    # 2. 读取详细结果
    if not write_out_file.exists():
        print(f"❌ 详细结果文件不存在: {write_out_file}")
        return
    
    with open(write_out_file) as f:
        detailed_results = json.load(f)
    
    print(f"✅ 读取了 {len(detailed_results)} 个样本的详细结果")
    print()
    
    # 3. 分析每个样本
    correct_samples = []
    incorrect_samples = []
    
    analysis_lines = []
    analysis_lines.append("=" * 80)
    analysis_lines.append("taiwan 任务详细分析报告")
    analysis_lines.append("=" * 80)
    analysis_lines.append("")
    
    for i, result in enumerate(detailed_results):
        doc_id = result.get("doc_id", i)
        prompt = result.get("prompt_0", "")
        logit = result.get("logit_0", "")
        truth = result.get("truth", "").strip().lower()
        acc = float(result.get("acc", "0"))
        
        # 提取预测答案
        predicted = extract_predicted_answer(logit)
        
        # doc_id 是顺序索引（0, 1, 2...），直接映射到样本 ID 列表
        if doc_id < len(sample_ids):
            sample_id = sample_ids[doc_id]
        else:
            sample_id = f"index_{doc_id}"
        
        # 判断是否正确：使用 acc 字段，如果 acc > 0.5 则认为正确
        is_correct = acc > 0.5
        
        # 提取问题（简化显示）
        question_match = re.search(r'Text:\s*(.*?)(?:\n|$)', prompt, re.DOTALL)
        question = question_match.group(1).strip()[:100] + "..." if question_match and len(question_match.group(1)) > 100 else (question_match.group(1).strip() if question_match else "N/A")
        
        sample_info = {
            "sample_id": sample_id,
            "doc_id": doc_id,
            "question": question,
            "predicted": predicted,
            "truth": truth,
            "is_correct": is_correct,
            "logit": logit[:200] + "..." if len(logit) > 200 else logit,
        }
        
        if is_correct:
            correct_samples.append(sample_info)
        else:
            incorrect_samples.append(sample_info)
        
        # 添加到报告
        status = "✅ 正确" if is_correct else "❌ 错误"
        analysis_lines.append(f"\n样本 {i+1}/{len(detailed_results)}: {sample_id} [{status}]")
        analysis_lines.append(f"  正确答案: {truth}")
        analysis_lines.append(f"  预测答案: {predicted}")
        analysis_lines.append(f"  模型输出: {logit[:150]}...")
        analysis_lines.append("-" * 80)
    
    # 4. 生成总结
    analysis_lines.append("\n" + "=" * 80)
    analysis_lines.append("总结")
    analysis_lines.append("=" * 80)
    analysis_lines.append(f"总样本数: {len(detailed_results)}")
    analysis_lines.append(f"正确: {len(correct_samples)} ({len(correct_samples)/len(detailed_results)*100:.1f}%)")
    analysis_lines.append(f"错误: {len(incorrect_samples)} ({len(incorrect_samples)/len(detailed_results)*100:.1f}%)")
    analysis_lines.append("")
    
    # 5. 列出正确的样本
    analysis_lines.append("=" * 80)
    analysis_lines.append("✅ 正确的样本")
    analysis_lines.append("=" * 80)
    for sample in correct_samples:
        analysis_lines.append(f"  {sample['sample_id']}: 预测={sample['predicted']}, 正确答案={sample['truth']}")
    analysis_lines.append("")
    
    # 6. 列出错误的样本
    analysis_lines.append("=" * 80)
    analysis_lines.append("❌ 错误的样本")
    analysis_lines.append("=" * 80)
    for sample in incorrect_samples:
        analysis_lines.append(f"  {sample['sample_id']}: 预测={sample['predicted']}, 正确答案={sample['truth']}")
        analysis_lines.append(f"    模型输出: {sample['logit'][:100]}...")
        analysis_lines.append("")
    
    # 7. 保存报告
    output_file.write_text("\n".join(analysis_lines))
    print(f"✅ 详细分析报告已保存到: {output_file}")
    
    # 8. 同时生成 JSON 格式的详细结果
    json_output_file = output_file.with_suffix('.json')
    all_samples_data = []
    for i, result in enumerate(detailed_results):
        doc_id = result.get("doc_id", i)
        if doc_id < len(sample_ids):
            sample_id = sample_ids[doc_id]
        else:
            sample_id = f"index_{doc_id}"
        
        all_samples_data.append({
            "sample_id": sample_id,
            "doc_id": doc_id,
            "predicted": extract_predicted_answer(result.get("logit_0", "")),
            "truth": result.get("truth", "").strip().lower(),
            "is_correct": float(result.get("acc", "0")) > 0.5,
            "acc": float(result.get("acc", "0")),
            "logit": result.get("logit_0", ""),
            "prompt": result.get("prompt_0", ""),
        })
    
    json_data = {
        "summary": {
            "total": len(detailed_results),
            "correct": len(correct_samples),
            "incorrect": len(incorrect_samples),
            "accuracy": len(correct_samples) / len(detailed_results) if detailed_results else 0,
        },
        "correct_samples": correct_samples,
        "incorrect_samples": incorrect_samples,
        "all_samples": all_samples_data
    }
    
    json_output_file.write_text(json.dumps(json_data, indent=2, ensure_ascii=False))
    print(f"✅ JSON 格式详细结果已保存到: {json_output_file}")
    
    # 9. 打印到控制台
    print("\n" + "\n".join(analysis_lines[-50:]))  # 打印最后50行


if __name__ == "__main__":
    analyze_results()





