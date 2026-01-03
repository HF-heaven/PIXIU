# Truth Label Mismatch Investigation

## Issue Reported
User found that truth labels in two different result files don't match:
- `/home/hefan/PIXIU/results/harbor_test/flare_cra_taiwan_write_out_info.json` - First 2 samples have truth="yes"
- `/home/hefan/PIXIU/results/harbor_all_tasks_codex_gpt-5-mini_noshuffle/cra-taiwan/taiwan_write_out_info.json` - First 2 samples have truth="no"

## Investigation Results

### Root Cause #1: Different Dataset Samples
The two result files are using **different samples from the dataset**:

**harbor_test Sample 0:**
- Bankrupt? attribute: 0.371
- Actual dataset index: 0
- Truth: "yes" ✅ CORRECT

**harbor_all_tasks Sample 0:**
- Bankrupt? attribute: 0.513  
- Actual dataset index: 12
- Truth: "no" ✅ CORRECT (for sample 12)

**Conclusion:** Both files have correct truth labels, but they're evaluating different samples. The harbor_all_tasks results appear to be using a shuffled or differently ordered version of the dataset, despite the path name containing "noshuffle".

### Root Cause #2: Gold Index vs Label String Issue (FIXED)
Found a bug in [src/evaluator.py](src/evaluator.py#L433) where for MultipleChoiceTask, the code was storing the raw gold index instead of converting it to the label string:

**Before (Line 433):**
```python
if isinstance(task, lm_eval.base.MultipleChoiceTask):
    write_out_info[task_name][doc_id]["truth"] = doc["gold"]  # BUG: This is an index (0 or 1)
```

**After (Fixed):**
```python
if isinstance(task, lm_eval.base.MultipleChoiceTask):
    # Convert gold index to actual label string for MultipleChoiceTask
    if "choices" in doc and isinstance(doc["gold"], int):
        write_out_info[task_name][doc_id]["truth"] = doc["choices"][doc["gold"]]
    else:
        write_out_info[task_name][doc_id]["truth"] = doc["gold"]
```

## Verification

**Actual Taiwan Dataset (TheFinAI/cra-taiwan test split):**
- Sample 0: gold=1 → "yes"
- Sample 1: gold=1 → "yes"  
- Sample 12: gold=0 → "no"

**harbor_test results:**
- Sample 0: truth="yes" ✅ Matches dataset index 0
- Sample 1: truth="yes" ✅ Matches dataset index 1

**harbor_all_tasks results:**
- Sample 0: truth="no" ✅ Matches dataset index 12 (shuffled)
- Sample 1: truth=? (would need to verify which original index)

## Fix Applied

Committed fix to [src/evaluator.py](src/evaluator.py#L429-L437) that ensures truth labels are always stored as label strings, not indices, for MultipleChoiceTask types.

## Recommendation

For future runs, ensure dataset ordering is consistent:
1. Check if shuffle is intended or accidental
2. Consider setting a fixed random seed if shuffling is needed
3. Save dataset indices in results for traceability
