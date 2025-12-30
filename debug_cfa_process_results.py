#!/usr/bin/env python3
"""
调试 CFA 任务的 process_results 逻辑
"""

import json
from pathlib import Path

# 读取实际的结果文件
write_out_file = Path("/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini/flare-cfa/FilteredCFA_write_out_info.json")
with open(write_out_file) as f:
    results = json.load(f)

# 模拟 process_results 的逻辑
def simulate_process_results(doc_choices, doc_gold_index, model_output, lower_case=False):
    """模拟 Classification.process_results 的逻辑"""
    print("=" * 80)
    print("模拟 process_results 逻辑")
    print("=" * 80)
    print(f"输入:")
    print(f"  doc['choices']: {doc_choices}")
    print(f"  doc['gold'] (index): {doc_gold_index}")
    print(f"  model_output: {model_output[:100]}...")
    print(f"  LOWER_CASE: {lower_case}")
    print()
    
    # 步骤1: 获取 gold
    gold = doc_choices[doc_gold_index]
    print(f"步骤1: gold = doc['choices'][doc['gold']] = '{gold}'")
    
    # 步骤2: 如果 LOWER_CASE，转换为小写
    if lower_case:
        gold = gold.lower()
        print(f"步骤2 (LOWER_CASE=True): gold = '{gold}'")
    else:
        print(f"步骤2 (LOWER_CASE=False): gold 保持为 '{gold}'")
    
    # 步骤3: 获取模型输出并 strip
    ini_result = model_output.strip()
    print(f"步骤3: ini_result = model_output.strip() = '{ini_result[:80]}...'")
    
    # 步骤4: 如果 LOWER_CASE，转换为小写
    if lower_case:
        ini_result = ini_result.lower()
        print(f"步骤4 (LOWER_CASE=True): ini_result = '{ini_result[:80]}...'")
    else:
        print(f"步骤4 (LOWER_CASE=False): ini_result 保持为 '{ini_result[:80]}...'")
    
    # 步骤5: 遍历 choices，查找匹配
    result = None
    print(f"步骤5: 遍历 choices 查找匹配:")
    for i, choice in enumerate(doc_choices):
        choice_check = choice
        if lower_case:
            choice_check = choice.lower()
        
        print(f"  检查 choice[{i}] = '{choice}' (检查时: '{choice_check}')")
        print(f"    判断: '{choice_check}' in '{ini_result[:50]}...'")
        
        if choice_check in ini_result:
            result = choice_check if lower_case else choice
            print(f"    ✓ 找到匹配！result = '{result}'")
            break
        else:
            print(f"    ✗ 未找到")
    
    # 步骤6: 如果未找到，设为 "missing"
    if result is None:
        result = "missing"
        print(f"步骤6: 未找到任何匹配，result = 'missing'")
    
    # 步骤7: 计算 acc
    acc = 1.0 if gold == result else 0.0
    print(f"步骤7: acc = 1.0 if '{gold}' == '{result}' else 0.0")
    print(f"  结果: acc = {acc}")
    print()
    
    return {
        "gold": gold,
        "result": result,
        "acc": acc
    }

# 测试几个实际的案例
print("测试案例 1: acc=0 但预测看起来正确")
print()
test_cases = [
    {
        "name": "样本 cfa25 (acc=0.0)",
        "choices": ["A", "B", "C"],
        "gold_index": 2,  # C
        "model_output": "C — electric utilities typically have stable, regulated cash flows and capital‑intensive assets, enabling higher leverage.",
        "truth": "C"
    },
    {
        "name": "样本 cfa319 (acc=0.0)",
        "choices": ["A", "B", "C"],
        "gold_index": 2,  # C
        "model_output": "C: $7.0 million.\n\nIn the long run the firm must cover all costs (variable + fixed) so total revenue must be at least $4M + $3M = $7M.",
        "truth": "C"
    },
    {
        "name": "样本 cfa1020 (acc=1.0, 正确的)",
        "choices": ["A", "B", "C"],
        "gold_index": 0,  # A
        "model_output": "A — Restricting short selling reduces price discovery and liquidity, which most directly impedes market efficiency.",
        "truth": "A"
    }
]

for case in test_cases:
    print(f"\n{case['name']}")
    print("-" * 80)
    result = simulate_process_results(
        case["choices"],
        case["gold_index"],
        case["model_output"],
        lower_case=False  # CFA 使用 LOWER_CASE = False
    )
    print(f"实际结果中的 truth: {case['truth']}")
    print(f"实际结果中的 acc: 0.0 (对于前两个), 1.0 (对于第三个)")
    print(f"模拟结果: {result}")
    print()





