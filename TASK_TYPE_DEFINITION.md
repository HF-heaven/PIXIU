# PIXIU 任务类型划分说明

## 划分位置

任务类型的划分主要在以下两个文件中：

1. **`src/tasks/flare.py`** - 定义所有任务类及其继承关系（任务类型的划分）
2. **`src/tasks/__init__.py`** - 注册所有任务到 `TASK_REGISTRY` 字典

## 划分方式

任务类型通过**类的继承关系**来确定。每个任务类继承自某个基类，基类名称就是任务类型。

### 基类（任务类型）定义

在 `src/tasks/flare.py` 中定义了以下基类：

- `Classification` (第 36 行) - 分类任务
- `SequentialLabeling` (第 166 行) - 序列标注任务
- `AbstractiveSummarization` (第 277 行) - 抽象摘要任务
- `ExtractiveSummarization` (第 398 行) - 抽取式摘要任务
- `RelationExtraction` (第 541 行) - 关系抽取任务
- `QA` (第 642 行) - 问答任务
- `NER` (第 723 行) - 命名实体识别任务
- `TSA` (第 976 行) - 时间序列分析任务
- `LongFormFactuality` (第 1161 行) - 长文本事实性任务

### 任务类型划分示例

在 `src/tasks/flare.py` 中，每个具体任务通过继承关系确定类型：

```python
# Classification 类型
class FPB(Classification):          # 第 715 行
class FIQASA(Classification):       # 第 719 行
class StockMovement(Classification): # 第 804 行
class Headlines(Classification):     # 第 867 行
class FOMC(Classification):          # 第 930 行
# ... 等等

# QA 类型
class FinQA(QA):                     # 第 800 行
class ConvFinQA(QA):                 # 第 964 行
class TATQA(QA):                     # 第 1117 行
class ACRONYM(QA):                   # 第 1257 行
# ... 等等

# NER 类型
class NER(Task):                     # 第 723 行（直接继承 Task）
class ZHNER(NER):                    # 第 1365 行（继承 NER）

# RelationExtraction 类型
class FinRED(RelationExtraction):     # 第 1121 行
class ZH21CCKS(RelationExtraction):  # 第 1311 行
# ... 等等
```

## 完整任务类型列表

### Classification（分类任务）

定义在 `src/tasks/flare.py`，继承自 `Classification` 类的任务：

- `FPB` (第 715 行)
- `FIQASA` (第 719 行)
- `StockMovement` (第 804 行) - 以及其子类：`StockMovementBigData`, `StockMovementACL`, `StockMovementCIKM`, `German`, `Australian`
- `Headlines` (第 867 行)
- `FOMC` (第 930 行)
- `CFA` (第 1066 行, 第 1091 行 - 重复定义)
- `FINARGECCARC` (第 1071 行)
- `FINARGECCAUC` (第 1075 行)
- `FINARGECCAUC_test` (第 1079 行)
- `MLESG` (第 1083 行)
- `FinargECCAUC` (第 1094 行)
- `FinargECCARC` (第 1097 行)
- `MultiFinEN` (第 1104 行)
- `MA` (第 1107 行)
- `Causal20SC` (第 1110 行)
- `lendingclub` (第 1125 行)
- `ccf` (第 1130 行)
- `ccfraud` (第 1135 行)
- `polish` (第 1140 行)
- `taiwan` (第 1145 行)
- `portoseguro` (第 1150 行)
- `travelinsurace` (第 1155 行)
- `ZHFinFE` (第 1264 行)
- `ZHFinNL` (第 1268 行)
- `ZHFinNL2` (第 1272 行)
- `ZHFinNSP` (第 1276 行)
- `ZHFinRE` (第 1280 行)
- `ZHAFQMC` (第 1284 行)
- `ZHAstock` (第 1288 行)
- `ZHBQcourse` (第 1292 行)
- `ZHFinEval` (第 1296 行)
- `ZHstock11` (第 1300 行)
- `ZHFPB` (第 1375 行)
- `ZHFIQASA` (第 1379 行)
- `ESMultiFin` (第 1418 行)
- `ESEFP` (第 1421 行)
- `ESEFPA` (第 1424 行)
- `ESTSA` (第 1427 行)
- `ESFINANCEES` (第 1430 行)

### QA（问答任务）

继承自 `QA` 类的任务：

- `FinQA` (第 800 行)
- `ConvFinQA` (第 964 行)
- `TATQA` (第 1117 行)
- `ACRONYM` (第 1257 行)
- `ZHFinQA` (第 1303 行)
- `ZHFinQAE` (第 1411 行)
- `ZHConvFinQA` (第 1415 行) - 继承自 `ConvFinQA`

### NER（命名实体识别）

- `NER` (第 723 行) - 直接继承 `Task`
- `ZHNER` (第 1365 行) - 继承自 `NER`

### RelationExtraction（关系抽取）

- `FinRED` (第 1121 行)
- `ZH21CCKS` (第 1311 行)
- `ZH19CCKS` (第 1345 行)
- `ZH20CCKS` (第 1357 行) - 继承自 `ZH19CCKS`
- `ZH22CCKS` (第 1361 行) - 继承自 `ZH19CCKS`

### AbstractiveSummarization（抽象摘要）

- `EDTSUM` (第 956 行)
- `EDTSUM_test` (第 960 行)
- `ZHFinNA` (第 1307 行)
- `ESFNS` (第 1433 行)

### ExtractiveSummarization（抽取式摘要）

- `ECTSUM` (第 952 行)

### SequentialLabeling（序列标注）

- `FinerOrd` (第 917 行)
- `FSRL` (第 1087 行)
- `CD` (第 1100 行)
- `FNXL` (第 1113 行)

### TSA（时间序列分析）

- `TSA` (第 976 行) - 直接继承 `Task`
- `ESTSA` (第 1427 行) - 继承自 `Classification`（注意：这个可能有问题，应该是 TSA 类型）

### LongFormFactuality（长文本事实性）

- `LongFormFactuality` (第 1161 行) - 直接继承 `Task`
- `FINTERM` (第 1254 行) - 继承自 `LongFormFactuality`

## 任务注册

所有任务在 `src/tasks/__init__.py` 的 `TASK_REGISTRY` 字典中注册（第 9-59 行），将任务名称（字符串）映射到任务类。

## 总结

- **划分位置**: `src/tasks/flare.py` - 通过类的继承关系
- **注册位置**: `src/tasks/__init__.py` - `TASK_REGISTRY` 字典
- **划分方式**: 每个任务类继承自某个基类（Classification, QA, NER 等），基类名称就是任务类型

