#!/usr/bin/env python3
"""Simple test script for CodexLM in pixiu_env conda environment."""

import sys
import os

# Add paths
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/financial-evaluation')

# Set API key
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', 'Your OpenAI API key')

try:
    from codexlm import CodexLM
    print("✓ CodexLM imported successfully")
    
    lm = CodexLM(model='gpt-4o')
    print("✓ CodexLM initialized successfully")
    print(f"  Model: {lm.model}")
    
    tokenizer_status = 'fallback' if lm.tokenizer == 'fallback' else 'loaded'
    print(f"  Tokenizer: {tokenizer_status}")
    
    # Test a simple Codex CLI call
    print("\nTesting Codex CLI call...")
    test_output = lm._call_codex_cli("echo 'Hello from Codex'")
    print(f"✓ Codex CLI call successful")
    print(f"  Output preview: {test_output[:100]}...")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== All tests passed! ===")

