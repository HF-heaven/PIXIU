# 如何查看 Codex Agent 的输出

有几种方法可以查看 Codex agent 的原始输出：

## 方法 1: 使用 `--write_out` 参数（推荐）

这会保存详细的输出信息，包括 prompt 和 model 的响应：

```bash
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"

cd /home/hefan/PIXIU
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 5 \
  --write_out \
  --output_base_path results/codex_outputs
```

输出会保存在 `results/codex_outputs/flare_headlines_write_out_info.json`，包含：
- `prompt_0`, `prompt_1`, ...: 每个请求的 prompt
- `logit_0`, `logit_1`, ...: Codex 的原始输出
- `truth`: 正确答案

查看输出：
```bash
cat results/codex_outputs/flare_headlines_write_out_info.json | python -m json.tool | less
```

## 方法 2: 启用调试模式

设置环境变量 `CODEX_DEBUG=true` 可以在运行时打印输出：

```bash
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"
export CODEX_DEBUG=true

cd /home/hefan/PIXIU
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 5
```

这会在终端显示每个 prompt 和对应的输出。

## 方法 3: 查看评估结果 JSON

使用 `--output_path` 保存评估结果：

```bash
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 5 \
  --output_path results/codex_results.json
```

结果 JSON 包含评估指标，但不会包含原始的 agent 输出。

## 方法 4: 直接测试 CodexLM 类

创建一个简单的测试脚本查看输出：

```python
import sys
import os
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/financial-evaluation')

os.environ['OPENAI_API_KEY'] = 'your-api-key'
os.environ['CODEX_DEBUG'] = 'true'  # 启用调试模式

from codexlm import CodexLM

lm = CodexLM(model='gpt-4o')

# 测试一个 prompt
prompt = "Consider whether the headline references past prices of gold. Can a PastPrice in the gold market be inferred from the news headline? Your response should be either Yes or No.\nText: gold prices ease in asia\nAnswer:"

output = lm._call_codex_cli(prompt)
print("\n=== Codex Output ===")
print(output)
print("\n=== Raw Output ===")
print(lm._last_raw_output[:1000])  # 前 1000 个字符
```

## 方法 5: 修改代码添加日志

在 `src/codexlm.py` 的 `greedy_until` 方法中，输出已经可以通过 `self._last_raw_output` 访问。你可以添加日志文件：

```python
# 在 greedy_until 方法中添加
import logging
logging.basicConfig(filename='codex_outputs.log', level=logging.DEBUG)
logging.debug(f"Prompt: {prompt}")
logging.debug(f"Output: {output}")
logging.debug(f"Raw: {self._last_raw_output}")
```

## 推荐工作流

1. **快速查看**: 使用 `CODEX_DEBUG=true` 环境变量
2. **详细分析**: 使用 `--write_out --output_base_path` 保存完整信息
3. **调试单个样本**: 使用方法 4 直接测试

## 示例：查看 write_out 输出

```bash
# 运行评估并保存输出
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 3 \
  --write_out \
  --output_base_path results/debug

# 查看第一个样本的输出
cat results/debug/flare_headlines_write_out_info.json | \
  python -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data[0], indent=2))"
```

这会显示第一个样本的：
- `prompt_0`: 发送给 Codex 的完整 prompt
- `logit_0`: Codex 的原始输出
- `truth`: 正确答案

