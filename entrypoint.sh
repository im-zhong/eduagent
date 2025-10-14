#!/bin/sh

# 帮助信息函数
print_help() {
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  api         Start FastAPI server"
    echo "  ui          Start streamlit worker"
    echo "  dev        Start both FastAPI and Streamlit in development mode"
    echo "  help       Show this help message"
    echo
}

# install packages
install_deps() {
    echo "Installing dependencies with dev packages..."
    uv sync --dev
}

# 在这里安装合�?
install_precommit() {
    if command -v uv &>/dev/null; then
        echo "🔗 使用 uv 安装 pre-commit hooks..."
        uv run pre-commit install
    elif command -v pre-commit &>/dev/null; then
        echo "🔗 使用系统 pre-commit 安装 hooks..."
        pre-commit install
    else
        echo "�?pre-commit 未安装，请先运行: uv pip install pre-commit"
        exit 1
    fi
}

# 参数检�?
if [ $# -eq 0 ]; then
    echo "Error: No command specified"
    echo
    print_help
    exit 1
fi

# 命令处理
case "$1" in
    api)
        echo "Starting FastAPI..."
        # TODO(zhangzhong): 在这个位置做 pre commit install 比较合�?
        install_deps

        # exec poetry run python -m twitter_service.server.api.api
        exec uv run uvicorn eduagent.api:api \
            --host "0.0.0.0" \
            --port 8000 \
            --log-level info
            --reload
            # --reload-dir eduagent \
            # --reload-exclude 'data/*'
        ;;
    ui)
        echo "Starting Streamlit..."
        install_deps

        export PYTHONPATH=.
        exec uv run streamlit run eduagent/ui/main.py
        ;;
    dev)
        echo "Starting both FastAPI and Streamlit in development mode..."

        install_deps
        install_precommit
        # install claude code envs, I need to check the json file on the ~/.claude.json and ~/.claude
        # and I should use the proper API KEY, maybe on different project, I want to use different key
        # so in each container, use there own key is ok, so we try to not mapping the
        # we try to not touch the onboard settings, and only set the api keys envs, throuth docker env

        # "/bin/bash", "-c", "tail -f /dev/null"
        sleep infinity

        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo "Error: Invalid command '$1'"
        echo
        print_help
        exit 1
        ;;
esac
