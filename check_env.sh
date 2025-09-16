#!/bin/bash

# 	•	set -e：遇到错误就停。
# 	•	set -u：禁止用未定义变量。
# 	•	set -o pipefail：管道出错不会被忽略。

# 所以 set -euo pipefail 一起用，就是：

# 👉 脚本在遇到错误时立即退出，禁止使用未定义变量，管道中任何错误都会触发退出。
set -euo pipefail

echo "🔧 初始化开发环境..."

BASHRC="$HOME/.bashrc"

##############################################
# 1. 设置 UID/GID 自动注入
##############################################
if ! grep -q "## EduAgent Dev container UID setup" "$BASHRC"; then
    cat >> "$BASHRC" <<'EOF'

## EduAgent Dev container UID setup
if [ -z "${UID:-}" ]; then
    export UID=$(id -u)
fi
EOF
    echo "✅ 已将 UID/GID 设置逻辑写入 $BASHRC"
else
    echo "✅ UID/GID 设置逻辑已存在于 $BASHRC"
fi

##############################################
# 2. 检查 Git 仓库
##############################################
if [ ! -d ".git" ]; then
    echo "❌ 当前目录没有 .git 文件夹，可能是直接下载的压缩包，而不是 git clone 下来的！"
    echo "   👉 请使用: git clone git@github.com:<your-org>/<your-repo>.git"
    exit 1
else
    echo "✅ Git 仓库检测正常 (.git 存在)"
fi

##############################################
# 3. 检查 Git 用户配置
##############################################
if ! git config user.name >/dev/null 2>&1; then
    echo "❌ Git 未配置 user.name"
    echo "   👉 请执行: git config --global user.name \"Your Name\""
    exit 1
else
    echo "✅ 已检测到 git user.name: $(git config user.name)"
fi

if ! git config user.email >/dev/null 2>&1; then
    echo "❌ Git 未配置 user.email"
    echo "   👉 请执行: git config --global user.email \"you@example.com\""
    exit 1
else
    echo "✅ 已检测到 git user.email: $(git config user.email)"
fi

##############################################
# 4. 检查 SSH 公钥
##############################################
if [ ! -f "$HOME/.ssh/id_rsa.pub" ] && [ ! -f "$HOME/.ssh/id_ed25519.pub" ]; then
    echo "❌ 没有找到 ssh 公钥 (~/.ssh/id_rsa.pub 或 id_ed25519.pub)"
    echo "   👉 请运行: ssh-keygen -t ed25519 -C \"you@example.com\""
    exit 1
else
    echo "✅ 已检测到 ssh 公钥"
fi

##############################################
# 5. 检查 SSH 连接 GitHub
##############################################
# result=`ssh -T git@github.com 2>&1 | grep -n success`
# echo $result

# ssh -T git@github.com 2>&1

# if [ ! -z "$(ssh -T git@github.com 2>&1 | grep -n success)" ]; then
#     echo "❌ SSH 无法连接 GitHub，请确认已将公钥添加到 GitHub"
#     echo "   👉 GitHub 设置路径: https://github.com/settings/keys"
#     exit 1
# else
#     echo "✅ SSH 可以连接 GitHub"
# fi

if git ls-remote git@github.com:im-zhong/eduagent.git &>/dev/null; then
    echo "✅ GitHub SSH 配置正确"
else
    echo "❌ GitHub SSH 配置失败，请检查 SSH key 设置"
    exit 1
fi

##############################################
# 6. 检查 Docker
##############################################
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ 未检测到 Docker，请先安装 Docker"
    echo "   👉 https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker 服务未启动或当前用户无权限运行 docker"
    echo "   👉 请检查："
    echo "      1. Docker Desktop 是否已启动 (Windows/Mac)"
    echo "      2. systemctl status docker (Linux)"
    echo "      3. 当前用户是否加入 docker 组: sudo usermod -aG docker \$USER"
    exit 1
fi

echo "✅ Docker 已安装且正在运行"

##############################################
# 7. 检查 Git 分支（避免在 main 上开发）
##############################################
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
    echo "❌ 当前在 main 分支上，请切换到 dev 或其他开发分支再继续开发"
    exit 1
else
    echo "✅ 当前分支: $BRANCH"
fi

##############################################
# 全部检查通过
##############################################
echo "🎉 开发环境初始化完成！一切正常 ✅"
