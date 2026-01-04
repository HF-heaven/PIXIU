# Answer Extraction Fix Documentation

## Problem Summary

When running harbor mode evaluations on the Taiwan dataset (limit=15), we discovered two critical issues with answer extraction:

### Issue 1: Agent File Writing Bug
**Symptoms:**
- Some agents said they wrote "yes" in logit_0, but pred showed "no" (docs 6, 8, 10)
- Some predictions were "missing" (docs 2, 5, 12)

**Root Cause:**
Agents were incorrectly quoting the redirect operator when writing to `app/answer.txt`:
```bash
# What agents ran (WRONG):
echo yes ' >' app/answer.txt

# What they should run (CORRECT):
echo "yes" > app/answer.txt
```

The quoted `' >'` was treated as a literal string to echo, not a redirect operator, so:
- The answer was printed to stdout instead of being written to the file
- `app/answer.txt` was never created
- The fallback parser extracted answers from agent messages, which didn't always match

### Issue 2: Insufficient Fallback Parser
**Symptoms:**
- When `app/answer.txt` wasn't created, the parser extracted the full agent message
- Example: "I've analyzed...the best label is `yes`..." instead of just "yes"
- This caused mismatches between what agents said and what was extracted

**Root Cause:**
The original fallback parser in `_parse_codex_output_from_stdout()` returned the full agent message text without attempting to extract the simple yes/no answer.

---

## Solution

### Fix 1: Improved Instruction Template
**File:** `/home/hefan/PIXIU/src/codexlm.py` lines 137-148

**Change:** Added explicit command examples to the instruction:
```python
- Write your final answer as plain text to `/app/answer.txt`. Use one of these commands:
  * `echo "your_answer" > /app/answer.txt` (recommended)
  * `printf "your_answer" > /app/answer.txt`
  * `cat > /app/answer.txt <<< "your_answer"`
```

**Rationale:** Providing explicit command syntax reduces ambiguity and helps agents write correctly.

### Fix 2: Robust Regex-Based Fallback Parser
**File:** `/home/hefan/PIXIU/src/codexlm.py` lines 390-460

**Change:** Added intelligent regex patterns to extract yes/no from agent messages when `answer.txt` doesn't exist:

```python
# Pattern 1: "answer is **yes**" or "label is **no**"
match = re.search(r'\b(?:answer|label|result|prediction)\s+(?:is|determined|saved as)\s+(?:\*\*)?["`]?(yes|no)["`]?(?:\*\*)?', text, re.IGNORECASE)

# Pattern 2: "written to...as **yes**"
match = re.search(r'\b(?:written|saved|stored)\s+(?:to|as)\s+.*?(?:\*\*)?["`]?(yes|no)["`]?(?:\*\*)?', text, re.IGNORECASE)

# Pattern 3: quoted yes/no anywhere
match = re.search(r'["`\*]+(yes|no)["`\*]+', text, re.IGNORECASE)
```

**Rationale:** These patterns can extract simple yes/no answers from various agent message formats, making the system resilient to agent mistakes.

---

## Verification

### Test Results (limit=3)
```bash
cd /home/hefan/PIXIU
PYTHONPATH=/home/hefan/PIXIU/src/financial-evaluation:$PYTHONPATH \
python src/eval.py \
    --model codex \
    --model_args "model=gpt-4o-mini,harbor_mode=True" \
    --tasks flare_cra_taiwan \
    --limit 3 \
    --write_out \
    --output_base_path results/test_fix \
    --no_cache
```

**Results:**
- **Accuracy: 100%** (3/3 correct)
- **Missing: 0** (no failed extractions)
- **F1: 1.0**, **MCC: 1.0**

| doc_id | truth | pred | correct? |
|--------|-------|------|----------|
| 0      | yes   | yes  | ✅       |
| 1      | yes   | yes  | ✅       |
| 2      | no    | no   | ✅       |

**Note:** Even though `app/answer.txt` files were **not created** (agents still made the same mistakes), the improved regex parser successfully extracted correct answers from agent messages.

---

## Comparison: Before vs After

### Before Fix (test_run with limit=15):
- **Accuracy: 33.3%** (5/15 correct)
- **Missing: 20%** (3/15 failed)
- **Issues:** Agents misquoted redirects, parser extracted full messages

### After Fix (test_fix with limit=3):
- **Accuracy: 100%** (3/3 correct)
- **Missing: 0%** (0/3 failed)
- **Improvement:** Regex parser extracts answers despite agent mistakes

---

## Code Changes

### 1. codexlm.py (Instruction Template)
**Lines 137-148:**
```python
# Added explicit command examples
- Write your final answer as plain text to `/app/answer.txt`. Use one of these commands:
  * `echo "your_answer" > /app/answer.txt` (recommended)
  * `printf "your_answer" > /app/answer.txt`
  * `cat > /app/answer.txt <<< "your_answer"`
```

### 2. codexlm.py (Fallback Parser)
**Lines 390-460:**
```python
# Added regex-based extraction
if actual_output:
    import re
    # Pattern 1: "answer is **yes**"
    match = re.search(r'\b(?:answer|label|result|prediction)\s+(?:is|determined|saved as)\s+(?:\*\*)?["`]?(yes|no)["`]?(?:\*\*)?', actual_output, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    
    # Pattern 2: "written to...as **yes**"
    match = re.search(r'\b(?:written|saved|stored)\s+(?:to|as)\s+.*?(?:\*\*)?["`]?(yes|no)["`]?(?:\*\*)?', actual_output, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    
    # Pattern 3: quoted yes/no
    match = re.search(r'["`\*]+(yes|no)["`\*]+', actual_output, re.IGNORECASE)
    if match:
        return match.group(1).lower()
```

---

## Next Steps

1. **Re-run Full Dataset:** Test with limit=15 or full dataset to verify sustained improvement
2. **Monitor Agent Behavior:** Check if newer model versions fix the redirect quoting issue
3. **Consider Additional Patterns:** If new agent message formats appear, add more regex patterns
4. **Git Commit:** Tag this fix as `v0.3.0-answer-extraction-fix`

---

## Related Files

- Source Code: [src/codexlm.py](src/codexlm.py)
- Test Results: [results/test_fix/](results/test_fix/)
- Previous Documentation: [PIXIU_HARBOR_MODE_EXECUTION_FLOW.md](PIXIU_HARBOR_MODE_EXECUTION_FLOW.md)
