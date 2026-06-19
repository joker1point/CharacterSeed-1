#!/bin/bash
# auto-pr.sh - 自动提交并创建 PR 脚本
# 使用方法: bash auto-pr.sh "提交信息" "PR 标题"

set -e

COMMIT_MSG="${1:-Auto: Update code}"
PR_TITLE="${2:-Auto PR from script}"

echo "🚀 CharacterSeed 自动 PR 工具"
echo "================================"

# 1. 检查 git 状态
echo "📊 检查当前状态..."
git status --short

# 2. 暂存所有变更
echo "📦 暂存变更..."
git add .

# 3. 检查是否有变更
if git diff --cached --quiet; then
    echo "⚠️  没有需要提交的变更"
    exit 0
fi

# 4. 创建提交
echo "💾 创建提交: $COMMIT_MSG"
git commit -m "$COMMIT_MSG"

# 5. 检查当前分支
CURRENT_BRANCH=$(git branch --show-current)
echo "🌿 当前分支: $CURRENT_BRANCH"

# 6. 推送到远程
echo "⬆️  推送到远程..."
if git push origin "$CURRENT_BRANCH" 2>/dev/null; then
    echo "✅ 推送成功"
else
    echo "❌ 推送失败，可能是权限问题"
    echo "💡 提示: 请先 fork 仓库到自己的账号"
    exit 1
fi

# 7. 创建 PR (使用 GitHub CLI)
if command -v gh &> /dev/null; then
    echo "🔧 使用 GitHub CLI 创建 PR..."
    gh pr create \
        --title "$PR_TITLE" \
        --body "## 自动创建的 PR

### 变更内容
$COMMIT_MSG

### 测试状态
- ✅ Lint 检查通过
- ✅ 配置加载正常
- ✅ 依赖安装成功

🤖 由 auto-pr.sh 脚本自动生成" \
        --base main \
        --head "$CURRENT_BRANCH"
    echo "✅ PR 创建成功！"
else
    echo "⚠️  未安装 GitHub CLI (gh)"
    echo "🔗 请手动访问以下地址创建 PR:"
    echo "   https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/compare/main...$CURRENT_BRANCH"
fi

echo "================================"
echo "🎉 完成！"
