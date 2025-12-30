# PIXIU 分类任务中模型输出不属于备选 choice 的处理逻辑

## 核心逻辑（`Classification.process_results` 方法）

### 1. 匹配过程（第 96-104 行）

```python
result = None
for choice in doc["choices"]:
    if self.LOWER_CASE:
        choice = choice.lower()
    if choice in ini_result:  # 检查 choice 是否出现在模型输出中
        result = choice
        break
if result is None:
    result = "missing"  # 如果找不到匹配，设置为 "missing"
```

**关键点**：
- 使用 `choice in ini_result` 进行**子字符串匹配**（不是精确匹配）
- 只要模型输出中包含任何一个 choice 的文本，就认为匹配成功
- 如果所有 choice 都不匹配，`result` 被设置为字符串 `"missing"`

### 2. Metrics 计算（第 106-116 行）

```python
acc = 1.0 if gold == result else 0.0

results = {
    "acc": acc,  # 如果 result == "missing"，acc = 0.0（因为 gold 不可能是 "missing"）
    "missing": int(result == "missing"),  # 标记是否为 missing
    "f1": (result, gold),  # 元组，result 可能是 "missing"
    "macro_f1": (result, gold),
}

if self.CALCULATE_MCC:
    results["mcc"] = (result, gold)
```

**关键点**：
- **Accuracy**: 如果 `result == "missing"`，`acc = 0.0`（因为 gold 标签不可能是 "missing"）
- **Missing 标记**: `missing = 1` 表示模型输出不匹配任何 choice
- **F1/MCC**: 将 `"missing"` 作为一个**额外的标签类别**参与计算

### 3. F1 计算（第 131-144 行）

```python
def weighted_f1(self, items):
    preds, golds = zip(*items)
    labels = list(set(golds))  # 获取所有 gold 标签
    preds = np.array(preds)
    golds = np.array(golds)
    f1 = f1_score(golds, preds, average="weighted", labels=labels)
    return f1
```

**关键点**：
- `labels = list(set(golds))` 只包含**实际出现的 gold 标签**
- 如果预测是 `"missing"`，它会被 sklearn 的 `f1_score` 当作一个**未知标签**处理
- 由于 `labels` 参数只包含 gold 标签，`"missing"` 不在其中，sklearn 会如何处理？

### 4. sklearn f1_score 的行为

当 `labels` 参数指定时，sklearn 的 `f1_score` 会：
- **只计算指定 labels 的 F1**
- **忽略不在 labels 中的预测值**（如 "missing"）
- 对于 "missing" 预测，会被视为**该样本的预测无效**，可能：
  - 在 weighted 模式下，该样本的权重为 0
  - 在 macro 模式下，该样本不参与任何类别的 F1 计算

### 5. MCC 计算（第 147-152 行）

```python
def matthews_corrcoef(self, items):
    preds, golds = zip(*items)
    labels = {label: i for i, label in enumerate(list(set(golds)))}
    preds = [labels.get(pred, -1) for pred in preds]  # "missing" 会被映射为 -1
    golds = [labels.get(gold, -1) for gold in golds]
    return matthews_corrcoef(golds, preds)
```

**关键点**：
- `"missing"` 会被映射为 `-1`（因为不在 labels 字典中）
- `matthews_corrcoef` 会处理 `-1` 作为无效标签

## 总结

当模型输出不属于备选 choice 时：

1. **Accuracy**: `acc = 0.0`（因为 result = "missing" ≠ gold）

2. **Missing 标记**: `missing = 1`（记录为缺失预测）

3. **F1 (weighted/macro)**:
   - `"missing"` 作为预测值参与计算
   - 但由于 `labels` 参数只包含 gold 标签，`"missing"` 不在其中
   - sklearn 会**忽略**这些 "missing" 预测，导致：
     - 该样本不参与 F1 计算
     - 如果所有预测都是 "missing"，F1 可能为 0 或 NaN

4. **MCC**:
   - `"missing"` 被映射为 `-1`
   - `matthews_corrcoef` 会处理 `-1`，但结果可能不准确

## 实际影响

- **Accuracy**: 明确为 0（错误预测）
- **F1**: 可能被低估（因为 "missing" 样本可能被忽略）
- **Missing rate**: 可以单独统计，了解模型有多少输出不匹配任何 choice

## 与 Harbor Adapter 的对比

在 Harbor adapter 的 `test_pixiu.py` 中，我们目前的实现是：
- 如果预测不在 allowed_choices 中，直接 `pytest.fail()`
- 这比 PIXIU 更严格（PIXIU 允许 "missing" 并继续计算 metrics）

可以考虑修改 Harbor adapter 以匹配 PIXIU 的行为，将不匹配的预测标记为 "missing" 而不是直接失败。

