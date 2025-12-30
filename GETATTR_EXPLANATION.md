# `getattr` 函数说明

## 定义位置

`getattr` 是 **Python 的内置函数**（built-in function），定义在 Python 标准库中，不需要导入即可使用。

## 函数签名

```python
getattr(object, name[, default]) -> value
```

- `object`: 要获取属性的对象
- `name`: 属性名称（字符串）
- `default`: 可选，如果属性不存在时返回的默认值

## 在 evaluator.py 中的用法

```python
resps = getattr(lm, reqtype)([req.args for req in reqs])
```

### 解释

1. **`reqtype`** 是一个字符串变量，可能是：
   - `"greedy_until"` - 用于生成任务
   - `"loglikelihood"` - 用于计算对数似然
   - `"loglikelihood_rolling"` - 用于滚动对数似然

2. **`getattr(lm, reqtype)`** 等价于：
   - 如果 `reqtype = "greedy_until"`，则等价于 `lm.greedy_until`
   - 如果 `reqtype = "loglikelihood"`，则等价于 `lm.loglikelihood`

3. **`getattr(lm, reqtype)([req.args for req in reqs])`** 等价于：
   - `lm.greedy_until([req.args for req in reqs])` （当 reqtype = "greedy_until" 时）

### 为什么使用 getattr？

因为 `reqtype` 是一个**变量**，不能直接写成 `lm.reqtype`（那会查找名为 "reqtype" 的属性，而不是 `reqtype` 变量的值）。

### 等价写法对比

```python
# 使用 getattr（动态调用）
resps = getattr(lm, reqtype)(requests)

# 如果 reqtype = "greedy_until"，等价于：
resps = lm.greedy_until(requests)

# 如果 reqtype = "loglikelihood"，等价于：
resps = lm.loglikelihood(requests)
```

## 在 CodexLM 中的实现

`CodexLM` 类继承自 `BaseLM`，需要实现以下方法：

1. **`greedy_until(requests)`** - 用于生成任务（Codex 使用这个）
   - 定义在：`/home/hefan/PIXIU/src/codexlm.py` 第 223 行

2. **`loglikelihood(requests)`** - 用于计算对数似然（Codex 不支持）
   - CodexLM 中抛出 `NotImplementedError`

## 示例

```python
# 假设 reqtype = "greedy_until"
reqtype = "greedy_until"
requests = [("prompt1", None), ("prompt2", None)]

# 使用 getattr 动态调用
result = getattr(lm, reqtype)(requests)
# 等价于: result = lm.greedy_until(requests)

# 如果 reqtype = "loglikelihood"
reqtype = "loglikelihood"
result = getattr(lm, reqtype)(requests)
# 等价于: result = lm.loglikelihood(requests)
```

## 相关代码位置

- `getattr` 调用：`/home/hefan/PIXIU/src/evaluator.py` 第 342 行
- `greedy_until` 实现：`/home/hefan/PIXIU/src/codexlm.py` 第 223 行
- `BaseLM` 基类：`/home/hefan/PIXIU/src/financial-evaluation/lm_eval/base.py`

