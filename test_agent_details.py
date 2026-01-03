#!/usr/bin/env python3
"""
测试 PIXIU Codex Harbor 模式的 agent 详细信息保存功能
"""

import sys
import os
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from codexlm import CodexLM
import json

def test_agent_details_saving():
    """测试 agent 详细信息保存功能"""
    
    print("=" * 80)
    print("PIXIU Codex Harbor 模式 - Agent 详细信息保存测试")
    print("=" * 80)
    
    # 检查环境
    if "OPENAI_API_KEY" not in os.environ:
        print("❌ OPENAI_API_KEY 环境变量未设置")
        return False
    
    # 创建测试输出目录
    test_output_dir = Path("/tmp/pixiu_agent_test")
    test_output_dir.mkdir(exist_ok=True)
    
    # 初始化 CodexLM
    print("\n[1] 初始化 CodexLM (Harbor 模式 + Agent 详细信息)")
    print("-" * 80)
    
    try:
        lm = CodexLM(model="gpt-5-mini", harbor_mode=True)
        lm._save_agent_details = True
        lm._agent_log_base_dir = str(test_output_dir)
        print(f"✓ CodexLM 初始化成功")
        print(f"  - model: {lm.model}")
        print(f"  - harbor_mode: {lm.harbor_mode}")
        print(f"  - _save_agent_details: {lm._save_agent_details}")
        print(f"  - _agent_log_base_dir: {lm._agent_log_base_dir}")
    except Exception as e:
        print(f"❌ CodexLM 初始化失败: {e}")
        return False
    
    # 测试数据
    test_doc = {
        "id": "test_agent_details",
        "query": "Predict whether the company will face bankruptcy. Text: 'The client has attributes: Bankrupt?: 0.5, ROA: 0.6.' Answer:",
        "choices": ["no", "yes"],
        "gold": 0
    }
    
    print("\n[2] 调用 Codex CLI (将保存 agent 详细信息)")
    print("-" * 80)
    print("⚠️  注意: 这将实际调用 Codex API，会产生费用")
    
    user_input = os.environ.get("TEST_MODEL_CALL", "no").lower()
    if user_input not in ("yes", "y", "1", "true"):
        print("跳过模型调用测试（设置 TEST_MODEL_CALL=yes 来测试）")
        return True
    
    try:
        lm._debug_mode = True
        doc_id = test_doc.get('id', 'test')
        agent_log_dir = Path(lm._agent_log_base_dir) / f"agent_{doc_id}"
        
        print(f"\n调用 Codex CLI...")
        print(f"Agent 详细信息将保存到: {agent_log_dir}")
        
        answer = lm._call_codex_cli_harbor_mode(
            test_doc,
            save_agent_details=True,
            agent_log_dir=agent_log_dir
        )
        
        print(f"\n✓ Codex CLI 调用成功")
        print(f"  返回答案: '{answer}'")
        
        # 检查保存的文件
        print("\n[3] 检查保存的 Agent 详细信息")
        print("-" * 80)
        
        expected_files = [
            agent_log_dir / "command-0" / "command.txt",
            agent_log_dir / "command-0" / "return-code.txt",
            agent_log_dir / "command-0" / "stdout.txt",
            agent_log_dir / "command-1" / "command.txt",
            agent_log_dir / "command-1" / "return-code.txt",
            agent_log_dir / "command-1" / "stdout.txt",
            agent_log_dir / "codex.txt",
        ]
        
        all_exist = True
        for file_path in expected_files:
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"✓ {file_path.relative_to(test_output_dir)} ({size} bytes)")
            else:
                print(f"✗ {file_path.relative_to(test_output_dir)} 不存在")
                all_exist = False
        
        if all_exist:
            print("\n✓ 所有 Agent 详细信息文件都已保存")
            
            # 显示一些内容
            print("\n[4] 查看 Agent 详细信息内容")
            print("-" * 80)
            
            # command-0
            print("\nCommand 0 (Auth):")
            print((agent_log_dir / "command-0" / "command.txt").read_text()[:200])
            
            # command-1
            print("\nCommand 1 (Codex Exec):")
            cmd = (agent_log_dir / "command-1" / "command.txt").read_text()
            print(cmd[:300] + "..." if len(cmd) > 300 else cmd)
            
            # codex.txt (前几行)
            print("\nCodex Output (前3行):")
            codex_output = (agent_log_dir / "codex.txt").read_text()
            lines = codex_output.strip().split('\n')[:3]
            for line in lines:
                if line.strip():
                    try:
                        event = json.loads(line)
                        event_type = event.get("type", "unknown")
                        print(f"  {event_type}: {str(event)[:100]}...")
                    except:
                        print(f"  {line[:100]}...")
            
            print(f"\n✓ Agent 详细信息查看完成")
            print(f"\n完整文件位置: {agent_log_dir}")
        else:
            print("\n⚠️  部分文件缺失")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 80)
    print("✅ Agent 详细信息保存功能测试完成！")
    print("=" * 80)
    
    return True

if __name__ == "__main__":
    success = test_agent_details_saving()
    sys.exit(0 if success else 1)

