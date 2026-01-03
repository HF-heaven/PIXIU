#!/usr/bin/env python3
"""Test taiwan dataset with fixed harbor mode"""
import json
import subprocess
import sys
from pathlib import Path
import uuid
import os

def load_harbor_instruction():
    """Load Harbor instruction template with relative paths."""
    return """You are given a financial task instance in `tests/data/item.json`.

- Read the JSON file at `tests/data/item.json` to understand the query and available choices.
- Decide on the single best label according to the task description.
- Write your final answer as plain text to `app/answer.txt`.

Your answer must exactly match one of the allowed labels."""

def test_taiwan_sample(sample_id, query, gold_label, choices=["no", "yes"]):
    """Test a single taiwan sample"""
    # Create temp directory structure
    temp_dir = Path(f"/tmp/pixiu_taiwan_test_{uuid.uuid4().hex}")
    app_dir = temp_dir / "app"
    data_dir = temp_dir / "tests" / "data"
    app_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create agent log directory
    agent_log_dir = Path(f"results/taiwan_fix_test/agent_{sample_id}")
    agent_log_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Write item.json
        item_data = {
            "id": sample_id,
            "query": query,
            "choices": choices,
            "dataset": "pixiu",
            "split": "test"
        }
        (data_dir / "item.json").write_text(json.dumps(item_data, indent=2))
        
        # Get instruction
        instruction = load_harbor_instruction()
        
        # Execute codex with --cd flag (THE FIX)
        cmd = [
            "codex", "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "--cd", str(temp_dir),
            "--model", "gpt-4o-mini",
            "--json",
            "--",
            instruction
        ]
        
        print(f"Executing codex for sample {sample_id}...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            timeout=180
        )
        
        # Save agent logs
        (agent_log_dir / "codex.txt").write_text(result.stdout)
        (agent_log_dir / "command.txt").write_text(" ".join(cmd))
        if result.stderr:
            (agent_log_dir / "stderr.txt").write_text(result.stderr)
        
        if result.returncode != 0:
            print(f"❌ Codex failed with return code {result.returncode}")
            return None, False
        
        # Read answer
        answer_file = app_dir / "answer.txt"
        if answer_file.exists():
            prediction = answer_file.read_text().strip()
        else:
            # Parse from codex output as fallback
            prediction = None
            for line in result.stdout.strip().split('\n'):
                try:
                    parsed = json.loads(line)
                    if parsed.get("type") == "item.completed":
                        item = parsed.get("item", {})
                        if item.get("type") == "agent_message":
                            text = item.get("text", "")
                            # Try to extract answer from text
                            for choice in choices:
                                if choice in text.lower():
                                    prediction = choice
                                    break
                except:
                    pass
        
        if prediction:
            correct = (prediction == gold_label)
            return prediction, correct
        else:
            return None, False
            
    finally:
        # Cleanup temp dir
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def main():
    print("Testing Taiwan dataset with fixed harbor mode")
    print("="*60)
    
    # Load taiwan dataset
    from datasets import load_dataset
    dataset = load_dataset("TheFinAI/cra-taiwan", split="test")
    
    results = []
    for i in range(2):  # Test 2 samples
        sample = dataset[i]
        
        # Use the query from dataset directly
        query = sample['query']
        gold_label = sample['choices'][sample['gold']]  # Get label from choices using gold index
        
        print(f"\n{'='*60}")
        print(f"Sample {i}")
        print(f"{'='*60}")
        print(f"Gold label: {gold_label}")
        
        prediction, correct = test_taiwan_sample(i, query, gold_label)
        
        if prediction:
            print(f"✅ Prediction: '{prediction}'")
            print(f"   Result: {'✓ CORRECT' if correct else '✗ WRONG'}")
        else:
            print(f"❌ Failed to get prediction")
            correct = False
        
        results.append({
            "sample_id": i,
            "prediction": prediction,
            "gold": gold_label,
            "correct": correct
        })
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    correct_count = sum(1 for r in results if r.get("correct", False))
    total = len(results)
    print(f"Accuracy: {correct_count}/{total} = {correct_count/total*100:.1f}%")
    print(f"\nAgent logs saved to: results/taiwan_fix_test/")
    
    return results

if __name__ == "__main__":
    results = main()
