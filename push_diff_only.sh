#!/bin/bash
# 只推送 adapter 分支和 main 分支的差异

set -euo pipefail

cd /home/hefan/PIXIU

BRANCH="adapter"
REMOTE="origin"
MAIN_BRANCH="main"

echo "=========================================="
echo "推送 $BRANCH 和 $MAIN_BRANCH 的差异"
echo "=========================================="
echo ""

# 获取远程最新信息
echo "步骤 1: 获取远程最新信息..."
git fetch $REMOTE

# 检查差异
echo ""
echo "步骤 2: 检查差异..."
BASE=$(git merge-base $REMOTE/$MAIN_BRANCH $BRANCH)
DIFF_COUNT=$(git rev-list --count $BASE..$BRANCH)

echo "  共同祖先: $BASE"
echo "  需要推送的提交数: $DIFF_COUNT"

if [ "$DIFF_COUNT" -eq 0 ]; then
    echo "  没有需要推送的差异！"
    exit 0
fi

echo ""
echo "  要推送的提交："
git log --oneline $BASE..$BRANCH | head -10
if [ "$DIFF_COUNT" -gt 10 ]; then
    echo "  ... 还有 $((DIFF_COUNT - 10)) 个提交"
fi

echo ""
echo "步骤 3: 尝试推送差异..."

# 方法 1: 尝试正常推送（只推送差异，这是 git 的默认行为）
echo ""
echo "方法 1: 正常推送（git 默认只推送差异）..."
if git push -u $REMOTE $BRANCH 2>&1; then
    echo "✅ 推送成功！"
    exit 0
fi

echo ""
echo "方法 1 失败，尝试方法 2..."

# 方法 2: 使用 --force-with-lease（安全强制推送）
echo ""
echo "方法 2: 使用 --force-with-lease（安全强制推送）..."
if git push --force-with-lease $REMOTE $BRANCH 2>&1; then
    echo "✅ 推送成功！"
    exit 0
fi

echo ""
echo "方法 2 失败，尝试方法 3..."

# 方法 3: 推送特定范围
echo ""
echo "方法 3: 推送特定提交范围..."
if git push $REMOTE $BASE..$BRANCH:refs/heads/$BRANCH 2>&1; then
    echo "✅ 推送成功！"
    exit 0
fi

echo ""
echo "❌ 所有方法都失败了"
echo ""
echo "可能的解决方案："
echo "1. 检查 GitHub 仓库权限设置"
echo "2. 尝试使用 HTTPS 而不是 SSH："
echo "   git remote set-url $REMOTE https://github.com/HF-heaven/PIXIU.git"
echo "   git push -u $REMOTE $BRANCH"
echo "3. 检查是否有大文件需要 Git LFS"
echo "4. 查看详细错误信息并联系 GitHub 支持"

exit 1

