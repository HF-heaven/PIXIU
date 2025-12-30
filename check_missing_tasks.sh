#!/bin/bash
# 快速检查7个缺失任务的运行情况

MISSING_TASKS=(
    "en-forecasting-travelinsurance"
    "finben-finer-ord"
    "flare-causal20-sc"
    "flare-multifin-en"
    "flare-sm-acl"
    "flare-sm-bigdata"
    "flare-sm-cikm"
)

cd /home/hefan/PIXIU

echo "=========================================="
echo "缺失任务运行状态检查"
echo "=========================================="
echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

completed=0
running=0
not_started=0

for task in "${MISSING_TASKS[@]}"; do
    result_file="results/harbor_all_tasks_codex_gpt-5-mini/$task/results.json"
    task_dir="results/harbor_all_tasks_codex_gpt-5-mini/$task"
    
    if [ -f "$result_file" ]; then
        size=$(stat -c%s "$result_file" 2>/dev/null)
        lines=$(wc -l < "$result_file" 2>/dev/null)
        echo "✅ $task"
        echo "   状态: 已完成"
        echo "   文件大小: ${size} bytes"
        echo "   行数: ${lines}"
        ((completed++))
    elif [ -d "$task_dir" ]; then
        mtime=$(stat -c %y "$task_dir" 2>/dev/null | cut -d'.' -f1)
        file_count=$(find "$task_dir" -type f 2>/dev/null | wc -l)
        echo "⏳ $task"
        echo "   状态: 运行中或已创建目录"
        echo "   最后修改: $mtime"
        echo "   目录内文件数: $file_count"
        ((running++))
    else
        echo "❌ $task"
        echo "   状态: 未开始"
        ((not_started++))
    fi
    echo ""
done

echo "=========================================="
echo "统计汇总"
echo "=========================================="
echo "已完成: $completed / 7"
echo "运行中: $running / 7"
echo "未开始: $not_started / 7"
echo ""

# 检查是否有相关进程
echo "检查相关进程..."
if ps aux | grep -E "run_single_missing|simple_evaluate" | grep -v grep > /dev/null; then
    echo "✅ 发现相关进程正在运行"
    ps aux | grep -E "run_single_missing|simple_evaluate" | grep -v grep | head -3
else
    echo "⚠️  未发现相关进程（可能已完成或失败）"
fi

echo ""
echo "查看日志: tail -f /home/hefan/PIXIU/run_missing_tasks_direct.log"

