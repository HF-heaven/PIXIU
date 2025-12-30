#!/bin/bash
# 检查批量评估进度

OUTPUT_DIR="${1:-results/harbor_all_tasks_codex_gpt-5-mini}"

echo "=========================================="
echo "批量评估进度检查"
echo "=========================================="
echo ""

if [ ! -d "$OUTPUT_DIR" ]; then
    echo "输出目录不存在: $OUTPUT_DIR"
    exit 1
fi

# 统计已完成和进行中的任务
completed=0
in_progress=0
total=29  # 总共 29 个任务

echo "任务状态:"
for dir in "$OUTPUT_DIR"/*/; do
    if [ -d "$dir" ]; then
        task_name=$(basename "$dir")
        if [ -f "$dir/results.json" ]; then
            echo "  ✓ $task_name"
            completed=$((completed + 1))
        else
            echo "  ⏳ $task_name (进行中)"
            in_progress=$((in_progress + 1))
        fi
    fi
done

echo ""
echo "=========================================="
echo "进度: $completed/$total 已完成"
if [ $in_progress -gt 0 ]; then
    echo "进行中: $in_progress"
fi
echo "剩余: $((total - completed - in_progress))"
echo "=========================================="

# 如果有汇总文件，显示失败的任务
if [ -f "$OUTPUT_DIR/summary.json" ]; then
    echo ""
    echo "汇总文件已生成"
    failed=$(python3 -c "
import json, sys
try:
    data = json.load(open('$OUTPUT_DIR/summary.json'))
    if data.get('failed'):
        print('失败的任务:')
        for task, error in data['failed']:
            print(f'  - {task}: {error}')
    else:
        print('所有任务都成功完成！')
except:
    pass
" 2>/dev/null)
    if [ -n "$failed" ]; then
        echo "$failed"
    fi
fi

