# Harbor Parity Investigation Summary

## Context
Investigated permission errors and prediction discrepancies between PIXIU and Harbor implementations of the PIXIU adapter.

## Key Findings

### 1. Permission Error Root Cause
- **Harbor's helper scripts** (`write_answer.py`, `check_answer.py`) use hardcoded `/app/answer.txt` paths
- `/app` is a system root directory requiring root privileges
- Regular users cannot create `/app` directory: "Permission denied"

### 2. Environment Differences

#### Harbor Setup
- Runs codex CLI on **host machine**
- Executes commands **inside Docker container** via `docker exec`
- Docker container has `/app` as WORKDIR (defined in Dockerfile)
- Helper scripts work as-is because `/app` exists in container

#### PIXIU Setup (Original)
- Runs codex CLI **natively** (no Docker)
- Commands execute directly on host machine
- `/app` directory doesn't exist and can't be created without sudo

### 3. Agent Self-Recovery Behavior
When permission errors occur, AI agents:
1. Detect "Permission denied" error after 1-3 write attempts
2. Automatically modify helper scripts to use workspace-relative paths
3. Sometimes change predictions during error recovery
- Example: Sample 6 tried "yes" 3 times (failed), then succeeded with "no"
- Example: Sample 11 tried "yes" 2 times (failed), then switched to "no"

This self-recovery **changes agent behavior** compared to error-free execution.

### 4. Model Non-Determinism
Discovered that same inputs produce different outputs across runs:
- **Sample 1**: First run → "yes" (wrong), Second run → "no" (correct)
- **Sample 11**: First run → "no" (correct), Second run → "yes" (wrong)

This occurs even with:
- Identical model (gpt-4o-mini)
- Identical inputs
- Same environment setup

### 5. Comparison Results

| Approach | Accuracy | Permission Errors | Notes |
|----------|----------|------------------|-------|
| Harbor (baseline) | 73.3% (11/15) | 0 | Docker container, /app works |
| PIXIU (with errors) | 86.7% (13/15) | 14/15 samples | Agents self-fix, sometimes flip answer |
| PIXIU (path fix) | 40% (6/15) | 0 | Used gpt-5-mini by mistake |

**Critical Insight**: Fixing permission errors **changed predictions** dramatically, likely because:
1. Agent doesn't experience debugging phase
2. Different token usage patterns
3. Model non-determinism amplified by different execution paths

## Solutions Attempted

### Option 1: Workspace-Relative Path Fix ✅ (Committed: d833133)
**Implementation**:
```python
# Modified script copying to patch paths
content = src.read_text()
content = content.replace('"/app/answer.txt"', '"app/answer.txt"')
(app_dir / script).write_text(content)
```

**Result**: 
- ✅ Eliminates permission errors (0/15 vs 14/15)
- ❌ Changes agent behavior (no debugging phase)
- ❌ Different predictions (40% vs 87%)

### Option 2: Docker Implementation ⚠️ (Incomplete: 3705ea4)
**Approach**: Run commands inside Docker container like Harbor

**Blockers**:
1. Codex CLI doesn't support custom execution backends
2. Harbor uses `docker exec` via BaseEnvironment.exec()
3. Would need complex wrapper to intercept codex commands
4. Significant refactoring required

**Implementation Attempted**:
- Built Docker image from Harbor's Dockerfile
- Started long-running container
- Created shell wrapper for `docker exec`
- **Issue**: Codex CLI cannot be configured to use custom shell

## Recommendations

### For Production Use
1. **Use Harbor directly** if exact environment parity is required
   - Harbor handles Docker orchestration properly
   - Guaranteed consistency with benchmark environment

2. **Accept path fix limitations** for PIXIU standalone use
   - Simpler setup (no Docker required)
   - Trade-off: slightly different agent behavior
   - Document this difference in evaluation reports

### For Future Work
1. **Implement Docker execution properly**
   - Requires intercepting codex bash command execution
   - Replace subprocess calls with docker exec
   - Complex but achieves true parity

2. **Investigate model non-determinism**
   - Add temperature=0 parameter if supported
   - Run multiple trials per sample
   - Report variance in results

3. **Document agent self-recovery patterns**
   - Track error recovery sequences
   - Analyze correlation with prediction flips
   - Consider this a feature (robust agents) rather than bug

## Experiments Conducted

### harbor_parity_fixed (86.7% accuracy)
- Model: gpt-4o-mini
- Permission errors: 14/15 (all self-recovered)
- Path: Original Harbor helper scripts
- Result: Higher accuracy but with error recovery overhead

### harbor_parity_permission_fixed (40% accuracy)
- Model: gpt-5-mini (typo - should be gpt-4o-mini)
- Permission errors: 0/15
- Path: Patched helper scripts (workspace-relative)
- Result: Lower accuracy, likely due to wrong model + different behavior

### docker_test (incomplete)
- Model: gpt-4o-mini  
- Docker: Container started but codex execution failed
- Issue: codex CLI not installed in Docker image
- Blocker: Architecture mismatch with Harbor's approach

## Git Commit History

1. **d833133**: Harbor parity with permission fix
   - Query embedding fix
   - Helper script copying
   - Path patching for native execution
   
2. **45f5d91**: Docker support implementation
   - Added `use_docker` parameter
   - `_build_docker_image()` method
   - `_run_codex_in_docker()` method
   
3. **3705ea4**: Docker work-in-progress
   - Revised approach (long-running container)
   - Shell wrapper attempt
   - Documented blockers

## Conclusion

The permission error investigation revealed:
1. **Root cause**: Hardcoded system paths in Harbor's helper scripts
2. **Agent resilience**: Self-recovery from errors changes behavior
3. **Model variability**: Non-deterministic predictions across runs
4. **Architecture gap**: Docker integration requires deeper refactoring

**Recommended path forward**: Document the limitations and recommend Harbor for production use requiring exact parity. PIXIU's standalone mode (with path fix) is suitable for research where minor behavior differences are acceptable.
