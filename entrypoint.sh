#!/bin/sh

# 帮助信息函数
print_help() {
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  api         Start FastAPI server"
    echo "  ui          Start streamlit worker"
    echo "  help       Show this help message"
    echo
}

# install packages
install_deps() {
    echo "Installing dependencies with dev packages..."
    poetry install --with dev
}

# 参数检查
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
        # TODO(zhangzhong): 在这个位置做 pre commit install 比较合适
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

        exec uv run streamlit run eduagent/ui/ui.py


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
