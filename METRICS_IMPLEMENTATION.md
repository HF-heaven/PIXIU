# PIXIU Metrics 实现说明

本文档说明 PIXIU 中不同任务类型使用的 metrics 以及它们在哪里实现和比较。

## 核心评估流程

### 1. 主入口：`src/evaluator.py`

评估的核心流程在 `simple_evaluate` 函数中：

```python
# 第 384 行：对每个文档处理结果
metrics = task.process_results(doc, requests)
for metric, value in metrics.items():
    vals[(task_name, metric)].append(value)

# 第 396-405 行：聚合所有文档的结果
for (task_name, metric), items in vals.items():
    task = task_dict[task_name]
    real_metric = metric
    results[task_name][metric] = task.aggregation()[real_metric](items)
```

**关键步骤**：
1. **`process_results(doc, results)`**: 处理单个文档的模型输出，返回该文档的 metrics 值（可能是元组，用于后续聚合）
2. **`aggregation()`**: 返回一个字典，包含每个 metric 的聚合函数
3. **聚合函数**: 接收所有文档的 metrics 值列表，计算最终分数

## 各任务类型的 Metrics

### 1. Classification（分类任务）

**文件**: `src/tasks/flare.py` (第 36-164 行)

**Metrics**:
- `acc`: 准确率（精确匹配）
- `f1`: 加权 F1 分数
- `macro_f1`: 宏平均 F1 分数
- `mcc`: 马修斯相关系数（可选，由 `CALCULATE_MCC` 控制）
- `missing`: 缺失预测的比例

**实现**:
- `process_results()` (第 88-118 行): 将模型输出与标准答案比较，计算单个文档的 acc 和 missing
- `aggregation()` (第 154-163 行): 
  - `acc`: 使用 `mean` 函数（来自 `lm_eval.metrics`）
  - `f1`: 使用 `weighted_f1()` 方法（sklearn 的 `f1_score` with `average="weighted"`）
  - `macro_f1`: 使用 `macro_f1()` 方法（sklearn 的 `f1_score` with `average="macro"`）
  - `mcc`: 使用 `matthews_corrcoef()` 方法（sklearn 的 `matthews_corrcoef`）

**继承此类的任务**:
- `FPB`, `FIQASA`, `CFA`, `FINARGECCARC`, `FINARGECCAUC`, `StockMovement`, `FOMC`, `MultiFinEN`, `MA`, `Causal20SC`, `lendingclub`, `ccf`, `ccfraud`, `polish`, `taiwan`, `portoseguro`, `travelinsurace` 等

**特殊变体**:
- `Headlines` (第 867-914 行): 使用 `avg_f1` metric，按标签类型分组计算 F1，然后取平均
- `StockMovement` (第 804-845 行): 支持通过 `CHOICE_DICT` 进行同义词匹配（如 "rise" 匹配 "yes", "positive"）

---

### 2. QA（问答任务）

**文件**: `src/tasks/flare.py` (第 642-713 行)

**Metrics**:
- `acc`: 准确率（精确字符串匹配）

**实现**:
- `process_results()` (第 695-702 行): 将模型输出与标准答案进行精确字符串比较
- `aggregation()` (第 709-712 行): 使用 `mean` 函数计算平均准确率

**继承此类的任务**:
- `FinQA`, `TATQA`, `ACRONYM`, `ZHFinQA`, `ZHFinQAE` 等

---

### 3. NER（命名实体识别）

**文件**: `src/tasks/flare.py` (第 723-797 行)

**Metrics**:
- `entity_f1`: 实体级别的 F1 分数

**实现**:
- `process_results()` (第 777-781 行): 使用 `process_text()` 解析模型输出，返回 `(pred, doc["label"], results[0])` 元组
- `aggregation()` (第 794-797 行): 使用 `entity_f1()` 类方法，调用 `seqeval.metrics.f1_score` 计算实体级别的 F1

**继承此类的任务**:
- `ZHNER` 等

---

### 4. RelationExtraction（关系抽取）

**文件**: `src/tasks/flare.py` (第 541-640 行)

**Metrics**:
- `precision`: 精确率
- `recall`: 召回率
- `f1`: F1 分数

**实现**:
- `process_results()` (第 574-579 行): 返回 `(doc["label"], results[0])` 元组
- `aggregation()` (第 634-639 行):
  - `precision()`: 计算集合交集与预测集合的比例
  - `recall()`: 计算集合交集与标准答案集合的比例
  - `cal_f1()`: 基于 precision 和 recall 计算 F1

**继承此类的任务**:
- `ZH21CCKS`, `ZH19CCKS`, `ZH20CCKS`, `ZH22CCKS` 等

---

