#!/bin/bash
set -euo pipefail

# 初始化生产模式标志
production_mode=false

# 参数检查
if [ $# -eq 0 ]; then
    echo "ERROR: No arguments provided"
    echo "Usage: $0 [--dev | --prod] [--port PORT]"
    exit 1
fi

# 解析命令行参数
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
        --port)
            if [[ -z "$2" ]] || ! [[ "$2" =~ ^[0-9]+$ ]] || (( "$2" < 1 || "$2" > 65535 )); then
                echo "ERROR: --port requires valid port number (1-65535)"
                exit 1
            fi
            twitter_service_port="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--dev | --prod] [--port PORT]"
            echo "Options:"
            echo "  --dev     Run in development mode"
            echo "  --prod    Run in production mode"
            echo "  --port    Set proxy service port (1-65535)"
            exit 0
            ;;
        *)
            echo "ERROR: Unrecognized argument: $1"
            echo "Usage: $0 [--dev | --prod] [--port PORT]"
            exit 1
            ;;
    esac
done

# Step 1: Check required environment variables
required_vars=("UID" "USER")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! printenv "$var" > /dev/null; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "ERROR: Missing required environment variables:"
    printf ' - %s\n' "${missing_vars[@]}"
    echo "Please set these variables before running the script."
    exit 1
fi

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

    if [ -n "${twitter_service_port:-}" ]; then
        echo "Setting proxy service port to $twitter_service_port"
        export TWITTER_SERVICE_PORT="$twitter_service_port"
    fi
else
    compose_files=(-f dev.docker-compose.yaml)
    echo "Starting in DEVELOPMENT mode"
fi

docker compose "${compose_files[@]}" down
docker compose "${compose_files[@]}" up -d
