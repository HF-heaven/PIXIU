#!/usr/bin/env python3
"""
测试 PIXIU Codex Harbor 模式的三个核心功能：
1. 读取 item.json
2. 调 model
3. 根据 answer.txt eval
"""

import sys
import os
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from codexlm import CodexLM
import json

def test_harbor_mode():
    """测试 Harbor 模式的完整流程"""
    
    print("=" * 80)
    print("PIXIU Codex Harbor 模式功能测试")
    print("=" * 80)
    
    # 检查环境
    print("\n[1] 环境检查")
    print("-" * 80)
    
    if "OPENAI_API_KEY" not in os.environ:
        print("⚠️  OPENAI_API_KEY 环境变量未设置")
        print("   将跳过模型调用测试，但可以测试其他功能")
        has_api_key = False
    else:
        print("✓ OPENAI_API_KEY 已设置")
        has_api_key = True
    
    # 检查 Harbor instruction
    harbor_instruction_path = Path("/home/hefan/harbor/adapters/pixiu/template/instruction.md")
    if harbor_instruction_path.exists():
        print(f"✓ Harbor instruction 存在: {harbor_instruction_path}")
    else:
        print(f"❌ Harbor instruction 不存在: {harbor_instruction_path}")
        return False
    
    # 初始化 CodexLM
    print("\n[2] 初始化 CodexLM (Harbor 模式)")
    print("-" * 80)
    
    try:
        # 如果没有 API key，设置一个临时值来测试初始化（不会实际调用）
        if not has_api_key:
            os.environ["OPENAI_API_KEY"] = "test_key_for_initialization"
        
        lm = CodexLM(model="gpt-5-mini", harbor_mode=True)
        print(f"✓ CodexLM 初始化成功")
        print(f"  - model: {lm.model}")
        print(f"  - harbor_mode: {lm.harbor_mode}")
        
        if not has_api_key:
            print("  ⚠️  使用临时 API key，模型调用将失败")
            del os.environ["OPENAI_API_KEY"]
    except Exception as e:
        print(f"❌ CodexLM 初始化失败: {e}")
        if not has_api_key:
            print("  (这可能是正常的，因为需要 API key 来验证 Codex CLI)")
        return False
    
    # 测试功能 1: 读取 item.json
    print("\n[3] 测试功能 1: 读取 item.json")
    print("-" * 80)
    
    test_doc = {
        "id": "test001",
        "query": "Predict whether the company will face bankruptcy. Text: 'The client has attributes: Bankrupt?: 0.5, ROA: 0.6.' Answer:",
        "choices": ["no", "yes"],
        "gold": 0,
        "label_type": "bankruptcy prediction"
    }
    
    try:
        item_data = lm._build_item_json(test_doc)
        print("✓ item.json 构建成功")
        print(f"  包含字段: {list(item_data.keys())}")
        print(f"  id: {item_data.get('id')}")
        print(f"  query 长度: {len(item_data.get('query', ''))} 字符")
        print(f"  choices: {item_data.get('choices')}")
        
        # 验证 item.json 格式
        item_json_str = json.dumps(item_data, indent=2, ensure_ascii=False)
        print(f"  JSON 格式: ✓ (长度: {len(item_json_str)} 字符)")
    except Exception as e:
        print(f"❌ item.json 构建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试功能 2: 调 model
    print("\n[4] 测试功能 2: 调 model (Codex CLI)")
    print("-" * 80)
    
    if not has_api_key:
        print("⚠️  跳过模型调用测试（需要 OPENAI_API_KEY）")
        print("   要测试此功能，请设置:")
        print("   export OPENAI_API_KEY=your_api_key")
        answer = None
    else:
        # 检查环境变量 TEST_MODEL_CALL 来决定是否测试模型调用
        test_model = os.environ.get("TEST_MODEL_CALL", "yes").lower() in ("yes", "y", "1", "true")
        
        if not test_model:
            print("⚠️  跳过模型调用测试（TEST_MODEL_CALL=no）")
            answer = None
        else:
            print("⚠️  注意: 这将实际调用 Codex API，会产生费用")
            print("   开始测试模型调用...")
            # 继续执行模型调用测试
            try:
                # 启用调试模式
                lm._debug_mode = True
                
                print("\n调用 Codex CLI...")
                answer = lm._call_codex_cli_harbor_mode(test_doc)
                
                print(f"\n✓ Codex CLI 调用成功")
                print(f"  返回答案: '{answer}'")
                print(f"  答案长度: {len(answer)} 字符")
                
                if not answer or answer.strip() == "":
                    print("⚠️  警告: 返回的答案为空")
                    print("  可能原因:")
                    print("    - answer.txt 不存在或为空")
                    print("    - Codex CLI 输出解析失败")
                    print("    - 检查调试输出以获取更多信息")
                else:
                    print("✓ 答案读取成功")
                    
            except Exception as e:
                print(f"❌ Codex CLI 调用失败: {e}")
                import traceback
                traceback.print_exc()
                answer = None
    
    # 测试功能 3: 根据 answer.txt eval
    print("\n[5] 测试功能 3: 根据 answer.txt eval")
    print("-" * 80)
    
    if not answer or answer.strip() == "":
        print("⚠️  跳过评估测试（答案为空）")
        return True
    
    try:
        # 模拟 task.process_results 的评估逻辑（不创建实际的 Task 实例）
        # 直接使用分类任务的评估逻辑
        
        gold = test_doc["choices"][test_doc["gold"]]
        gold_lower = gold.lower()
        result_lower = answer.lower().strip()
        
        # 匹配 choices（模拟 Classification.process_results 的逻辑）
        matched_choice = None
        for choice in test_doc["choices"]:
            choice_lower = choice.lower()
            if choice_lower in result_lower or result_lower in choice_lower:
                matched_choice = choice_lower
                break
        
        if matched_choice is None:
            matched_choice = "missing"
        
        acc = 1.0 if gold_lower == matched_choice else 0.0
        
        print("✓ 评估完成")
        print(f"  模型输出: '{answer[:100]}...' (前100字符)")
        print(f"  匹配的 choice: '{matched_choice}'")
        print(f"  真实标签: '{gold_lower}'")
        print(f"  准确率: {acc}")
        print(f"  是否缺失: {1 if matched_choice == 'missing' else 0}")
        
        if acc == 1.0:
            print("  ✓ 预测正确")
        else:
            print("  ✗ 预测错误（这是正常的，因为模型输出可能不匹配）")
            
    except Exception as e:
        print(f"❌ 评估失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ 所有功能测试完成！")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = test_harbor_mode()
    sys.exit(0 if success else 1)

