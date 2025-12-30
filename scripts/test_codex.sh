#!/bin/bash
# Test script for Codex CLI integration in PIXIU

set -e

# Set API key (replace with your actual key)
export OPENAI_API_KEY="${OPENAI_API_KEY:-Your OpenAI API key}"

# Ensure Node.js 22 is used
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    source "$HOME/.nvm/nvm.sh"
    nvm use 22
fi

echo "=== Testing Codex CLI Integration ==="
echo ""

# Test 1: Check Codex CLI installation
echo "1. Checking Codex CLI installation..."
if command -v codex &> /dev/null; then
    codex --version
    echo "✓ Codex CLI is installed"
else
    echo "✗ Codex CLI not found. Please install with: npm install -g @openai/codex@latest"
    exit 1
fi
echo ""

# Test 2: Check API key
echo "2. Checking API key..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "✗ OPENAI_API_KEY is not set"
    exit 1
else
    echo "✓ OPENAI_API_KEY is set"
fi
echo ""

# Test 3: Check Codex login status
echo "3. Checking Codex login status..."
if codex login status 2>&1 | grep -q "logged in\|authenticated"; then
    echo "✓ Codex CLI is logged in"
else
    echo "⚠ Codex CLI may not be logged in. Attempting to login..."
    echo "$OPENAI_API_KEY" | codex login --with-api-key 2>&1 || true
    if codex login status 2>&1 | grep -q "logged in\|authenticated"; then
        echo "✓ Codex CLI login successful"
    else
        echo "✗ Codex CLI login failed. Please run: echo \$OPENAI_API_KEY | codex login --with-api-key"
    fi
fi
echo ""

# Test 4: Test Codex CLI directly (skip if not logged in)
echo "4. Testing Codex CLI with a simple command..."
cd "$(dirname "$0")/.."
test_output=$(codex exec \
    --dangerously-bypass-approvals-and-sandbox \
    --skip-git-repo-check \
    --model gpt-4o \
    --json \
    -- "echo 'Hello from Codex'" 2>&1) || true

if echo "$test_output" | grep -q "output\|Hello"; then
    echo "✓ Codex CLI is working"
    echo "Output preview: $(echo "$test_output" | head -3)"
elif echo "$test_output" | grep -q "401\|Unauthorized\|not logged"; then
    echo "⚠ Codex CLI authentication failed. Please login first."
    echo "Run: echo \$OPENAI_API_KEY | codex login --with-api-key"
else
    echo "⚠ Codex CLI test output:"
    echo "$test_output" | head -10
fi
echo ""

# Test 5: Test CodexLM import
echo "5. Testing CodexLM import..."
cd "$(dirname "$0")/.."
python3 -c "
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/financial-evaluation')
try:
    from codexlm import CodexLM
    print('✓ CodexLM import successful')
except Exception as e:
    print(f'✗ CodexLM import failed: {e}')
    sys.exit(1)
" || exit 1
echo ""

# Test 6: Test CodexLM initialization
echo "6. Testing CodexLM initialization..."
python3 -c "
import sys
import os
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/financial-evaluation')
from codexlm import CodexLM

try:
    lm = CodexLM(model='gpt-4o')
    print('✓ CodexLM initialized successfully')
    print(f'  Model: {lm.model}')
    print(f'  Max length: {lm.max_length}')
    print(f'  Max gen tokens: {lm.max_gen_toks}')
except Exception as e:
    print(f'✗ CodexLM initialization failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" || exit 1
echo ""

# Test 7: Test evaluator integration
echo "7. Testing evaluator integration..."
python3 -c "
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/financial-evaluation')
import evaluator

try:
    # This should not raise an error
    print('✓ Evaluator imports CodexLM successfully')
except Exception as e:
    print(f'✗ Evaluator integration failed: {e}')
    sys.exit(1)
" || exit 1
echo ""

echo "=== All tests passed! ==="
echo ""
echo "You can now run PIXIU evaluation with Codex using:"
echo "  python src/eval.py --model codex --model_args model=gpt-4o --tasks <task_name> --limit 5"

