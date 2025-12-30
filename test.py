import sys
import json
from pathlib import Path

# 确保路径正确
PIXIU_ROOT = Path("/home/hefan/PIXIU")
sys.path.insert(0, str(PIXIU_ROOT))
sys.path.insert(0, str(PIXIU_ROOT / "src"))
sys.path.insert(0, str(PIXIU_ROOT / "src" / "financial-evaluation"))

from tasks import TASK_REGISTRY

task_name = "flare_sm_acl"
pixiu_task_name = "flare_sm_acl"
# output_dir = Path("$OUTPUT_DIR")
limit = 15

# output_dir.mkdir(parents=True, exist_ok=True)
# output_file = output_dir / "results.json"

if pixiu_task_name not in TASK_REGISTRY:
    print(f"  ❌ 错误: PIXIU 任务 '{pixiu_task_name}' 未在注册表中找到", file=sys.stderr)
    sys.exit(1)

# 直接使用原始任务类，不使用过滤
original_task_class = TASK_REGISTRY[pixiu_task_name]
task = original_task_class()

# 检查测试文档数量
test_docs = task.test_docs()
print(f"📊 测试集总样本数: {len(test_docs)}")
print(f"📊 将使用前 {limit} 个样本")
print()

# 显示前 15 个样本的 ID
print("前 15 个样本的 ID:")
sample_ids_list = []
for i in range(min(limit, len(test_docs))):
    doc = test_docs[i]
    if isinstance(doc, dict):
        doc_id = doc.get('id', f'index_{i}')
    else:
        doc_id = f'index_{i}'
    sample_ids_list.append(doc_id)
    print(f"  [{i:2d}] {doc_id}")
    print(doc)
    print("--------------------------------")
print(type(task.test_docs()))
# try:
#     print(f"🚀 开始运行评估...")
#     print(f"   模型: codex")
#     print(f"   模型参数: model=gpt-5-mini")
#     print(f"   输出目录: {output_dir}")
#     print(f"   样本限制: {limit}")
#     print()
    
#     results = simple_evaluate(
#         model="codex",
#         model_args="model=gpt-5-mini",
#         tasks=[task],
#         num_fewshot=0,
#         limit=limit,  # 限制为前 15 个样本
#         write_out=True,
#         output_base_path=str(output_dir),
#     )
    
#     # 保存结果
#     output_file.write_text(json.dumps(results, indent=2))
    
#     # 打印主要指标
#     if "results" in results:
#         for task_name_inner, task_results in results["results"].items():
#             print(f"📊 {task_name_inner} 指标:")
#             for metric, value in task_results.items():
#                 if isinstance(value, (int, float)) and not metric.endswith("_stderr"):
#                     print(f"   {metric}: {value:.4f}")
    
#     # 检查详细输出文件，验证样本 ID
#     write_out_file = output_dir / f"{task_name_inner}_write_out_info.json"
#     if write_out_file.exists():
#         import json
#         from datasets import load_dataset
        
#         with open(write_out_file) as f:
#             write_out = json.load(f)
        
#         # 从数据集中获取实际 ID
#         ds = load_dataset("TheFinAI/flare-sm-acl", split="test")
        
#         print()
#         print(f"📋 验证：实际评估的样本 ID (共 {len(write_out)} 个):")
#         print("=" * 100)
#         print(f"{'doc_id':<8} {'期望索引':<10} {'期望ID':<15} {'实际ID':<15} {'股票':<8} {'truth':<8} {'acc':<6} {'匹配':<6}")
#         print("=" * 100)
        
#         for i, result in enumerate(write_out):
#             doc_id = result.get('doc_id', i)
#             prompt = result.get('prompt_0', '')
#             truth = result.get('truth', '')
#             acc = result.get('acc', '')
            
#             # 提取股票符号
#             if '$' in prompt:
#                 stock_symbol = prompt.split('$')[1].split()[0] if '$' in prompt else 'N/A'
#             else:
#                 stock_symbol = 'N/A'
            
#             # 获取实际 ID（从数据集中）
#             if doc_id < len(ds):
#                 actual_doc = ds[doc_id]
#                 actual_id = actual_doc.get('id', f'index_{doc_id}')
#             else:
#                 actual_id = f'index_{doc_id}'
            
#             # 检查是否匹配期望的 ID
#             if i < len(sample_ids_list):
#                 expected_id = sample_ids_list[i]
#                 match = "✓" if actual_id == expected_id else "✗"
#             else:
#                 expected_id = "N/A"
#                 match = "?"
            
#             print(f"{doc_id:<8} {i:<10} {expected_id:<15} {actual_id:<15} ${stock_symbol:<7} {truth:<8} {acc:<6} {match:<6}")
        
#         print("=" * 100)
#         print()
#         print(f"期望的前 {limit} 个样本 ID: {sample_ids_list}")
    
#     print()
#     print(f"✅ 完成！结果保存到: {output_file}")
#     sys.exit(0)
    
# except Exception as e:
#     print(f"  ❌ 评估失败: {e}", file=sys.stderr)
#     import traceback
#     traceback.print_exc()
#     sys.exit(1)