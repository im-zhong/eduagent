#!/bin/bash

set -euo pipefail

# 初始化生产模式标志
production_mode=false

# 参数检查
if [ $# -eq 0 ]; then
    echo "ERROR: No arguments provided"
    echo "Usage: $0 [--dev | --prod] [--api-port PORT] [--ui-port PORT]"
    exit 1
fi

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            production_mode=false
            shift
            ;;
        --prod)
            production_mode=true
            shift
            ;;
        --api-port)
            if [[ -z "$2" ]] || ! [[ "$2" =~ ^[0-9]+$ ]] || (( "$2" < 1 || "$2" > 65535 )); then
                echo "ERROR: --port requires valid port number (1-65535)"
                exit 1
            fi
            api_port="$2"
            shift 2
            ;;
        --ui-port)
            if [[ -z "$2" ]] || ! [[ "$2" =~ ^[0-9]+$ ]] || (( "$2" < 1 || "$2" > 65535 )); then
                echo "ERROR: --port requires valid port number (1-65535)"
                exit 1
            fi
            ui_port="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--dev | --prod] [--port PORT]"
            echo "Options:"
            echo "  --dev     Run in development mode"
            echo "  --prod    Run in production mode"
            echo "  --api-port    Set API service port (1-65535)"
            echo "  --ui-port     Set UI service port (1-65535)"
            exit 0
            ;;
        *)
            echo "ERROR: Unrecognized argument: $1"
            echo "Usage: $0 [--dev | --prod] [--api-port PORT] [--ui-port PORT]"
            exit 1
            ;;
    esac
done

# Step 1: Check required environment variables
ENV_FILE=".env"

# 确保 .env 存在
if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
fi

add_if_missing() {
    local key=$1
    local value=$2

    if grep -qE "^${key}=" "$ENV_FILE"; then
        echo "✅ $key 已存在于 $ENV_FILE 跳过"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
        echo "➕ 已写入 $key=$value 到 $ENV_FILE"
    fi
}

USER_UID=$(id -u)

add_if_missing "USER_UID" "$USER_UID"
add_if_missing "USER" "$USER"

echo "✅ 最终 .env 文件内容："
cat "$ENV_FILE"

# TODO(zhangzhong): add settings file later on
# Check for settings.toml
# if [ ! -f "etc/settings.toml" ]; then
#     echo "ERROR: Missing required configuration file: etc/settings.toml"
#     echo "Please create the file with appropriate settings before continuing."
#     exit 1
# fi

# Step 3: Start Docker Compose
echo "Starting Docker Compose..."
# docker compose -f docker-compose.prod.yaml -f docker-compose.dev.yaml up -d
# Step 3: Start Docker Compose with different configurations
echo "Starting Docker Compose..."

if [ "$production_mode" = true ]; then
    compose_files=(-f prod.docker-compose.yaml)
    echo "Starting in PRODUCTION mode with compose files: ${compose_files[*]}"

    if [ -n "${api_port:-}" ]; then
        echo "Setting API service port to $api_port"
        export EDUAGENT_API_PORT="$api_port"
    fi

    if [ -n "${ui_port:-}" ]; then
        echo "Setting UI service port to $ui_port"
        export EDUAGENT_UI_PORT="$ui_port"
    fi
else
    compose_files=(-f dev.docker-compose.yaml)
    echo "Starting in DEVELOPMENT mode"
fi

docker compose "${compose_files[@]}" down
docker compose "${compose_files[@]}" up -d

unset EDUAGENT_API_PORT
unset EDUAGENT_UI_PORT
