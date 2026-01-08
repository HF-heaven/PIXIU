# Codex Evaluation Script - README

This README explains how to run `run_harbor_tasks_docker.sh`, which evaluates all Harbor tasks using Codex CLI with Docker mode.

## Overview

The script runs evaluation on 29 PIXIU tasks using Codex CLI with GPT-5-mini model in Harbor mode. Each task is evaluated on the first 15 samples with Docker containerization for consistency.

## Prerequisites

### 1. Node.js and NVM

Install NVM (Node Version Manager) if not already installed:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts
```

### 2. Codex CLI

Install Codex CLI via npm:

```bash
npm install -g @openai/codex@latest
```

Verify installation:

```bash
codex --version
```

### 3. Conda Environment

Create and activate the conda environment:

```bash
# Create conda environment
conda create -n pixiu_env python=3.10
conda activate pixiu_env

# Install dependencies
pip install -r requirements_codex.txt

# Install local packages
cd src/financial-evaluation
pip install -e .
cd ../..

# Download NLTK data (if needed)
python -c "import nltk; nltk.download('punkt')"
```

**Note**: Use `requirements_codex.txt` instead of `requirements.txt` as it contains only the dependencies needed for Codex evaluation, excluding optional packages like `vllm` and `gradio`.

### 4. Docker

Install Docker and ensure it's running:

```bash
docker --version
docker ps  # Should not return an error
```

## Configuration

### 1. API Key Setup

Before running the script, you need to set up your OpenAI API key. There are two ways:

**Option 1: Edit the script (not recommended for production)**

Edit `run_harbor_tasks_docker.sh` and replace line 16:

```bash
export OPENAI_API_KEY="Your OpenAI API key"
```

**Option 2: Use environment variable (recommended)**

Set the API key in your shell:

```bash
export OPENAI_API_KEY="sk-proj-..."
```

Or add it to your `~/.bashrc` or `~/.zshrc`:

```bash
echo 'export OPENAI_API_KEY="sk-proj-..."' >> ~/.bashrc
source ~/.bashrc
```

### 2. Script Path Configuration

If your project is located in a different directory, update line 22 in `run_harbor_tasks_docker.sh`:

```bash
cd /path/to/your/PIXIU
```

Alternatively, modify the script to use a relative path or `$PWD`.

## Running the Script

### Basic Usage

```bash
cd /home/hefan/PIXIU
bash run_harbor_tasks_docker.sh
```

Or make it executable and run directly:

```bash
chmod +x run_harbor_tasks_docker.sh
./run_harbor_tasks_docker.sh
```

### What the Script Does

1. Sets up environment (nvm, conda, PYTHONPATH)
2. Iterates through 29 tasks
3. For each task:
   - Creates output directory
   - Runs evaluation with Codex CLI in Docker mode
   - Saves results to JSON file
   - Continues to next task even if one fails

### Configuration Options

You can modify these variables in the script:

- **`OUTPUT_BASE_DIR`** (line 27): Base directory for all outputs
  - Default: `results/harbor_test_docker`
  
- **`LIMIT`** (line 28): Number of samples per task
  - Default: `15`
  
- **`TASKS`** (lines 64-94): List of tasks to run
  - Comment out tasks you don't want to run

## Output Structure

### Directory Layout

```
results/harbor_test_docker/
├── en-fpb/
│   ├── results.json
│   ├── flare_fpb_write_out_info.json
│   └── agent_details/
│       ├── agent_0/
│       │   ├── codex.txt
│       │   └── command-*/...
│       └── ...
├── flare-headlines/
│   └── ...
└── ...
```

### Output Files

**1. `results.json`** - Main evaluation results
   - Contains aggregated metrics (accuracy, F1, MCC, etc.)
   - Format: `{"results": {"task_name": {...metrics...}}}`

**2. `{task_name}_write_out_info.json`** - Detailed per-sample results
   - Contains predictions, ground truth, and logits for each sample
   - Format: Array of objects with `doc_id`, `prompt_0`, `logit_0`, `truth`, `pred`, etc.

**3. `agent_details/agent_{doc_id}/`** - Agent execution logs
   - `codex.txt`: Full agent interaction log
   - `command-*/`: Individual command execution logs

### Example Output Files

**`results.json`**:
```json
{
  "results": {
    "flare_fpb": {
      "acc": 0.7333,
      "acc_stderr": 0.1182,
      "f1": 0.8462,
      "macro_f1": 0.8462,
      "mcc": 0.0,
      "missing": 0.0
    }
  },
  "config": {
    "model": "codex",
    "model_args": "model=gpt-5-mini,harbor_mode=True",
    "limit": 15.0
  }
}
```

## Tasks Evaluated

The script evaluates 29 tasks:

- Classification (18 tasks): en-fpb, flare-headlines, flare-ner, flare-causal20-sc, flare-fiqasa, finben-fomc, flare-cfa, flare-german, cra-ccfraud, flare-australian, cra-ccf, taiwan, en-forecasting-travelinsurance, flare-mlesg, flare-ma, flare-multifin-en, flare-sm-acl, flare-sm-bigdata, flare-sm-cikm
- Regression (1 task): flare-tsa
- Text Generation (2 tasks): flare-finqa, flare-tatqa
- Sequence Labeling (3 tasks): flare-fnxl, flare-ner, finben-finer-ord
- Relation Extraction (3 tasks): flare-finred, flare-cd, flare-fsrl
- Summarization (2 tasks): flare-ectsum, flare-edtsum

## Troubleshooting

### 1. Codex CLI Not Found

**Error**: `codex: command not found`

**Solution**:
```bash
# Check if nvm is loaded
source ~/.nvm/nvm.sh

