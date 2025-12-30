#!/usr/bin/env python3
"""Test script to verify Codex output extraction is working correctly."""

import sys
import os
import json

sys.path.insert(0, 'src')
sys.path.insert(0, 'src/financial-evaluation')

os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', 'Your OpenAI API key')

from codexlm import CodexLM

print("=" * 60)
print("Testing Codex Output Extraction")
print("=" * 60)

lm = CodexLM(model='gpt-4o')

# Test with a simple prompt
test_prompt = "Answer Yes or No: Is 2+2 equal to 4?"
print(f"\nTest Prompt: {test_prompt}")

try:
    output = lm._call_codex_cli(test_prompt)
    print(f"\n✓ Extracted Output: {repr(output)}")
    print(f"  Length: {len(output)}")
    print(f"  Type: {type(output).__name__}")
    
    # Check if it's the metadata JSON
    if output.startswith('{"type"') and "turn.completed" in output:
        print("\n✗ ERROR: Still extracting metadata instead of actual output!")
        print("  This means the parsing logic needs to be fixed.")
    else:
        print("\n✓ SUCCESS: Extracted actual output, not metadata!")
    
    # Show raw output structure
    if hasattr(lm, '_last_raw_output') and lm._last_raw_output:
        print(f"\nRaw Output Structure:")
        lines = lm._last_raw_output.strip().split('\n')
        for i, line in enumerate(lines[:5]):
            if line.strip():
                try:
                    parsed = json.loads(line)
                    msg_type = parsed.get('type', 'unknown')
                    if msg_type == 'item.completed':
                        item_text = parsed.get('item', {}).get('text', 'N/A')
                        print(f"  Line {i}: {msg_type} -> text: {repr(item_text)}")
                    else:
                        print(f"  Line {i}: {msg_type}")
                except:
                    print(f"  Line {i}: {line[:80]}...")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)

