#!/usr/bin/env python3
"""Quick test of the harbor mode fix"""
import json
import subprocess
import sys
from pathlib import Path
import uuid
import os

# Test data - simple taiwan bankruptcy prediction
test_doc = {
    "id": 0,
    "query": "Predict whether the company will face bankruptcy. Respond with only 'no' or 'yes'. Text: 'ROA: 0.5, Debt ratio: 20%'",
    "choices": ["no", "yes"],
    "gold": 0  # "no"
}

def test_harbor_mode_fix():
    """Test if codex agent can now access files with --cd flag"""
    # Create temp directory structure
    temp_dir = Path(f"/tmp/pixiu_codex_test_{uuid.uuid4().hex}")
    app_dir = temp_dir / "app"
    data_dir = temp_dir / "tests" / "data"
    app_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Write item.json
        item_data = {
            "id": test_doc["id"],
            "query": test_doc["query"],
            "choices": test_doc["choices"],
            "dataset": "pixiu",
            "split": "test"
        }
        (data_dir / "item.json").write_text(json.dumps(item_data, indent=2))
        
        # Harbor instruction (modified for --cd: use relative paths instead of absolute)
        instruction = """You are given a financial task instance in `tests/data/item.json`.

- Read the JSON file at `tests/data/item.json` to understand the query and available choices.
- Decide on the single best label according to the task description.
- Write your final answer as plain text to `app/answer.txt`.

Your answer must exactly match one of the allowed labels."""
        
        # Execute codex with --cd flag
        cmd = [
            "codex", "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--cd", str(temp_dir),  # THIS IS THE FIX
            "--model", "gpt-4o-mini",
            "--json",
            "--",
            instruction
        ]
        
        print(f"Testing harbor mode fix...")
        print(f"Temp dir: {temp_dir}")
        print(f"Command: {' '.join(cmd[:8])} ...")
        print(f"\nExecuting codex...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=120
        )
        
        if result.returncode != 0:
            print(f"❌ Codex failed with return code {result.returncode}")
            print(f"Stderr: {result.stderr[:500]}")
            return False
        
        # Print codex output for debugging
        print(f"\n--- Codex Output (first 2000 chars) ---")
        print(result.stdout[:2000])
        print(f"--- End Output ---\n")
        
        # Check if answer.txt was created
        answer_file = app_dir / "answer.txt"
        if not answer_file.exists():
            print(f"❌ answer.txt was not created at {answer_file}")
            return False
        
        answer = answer_file.read_text().strip()
        print(f"\n✅ Answer file created successfully!")
        print(f"Answer: '{answer}'")
        
        # Parse codex output to see if it accessed the file
        output_lines = result.stdout.strip().split('\n')
        found_item_read = False
        found_answer_write = False
        
        for line in output_lines:
            try:
                parsed = json.loads(line)
                if parsed.get("type") == "item.completed":
                    item = parsed.get("item", {})
                    cmd_text = item.get("command", "")
                    if "item.json" in cmd_text:
                        found_item_read = True
                        print(f"✅ Agent read item.json")
                    if "answer.txt" in cmd_text:
                        found_answer_write = True
                        print(f"✅ Agent wrote answer.txt")
            except:
                pass
        
        if not found_item_read:
            print(f"⚠️  Could not confirm agent read item.json from logs")
        if not found_answer_write:
            print(f"⚠️  Could not confirm agent wrote answer.txt from logs")
        
        # Check if answer is valid
        if answer in test_doc["choices"]:
            print(f"✅ Answer is valid (one of {test_doc['choices']})")
            return True
        else:
            print(f"❌ Answer '{answer}' is not one of valid choices {test_doc['choices']}")
            return False
            
    finally:
        # Cleanup
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temp directory")

if __name__ == "__main__":
    success = test_harbor_mode_fix()
    sys.exit(0 if success else 1)
