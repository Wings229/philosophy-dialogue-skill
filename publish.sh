#!/bin/bash
# ============================================
# 哲学对话 Skill 发布流程
# ============================================
#
# 发布前检查清单：
# 1. ✅ package.json 版本号已更新
# 2. ✅ SKILL.md 版本历史已更新
# 3. ✅ UPGRADE-LOG.md 已记录变更
# 4. ✅ 本地 git 已提交
#
# 发布顺序：
# 1. 更新 package.json 版本号
# 2. 更新 SKILL.md 版本历史
# 3. git commit
# 4. clawhub publish（版本号从 package.json 读取）
# 5. git push GitHub
#
# ⚠️ 禁止：clawhub publish --version X.Y.Z 手动指定版本号
#    必须从 package.json 读取，确保一致性
# ============================================

set -e

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SKILL_DIR"

# 从 package.json 读取版本号
VERSION=$(python3 -c "import json; print(json.load(open('package.json'))['version'])" 2>/dev/null || \
          node -e "console.log(require('./package.json').version)" 2>/dev/null)

if [ -z "$VERSION" ]; then
    echo "❌ 无法读取 package.json 版本号"
    exit 1
fi

echo "📦 准备发布 philosophy-dialogue v${VERSION}"
echo ""

# 检查 package.json 版本号是否已更新
echo "🔍 检查版本号一致性..."
SKILL_VERSION=$(grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' SKILL.md | tail -1)
echo "   package.json: v${VERSION}"
echo "   SKILL.md:     ${SKILL_VERSION}"

if [ "v${VERSION}" != "${SKILL_VERSION}" ]; then
    echo "⚠️  版本号不一致！请先同步 SKILL.md 中的版本号"
    echo "   期望: v${VERSION}"
    read -p "   继续发布？(y/N) " confirm
    if [ "$confirm" != "y" ]; then
        echo "❌ 发布取消"
        exit 1
    fi
fi

# 检查 git 状态
echo "🔍 检查 git 状态..."
if [ -n "$(git status --porcelain "$SKILL_DIR")" ]; then
    echo "⚠️  有未提交的更改，请先 git commit"
    git status --short "$SKILL_DIR"
    exit 1
fi

echo ""
echo "🚀 发布到 ClawHub..."
clawhub publish "$SKILL_DIR" --version "$VERSION" --changelog "${1:-v${VERSION} update}"

echo ""
echo "✅ ClawHub 发布完成: v${VERSION}"
echo ""
echo "📝 下一步："
echo "   1. 同步 GitHub: git push"
echo "   2. 更新 .git-upload 目录并推送 GitHub 仓库"