### 5. AbstractiveSummarization（抽象摘要）

**文件**: `src/tasks/flare.py` (第 277-397 行)

**Metrics**:
- `rouge1`: ROUGE-1 分数
- `rouge2`: ROUGE-2 分数
- `rougeL`: ROUGE-L 分数
- `bert_score_f1`: BERTScore F1
- `bart_score`: BARTScore

**实现**:
- `process_results()` (第 310-317 行): 返回元组 `(doc["answer"], results[0])`
- `aggregation()` (第 388-396 行):
  - `rouge1/rouge2/rougeL()`: 使用 `evaluate.load("rouge")` 计算 ROUGE 分数
  - `bert_score_f1()`: 使用 `evaluate.load("evaluate-metric/bertscore")` 计算 BERTScore，取 F1 的平均值
  - `bart_score()`: 使用自定义的 `BARTScorer` 类（来自 `src/metrics/BARTScore/bart_score.py`）

**继承此类的任务**:
- `ZHFinNA` 等

---

### 6. ExtractiveSummarization（抽取式摘要）

**文件**: `src/tasks/flare.py` (第 398-539 行)

**Metrics**:
- `rouge1`, `rouge2`, `rougeL`, `bert_score_f1`, `bart_score`（与 AbstractiveSummarization 相同）

**实现**:
- `process_results()` (第 431-438 行): 返回 `(doc["label"], doc["text"], results[0])` 元组（多了一个 `text` 参数）
- `aggregation()` (第 531-538 行): 与 AbstractiveSummarization 类似，但使用 `get_sum()` 方法从原始文本中提取摘要片段

**区别**: 需要根据 `label` 从原始文本中提取标准答案和预测答案的摘要片段，然后再计算 metrics

---

### 7. TSA（时间序列分析）

**文件**: `src/tasks/flare.py` (第 976-1063 行)

**Metrics**:
- `rmse`: 均方根误差（Root Mean Squared Error）
- `missing`: 缺失预测的比例

**实现**:
- `process_results()` (第 1010-1023 行): 从模型输出中提取数字，计算与标准答案的误差
- `aggregation()` (第 1058-1062 行):
  - `rmse()`: 使用 `sklearn.metrics.mean_squared_error` 计算 MSE，然后开平方根得到 RMSE
  - `missing`: 使用 `mean` 函数

**注意**: `rmse` 的 `higher_is_better` 为 `False`（越小越好）

---

### 8. LongFormFactuality（长文本事实性）

**文件**: `src/tasks/flare.py` (第 1161-1251 行)

**Metrics**:
- `factscore`: FactScore 分数

**实现**:
- `process_results()` (第 1194-1197 行): 返回 `(doc["answer"], doc["text"], results[0])` 元组
- `aggregation()` (第 1248-1251 行): 使用 `factscore()` 方法，调用 `FactScorer` 类（来自 `factscore_package.factscorer`）计算事实性分数

**继承此类的任务**:
- `FINTERM` 等

---

### 9. SequentialLabeling（序列标注）

**文件**: `src/tasks/flare.py` (第 166-275 行)

**Metrics**:
- `entity_f1`: 实体级别的 F1 分数
- `f1`: 标签级别的加权 F1 分数

**实现**:
- `process_results()` (第 200-204 行): 返回 `(doc["label"], results[0], doc["token"])` 元组
- `aggregation()` (第 270-274 行):
  - `entity_f1()`: 使用 `seqeval.metrics.f1_score` 计算实体级别的 F1
  - `label_f1()`: 使用 `sklearn.metrics.f1_score` 计算标签级别的加权 F1

---

## Metrics 库依赖

PIXIU 使用了多个 metrics 库：

1. **`lm_eval.metrics`**: 提供 `mean` 等基础聚合函数
2. **`sklearn.metrics`**: 
   - `f1_score` (weighted/macro)
   - `matthews_corrcoef`
   - `mean_squared_error`
3. **`seqeval.metrics`**: 用于序列标注任务的实体级别 F1
4. **`evaluate`** (Hugging Face): 
   - `rouge` metric
   - `evaluate-metric/bertscore`
5. **自定义 metrics**:
   - `BARTScore`: `src/metrics/BARTScore/bart_score.py`
   - `FactScore`: `factscore_package.factscorer`

## 总结

- **比较位置**: `src/evaluator.py` 的 `simple_evaluate` 函数（第 384-405 行）
- **任务定义**: `src/tasks/flare.py` 中的各个 Task 类
- **每个任务类必须实现**:
  - `process_results(doc, results)`: 处理单个文档的结果
  - `aggregation()`: 返回 metrics 到聚合函数的映射
  - `higher_is_better()`: 返回每个 metric 是否越大越好

