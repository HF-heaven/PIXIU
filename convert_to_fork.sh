#!/bin/bash
# 将当前的 PIXIU clone 转换为 fork 形式
# 
# 使用前请确保：
# 1. 在 GitHub 上已经 fork 了 https://github.com/The-FinAI/PIXIU
# 2. 知道你的 GitHub 用户名或 fork 的 URL

set -euo pipefail

# 原始仓库
ORIGINAL_REPO="https://github.com/The-FinAI/PIXIU.git"

# 检查是否在 PIXIU 目录
if [ ! -d ".git" ]; then
    echo "错误: 当前目录不是 git 仓库"
    exit 1
fi

# 提示用户输入 fork 的 URL
echo "=========================================="
echo "将 PIXIU clone 转换为 fork"
echo "=========================================="
echo ""
echo "原始仓库: $ORIGINAL_REPO"
echo ""
read -p "请输入你的 GitHub fork URL (例如: https://github.com/YOUR_USERNAME/PIXIU.git): " FORK_URL

if [ -z "$FORK_URL" ]; then
    echo "错误: 必须提供 fork URL"
    exit 1
fi

echo ""
echo "步骤 1: 添加 upstream 远程（指向原始仓库）..."
if git remote get-url upstream >/dev/null 2>&1; then
    echo "  upstream 已存在，更新为原始仓库..."
    git remote set-url upstream "$ORIGINAL_REPO"
else
    echo "  添加 upstream 远程..."
    git remote add upstream "$ORIGINAL_REPO"
fi

echo ""
echo "步骤 2: 将 origin 改为指向你的 fork..."
git remote set-url origin "$FORK_URL"

echo ""
echo "步骤 3: 验证远程配置..."
echo "  远程仓库配置:"
git remote -v

echo ""
echo "步骤 4: 获取最新信息..."
git fetch upstream
git fetch origin 2>/dev/null || echo "  注意: 你的 fork 可能还没有在本地，这很正常"

echo ""
echo "步骤 5: 检查当前状态..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
AHEAD_COUNT=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "0")

echo "  当前分支: $CURRENT_BRANCH"
echo "  领先 origin/main: $AHEAD_COUNT 个提交"

echo ""
echo "=========================================="
echo "转换完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 如果有未提交的更改，先提交或暂存："
echo "   git stash  # 暂存更改"
echo "   或"
echo "   git commit -am '你的提交信息'  # 提交更改"
echo ""
echo "2. 如果需要创建新分支保存当前状态："
echo "   git checkout -b harbor-integration"
echo ""
echo "3. 推送当前分支到你的 fork："
echo "   git push -u origin $CURRENT_BRANCH"
echo ""
echo "4. 之后可以这样同步原始仓库的更新："
echo "   git fetch upstream"
echo "   git merge upstream/main"
echo ""

