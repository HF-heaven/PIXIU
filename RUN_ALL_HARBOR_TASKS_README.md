# 批量运行所有 Harbor 任务在 PIXIU Benchmark 中

## 概述

这个脚本会自动：
1. 扫描 `/home/hefan/harbor/datasets/pixiu` 下所有任务
2. 提取每个任务的样本 ID
3. 在 PIXIU benchmark 中运行 Codex (gpt-5-mini) 评估
4. 输出每个任务的结果

## 使用方法

### 基本用法

```bash
cd /home/hefan/PIXIU
bash run_all_harbor_tasks.sh codex gpt-5-mini
```

### 后台运行

```bash
cd /home/hefan/PIXIU
nohup bash run_all_harbor_tasks.sh codex gpt-5-mini > /tmp/pixiu_all_tasks.log 2>&1 &
```

### 监控进度

```bash
# 查看日志
tail -f /tmp/pixiu_all_tasks.log

# 查看已完成的任务数
find results/harbor_all_tasks_codex_gpt-5-mini -name "results.json" | wc -l
```

## 输出结构

```
results/harbor_all_tasks_codex_gpt-5-mini/
├── summary.json                    # 汇总结果
├── en-fpb/
│   ├── results.json                # 该任务的结果
│   └── FilteredFPB_write_out_info.json  # 详细输出（如果使用 --write-out）
├── flare-headlines/
│   ├── results.json
│   └── ...
└── ...
```

## 结果文件格式

### 单个任务结果 (`<task_name>/results.json`)

```json
{
  "results": {
    "FilteredFPB": {
      "acc": 0.8667,
      "acc_stderr": 0.0909,
      "f1": 0.8667,
      "macro_f1": 0.8968,
      "mcc": 0.7794
    }
  },
  "config": {
    "model": "codex",
    "model_args": "model=gpt-5-mini",
    ...
  }
}
```

### 汇总结果 (`summary.json`)

```json
{
  "total_tasks": 29,
  "successful_tasks": 29,
  "failed_tasks": 0,
  "model": "codex",
  "model_args": "model=gpt-5-mini",
  "results": {
    "en-fpb": {
      "pixiu_task": "flare_fpb",
      "sample_count": 15,
      "results": {...},
      "output_file": "..."
    },
    ...
  },
  "failed": []
}
```

## 查看结果

### 查看汇总

```bash
cd /home/hefan/PIXIU
cat results/harbor_all_tasks_codex_gpt-5-mini/summary.json | python3 -m json.tool | less
```

### 查看特定任务的结果

```bash
cd /home/hefan/PIXIU
cat results/harbor_all_tasks_codex_gpt-5-mini/en-fpb/results.json | python3 -m json.tool
```

### 提取所有任务的指标

```bash
cd /home/hefan/PIXIU
python3 << 'EOF'
import json
from pathlib import Path

summary_file = Path("results/harbor_all_tasks_codex_gpt-5-mini/summary.json")
if summary_file.exists():
    summary = json.loads(summary_file.read_text())
    print("任务\t\t样本数\tAccuracy\tF1\tMacro F1")
    print("-" * 60)
    for task_name, task_data in sorted(summary["results"].items()):
        results = task_data["results"].get("results", {})
        for task_type, metrics in results.items():
            acc = metrics.get("acc", 0.0)
            f1 = metrics.get("f1", metrics.get("acc", 0.0))
            macro_f1 = metrics.get("macro_f1", 0.0)
            print(f"{task_name:20}\t{task_data['sample_count']}\t{acc:.4f}\t{f1:.4f}\t{macro_f1:.4f}")
EOF
```

## 注意事项

1. **运行时间**: 29 个任务，每个 15 个样本，预计需要较长时间（数小时）
2. **API 费用**: 使用 Codex API 会产生费用
3. **日志文件**: 建议使用 `nohup` 后台运行，并监控日志文件
4. **中断恢复**: 如果中断，可以手动运行单个任务：
   ```bash
   python auto_eval_harbor_task.py en-fpb
   ```

## 故障排除

### 查看失败的任务

```bash
cd /home/hefan/PIXIU
cat results/harbor_all_tasks_codex_gpt-5-mini/summary.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data['failed']:
    print('失败的任务:')
    for task, error in data['failed']:
        print(f'  {task}: {error}')
else:
    print('所有任务都成功完成！')
"
```

### 重新运行失败的任务

```bash
cd /home/hefan/PIXIU
# 手动运行单个任务
python auto_eval_harbor_task.py <task_name>
```

