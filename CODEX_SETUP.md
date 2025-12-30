# Codex CLI 配置指南

本指南说明如何在 PIXIU benchmark 中配置和使用 Codex CLI agent。

## 前置要求

1. **Node.js 22+**: Codex CLI 需要 Node.js 22 或更高版本
2. **OpenAI API Key**: 需要有效的 OpenAI API key

## 安装步骤

### 1. 安装/更新 Node.js

```bash
# 安装 nvm (如果还没有)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
source "$HOME/.nvm/nvm.sh"

# 安装 Node.js 22
nvm install 22
nvm use 22

# 验证安装
node --version  # 应该显示 v22.x.x
```

### 2. 安装 Codex CLI

```bash
npm install -g @openai/codex@latest

# 验证安装
codex --version
```

### 3. 配置 API Key 和登录

Codex CLI 需要先登录才能使用。有两种方式：

**方式 1: 使用环境变量登录（推荐）**

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
echo "$OPENAI_API_KEY" | codex login --with-api-key
```

**方式 2: 交互式登录**

```bash
codex login
# 按照提示输入 API key
```

验证登录状态：

```bash
codex login status
```

**注意**: 确保 API key 是有效的，并且有足够的配额。

### 4. 安装 Python 依赖

确保安装了 PIXIU 的所有依赖：

```bash
cd /home/hefan/PIXIU
pip install -r requirements.txt
```

如果遇到 `sqlitedict` 缺失，可以单独安装：

```bash
pip install sqlitedict
```

## 使用方法

### 运行评估

使用 Codex 运行 PIXIU 评估：

```bash
# 设置 API key
export OPENAI_API_KEY="your-api-key"

# 确保使用 Node.js 22
source "$HOME/.nvm/nvm.sh"
nvm use 22

# 运行评估（小规模测试）
cd /home/hefan/PIXIU
python src/eval.py \
  --model codex \
  --model_args model=gpt-4o \
  --tasks flare_headlines \
  --limit 5
```

### 参数说明

- `--model codex`: 指定使用 Codex 模型
- `--model_args model=gpt-4o`: 指定 Codex 使用的 OpenAI 模型（如 `gpt-4o`, `gpt-4-turbo` 等）
- `--tasks <task_name>`: 指定要运行的任务
- `--limit 5`: 限制测试样本数量（仅用于测试）

### 支持的模型

Codex CLI 支持以下 OpenAI 模型：
- `gpt-4o` (推荐)
- `gpt-4-turbo`
- `gpt-4`
- `gpt-3.5-turbo`

## 故障排除

### 1. Codex CLI 认证失败

如果遇到 `401 Unauthorized` 错误：

- **首先确保已登录**：
  ```bash
  echo "$OPENAI_API_KEY" | codex login --with-api-key
  codex login status  # 验证登录状态
  ```
- 检查 `OPENAI_API_KEY` 是否正确设置
- 验证 API key 是否有效且有足够配额
- 如果仍然失败，尝试重新登录：
  ```bash
  codex logout
  echo "$OPENAI_API_KEY" | codex login --with-api-key
  ```

### 2. Node.js 版本问题

如果 Codex CLI 无法运行：

```bash
# 确保使用 Node.js 22
source "$HOME/.nvm/nvm.sh"
nvm use 22
node --version
```

### 3. Python 依赖问题

如果遇到模块导入错误：

```bash
# 安装缺失的依赖
pip install sqlitedict transformers tqdm numpy
```

### 4. 测试配置

运行测试脚本验证配置：

```bash
cd /home/hefan/PIXIU
bash scripts/test_codex.sh
```

## 代码结构

- `src/codexlm.py`: CodexLM 类实现，包装 Codex CLI
- `src/evaluator.py`: 评估器，已添加对 `codex` 模型的支持
- `scripts/test_codex.sh`: 测试脚本

## 与 Harbor 的对比

在 Harbor 框架中，Codex agent 通过 Docker 容器运行，而在 PIXIU 中，Codex 直接通过 CLI 调用。两者的核心逻辑相同，但运行环境不同。

## 下一步

配置完成后，你可以：

1. 运行小规模测试验证配置
2. 在完整数据集上运行评估
3. 将结果与 Harbor 中的结果进行对比，验证 parity