# Verify Codex CLI is installed
which codex

# If not found, reinstall
npm install -g @openai/codex@latest
```

### 2. Conda Environment Not Activated

**Error**: `conda: command not found` or `pixiu_env not found`

**Solution**:
```bash
# Initialize conda
source ~/anaconda3/etc/profile.d/conda.sh

# Activate environment
conda activate pixiu_env
```

### 3. Docker Not Running

**Error**: `Cannot connect to Docker daemon`

**Solution**:
```bash
# Start Docker service
sudo systemctl start docker

# Verify Docker is running
docker ps
```

### 4. API Key Issues

**Error**: Authentication errors or API key not found

**Solution**:
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test Codex CLI authentication
codex login status

# If not logged in, set API key
echo $OPENAI_API_KEY | codex login --with-api-key
```

### 5. Import Errors

**Error**: `ModuleNotFoundError: No module named 'lm_eval'`

**Solution**: The script should automatically set PYTHONPATH. If this error occurs:
```bash
# Manually set PYTHONPATH
export PYTHONPATH="$PWD:$PWD/src:$PWD/src/financial-evaluation:$PWD/src/metrics/BARTScore:$PYTHONPATH"

# Verify Python can find modules
python -c "from lm_eval import utils; print('OK')"
```

### 6. Task Fails

If a specific task fails, the script will:
- Print a warning message
- Continue to the next task
- Not stop the entire run

Check the task output directory for error logs:
```bash
cat results/harbor_test_docker/{task_name}/agent_details/agent_*/codex.txt
```

## Time Estimates

- Each task typically takes 2-3 minutes
- Total runtime for all 29 tasks: ~60-90 minutes (depending on API response time)
- With `LIMIT=15`, each task processes 15 samples

## Customization

### Run Specific Tasks

Edit the `TASKS` array in the script (lines 64-94) to run only selected tasks:

```bash
TASKS=(
    "en-fpb"
    "taiwan"
    # Comment out tasks you don't want
)
```

### Change Sample Limit

Modify the `LIMIT` variable (line 28):

```bash
LIMIT=50  # Process 50 samples instead of 15
```

### Change Output Directory

Modify the `OUTPUT_BASE_DIR` variable (line 27):

```bash
OUTPUT_BASE_DIR="results/my_custom_run"
```

### Change Model

Modify the `--model_args` in the script (line 125):

```bash
--model_args "model=gpt-4o,harbor_mode=True"
```

## Notes

- The script uses `--no_cache` flag, so each run re-evaluates all tasks
- Agent details are saved when `--write_out` is enabled
- The script continues even if individual tasks fail
- All paths in the script use relative paths (after `cd`) for portability

## Related Files

- `src/eval.py`: Main evaluation script
- `src/codexlm.py`: Codex LM implementation with Harbor mode
- `src/evaluator.py`: Evaluation orchestrator
- `results/`: Output directory (created automatically)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review agent logs in `agent_details/` directories
3. Check Codex CLI logs and Docker logs
4. Verify all prerequisites are installed and configured correctly

