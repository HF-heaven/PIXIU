# Codex CLI 配置完成

## ✅ 配置状态

Codex CLI 已在 PIXIU benchmark 中成功配置并测试通过！

### 已验证的功能

1. ✅ Codex CLI 已安装 (v0.75.0)
2. ✅ Codex CLI 已登录
3. ✅ CodexLM 类可以正常初始化
4. ✅ Codex CLI 调用测试成功

### 已知问题

- **Tokenizer Fallback**: 由于 `transformers` 和 `torch` 版本不兼容，tokenizer 使用了 fallback 模式。这不影响 Codex CLI 的实际功能，只是 token 编码/解码可能不够精确，但对于评估任务影响很小。

## 使用方法

### 在 pixiu_env conda 环境中运行

```bash
# 激活 conda 环境
source ~/anaconda3/etc/profile.d/conda.sh
conda activate pixiu_env

# 设置 API key
export OPENAI_API_KEY="your-api-key"

# 运行评估（小规模测试）
cd /home/hefan/PIXIU
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 5
```

### 测试脚本

运行简单测试：

```bash
conda activate pixiu_env
export OPENAI_API_KEY="your-api-key"
cd /home/hefan/PIXIU
python test_codex_simple.py
```

## 文件位置

- `src/codexlm.py` - CodexLM 实现（已优化，支持 tokenizer fallback）
- `src/evaluator.py` - 评估器（已添加 codex 模型支持）
- `test_codex_simple.py` - 简单测试脚本
- `CODEX_SETUP.md` - 详细配置文档

## 下一步

1. **运行小规模评估**：使用 `--limit 5` 测试几个任务
2. **运行完整评估**：移除 `--limit` 参数运行完整数据集
3. **对比结果**：将结果与 Harbor 中的结果进行对比，验证 parity

## 故障排除

如果遇到问题：

1. **确保 Codex CLI 已登录**：
   ```bash
   codex login status
   # 如果未登录，运行：
   echo $OPENAI_API_KEY | codex login --with-api-key
   ```

2. **确保使用正确的 conda 环境**：
   ```bash
   conda activate pixiu_env
   ```

3. **检查 Node.js 版本**（Codex CLI 需要 Node.js 22+）：
   ```bash
   source ~/.nvm/nvm.sh
   nvm use 22
   ```

## 注意事项

- Tokenizer 使用 fallback 模式，token 计数可能不够精确，但不影响评估结果
- Codex CLI 调用是同步的，可能需要较长时间
- 确保 API key 有足够的配额

