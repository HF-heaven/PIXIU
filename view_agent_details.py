#!/usr/bin/env python3
"""
查看 PIXIU Codex Harbor 模式的 Agent 详细信息

用法:
    python view_agent_details.py <agent_log_dir>
    
示例:
    python view_agent_details.py results/harbor_test/agent_details/agent_taiwan000000
"""

import sys
import json
from pathlib import Path
from typing import Optional


def format_codex_event(event: dict) -> str:
    """格式化 Codex 事件为可读格式"""
    event_type = event.get("type", "unknown")
    
    if event_type == "thread.started":
        return f"Thread started: {event.get('thread_id', 'unknown')}"
    
    elif event_type == "turn.started":
        return "Turn started"
    
    elif event_type == "turn.completed":
        usage = event.get("usage", {})
        return f"Turn completed - Usage: {usage.get('input_tokens', 0)} input tokens, {usage.get('output_tokens', 0)} output tokens"
    
    elif event_type == "item.completed":
        item = event.get("item", {})
        item_type = item.get("type", "unknown")
        item_id = item.get("id", "unknown")
        
        if item_type == "agent_message":
            text = item.get("text", "")
            return f"Agent message ({item_id}): {text[:200]}{'...' if len(text) > 200 else ''}"
        
        elif item_type == "command_execution":
            command = item.get("command", "")
            output = item.get("aggregated_output", "")
            exit_code = item.get("exit_code")
            status = item.get("status", "unknown")
            return f"Command execution ({item_id}):\n  Command: {command[:100]}{'...' if len(command) > 100 else ''}\n  Exit code: {exit_code}\n  Status: {status}\n  Output: {output[:200]}{'...' if len(output) > 200 else ''}"
        
        elif item_type == "reasoning":
            text = item.get("text", "")
            return f"Reasoning ({item_id}): {text[:200]}{'...' if len(text) > 200 else ''}"
        
        else:
            return f"Item completed ({item_id}, type={item_type})"
    
    elif event_type == "item.started":
        item = event.get("item", {})
        item_type = item.get("type", "unknown")
        item_id = item.get("id", "unknown")
        return f"Item started ({item_id}, type={item_type})"
    
    else:
        return f"{event_type}: {str(event)[:100]}..."


def view_agent_details(agent_log_dir: Path):
    """查看 agent 详细信息"""
    
    if not agent_log_dir.exists():
        print(f"❌ Agent log directory not found: {agent_log_dir}")
        return
    
    print("=" * 80)
    print(f"Agent 详细信息: {agent_log_dir}")
    print("=" * 80)
    
    # 1. Command 0 (Auth)
    print("\n[1] Command 0: Create auth.json")
    print("-" * 80)
    cmd0_dir = agent_log_dir / "command-0"
    if cmd0_dir.exists():
        if (cmd0_dir / "command.txt").exists():
            print("Command:")
            print((cmd0_dir / "command.txt").read_text())
        
        if (cmd0_dir / "return-code.txt").exists():
            return_code = (cmd0_dir / "return-code.txt").read_text().strip()
            print(f"Return code: {return_code}")
        
        if (cmd0_dir / "stdout.txt").exists():
            stdout = (cmd0_dir / "stdout.txt").read_text()
            if stdout.strip():
                print(f"Stdout:\n{stdout}")
        
        if (cmd0_dir / "stderr.txt").exists():
            stderr = (cmd0_dir / "stderr.txt").read_text()
            if stderr.strip():
                print(f"Stderr:\n{stderr}")
    else:
        print("Command-0 directory not found")
    
    # 2. Command 1 (Codex Exec)
    print("\n[2] Command 1: Execute Codex CLI")
    print("-" * 80)
    cmd1_dir = agent_log_dir / "command-1"
    if cmd1_dir.exists():
        if (cmd1_dir / "command.txt").exists():
            command = (cmd1_dir / "command.txt").read_text()
            print("Command:")
            # 显示命令的前500字符（instruction 可能很长）
            if len(command) > 500:
                print(command[:500] + "...")
            else:
                print(command)
        
        if (cmd1_dir / "return-code.txt").exists():
            return_code = (cmd1_dir / "return-code.txt").read_text().strip()
            print(f"\nReturn code: {return_code}")
        
        if (cmd1_dir / "stdout.txt").exists():
            stdout = (cmd1_dir / "stdout.txt").read_text()
            print(f"\nStdout length: {len(stdout)} characters")
    else:
        print("Command-1 directory not found")
    
    # 3. Codex Output (JSON events)
    print("\n[3] Codex Output (JSON Events)")
    print("-" * 80)
    codex_file = agent_log_dir / "codex.txt"
    if codex_file.exists():
        codex_output = codex_file.read_text()
        lines = codex_output.strip().split('\n')
        
        print(f"Total events: {len([l for l in lines if l.strip()])}")
        print("\nEvent timeline:")
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                event = json.loads(line)
                formatted = format_codex_event(event)
                print(f"\n[{i}] {formatted}")
            except json.JSONDecodeError:
                print(f"\n[{i}] (Non-JSON line): {line[:100]}...")
    else:
        print("codex.txt not found")
    
    # 4. Extract key information
    print("\n[4] 关键信息提取")
    print("-" * 80)
    
    if codex_file.exists():
        codex_output = codex_file.read_text()
        
        # Extract final answer
        final_answer = None
        for line in reversed(codex_output.strip().split('\n')):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        text = item.get("text", "")
                        # Check if it looks like a final answer
                        if text.lower().strip() in ["yes", "no", "positive", "negative"] or len(text.strip()) < 10:
                            final_answer = text.strip()
                            break
            except:
                continue
        
        if final_answer:
            print(f"最终答案: '{final_answer}'")
        else:
            print("未找到明确的最终答案")
        
        # Extract usage
        for line in reversed(codex_output.strip().split('\n')):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get("type") == "turn.completed":
                    usage = event.get("usage", {})
                    print(f"Token 使用:")
                    print(f"  Input tokens: {usage.get('input_tokens', 0)}")
                    print(f"  Cached input tokens: {usage.get('cached_input_tokens', 0)}")
                    print(f"  Output tokens: {usage.get('output_tokens', 0)}")
                    break
            except:
                continue
    
    print("\n" + "=" * 80)


def main():
    if len(sys.argv) < 2:
        print("用法: python view_agent_details.py <agent_log_dir>")
        print("\n示例:")
        print("  python view_agent_details.py results/harbor_test/agent_details/agent_taiwan000000")
        sys.exit(1)
    
    agent_log_dir = Path(sys.argv[1])
    view_agent_details(agent_log_dir)


if __name__ == "__main__":
    main()

