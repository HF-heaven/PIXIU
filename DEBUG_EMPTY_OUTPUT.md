# 调试模型输出为空的问题

## 问题描述

在 `flare_cra_taiwan_write_out_info.json` 中，所有样本的 `logit_0` 字段都是空字符串 `""`，说明模型没有返回任何输出。

## 可能的原因

1. **Codex CLI 执行失败但没有抛出异常**
   - Codex CLI 可能返回了非零退出码，但被捕获了
   - 或者执行成功但返回了空输出

2. **输出解析失败**
   - Codex CLI 的输出格式可能不符合预期
   - JSON 解析失败导致无法提取输出

3. **异常被捕获但只返回空字符串**
   - `greedy_until` 中的异常处理会返回空字符串
   - 但错误信息可能没有正确打印

## 调试步骤

### 1. 启用调试模式

```bash
export CODEX_DEBUG=true
```

或者在代码中：

```python
lm = CodexLM(model="gpt-4o")
lm._debug_mode = True
```

### 2. 检查 Codex CLI 是否正常工作

```bash
# 测试 Codex CLI
codex --version

# 测试简单执行
codex exec --model gpt-4o --json -- "echo 'test'"
```

### 3. 检查运行日志

查看运行时的输出，应该会看到：
- `[ERROR]` 或 `[WARNING]` 消息
- Codex CLI 的原始输出
- 异常堆栈跟踪

### 4. 手动测试一个样本

```python
from codexlm import CodexLM

lm = CodexLM(model="gpt-4o", harbor_mode=False)
lm._debug_mode = True

# 测试一个简单的 prompt
output = lm._call_codex_cli("What is 2+2? Answer with just the number.")
print(f"Output: '{output}'")
```

### 5. 检查临时文件（Harbor 模式）

如果使用 Harbor 模式，检查临时目录：

```python
import tempfile
import glob

# 查找临时目录
temp_dirs = glob.glob("/tmp/pixiu_codex_*")
for temp_dir in temp_dirs:
    print(f"Found temp dir: {temp_dir}")
    # 检查 answer.txt
    answer_path = Path(temp_dir) / "app" / "answer.txt"
    if answer_path.exists():
        print(f"  answer.txt exists: {answer_path.read_text()}")
    else:
        print(f"  answer.txt does not exist")
```

## 常见问题

### 问题 1: Codex CLI 未安装或未登录

**症状**: 执行失败，返回错误码

**解决**:
```bash
npm install -g @openai/codex@latest
echo $OPENAI_API_KEY | codex login --with-api-key
```

### 问题 2: API Key 未设置

**症状**: `ValueError: OPENAI_API_KEY environment variable is required`

**解决**:
```bash
export OPENAI_API_KEY=your_api_key_here
```

### 问题 3: 输出格式不符合预期

**症状**: Codex CLI 返回了输出，但解析失败

**解决**: 检查 Codex CLI 的输出格式，可能需要更新解析逻辑

### 问题 4: 超时

**症状**: `RuntimeError: Codex CLI timed out`

**解决**: 增加超时时间或检查网络连接

## 修复建议

如果确认是代码问题，可以：

1. **添加更详细的日志**（已实现）
2. **改进错误处理**（已实现）
3. **添加重试机制**
4. **验证 Codex CLI 输出格式**

## 下一步

1. 重新运行评估，启用 `CODEX_DEBUG=true`
2. 查看完整的错误日志
3. 根据错误信息进行修复

