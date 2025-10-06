# Windows 系统配置指南

本文档专门针对 Windows 用户提供 EduAgent 项目的配置和使用指南。

## 前置要求

1. **Docker Desktop for Windows**
   - 下载地址: https://www.docker.com/products/docker-desktop
   - 确保启用 WSL2 后端（推荐）

2. **PowerShell 或 Git Bash**
   - Windows 10/11 自带 PowerShell
   - 或使用 Git Bash (随 Git for Windows 安装)

## 环境配置

### 1. 创建环境变量文件

在项目根目录执行：

**PowerShell:**
```powershell
Copy-Item env.template .env
```

**Git Bash / WSL:**
```bash
cp env.template .env
```

### 2. 验证 .env 文件

确认 `.env` 文件包含以下关键配置：

```bash
USER=eduagent
UID=1000
```

> **注意**: 在 Linux 容器中，UID 用于文件权限管理。Windows 用户使用固定值 `1000` 即可。

## 启动服务

### 开发环境

```powershell
docker compose -f dev.docker-compose.yaml up -d
```

### 生产环境

```powershell
docker compose -f prod.docker-compose.yaml up -d
```

### 查看服务状态

```powershell
docker compose -f dev.docker-compose.yaml ps
```

### 查看日志

```powershell
# 查看所有服务日志
docker compose -f dev.docker-compose.yaml logs

# 查看特定服务日志
docker compose -f dev.docker-compose.yaml logs eduagent-api

# 实时跟踪日志
docker compose -f dev.docker-compose.yaml logs -f
```

### 停止服务

```powershell
docker compose -f dev.docker-compose.yaml down
```

## 常见问题

### 1. entrypoint.sh 文件找不到或无法执行

**症状**: 容器不断重启，日志显示 `exec ./entrypoint.sh: no such file or directory`

**原因**: Windows 使用 CRLF (\\r\\n) 作为行结束符，而 Linux 使用 LF (\\n)。Shell 脚本在 Linux 容器中必须使用 LF。

**解决方法**:

方法 1 - 使用 PowerShell 转换：
```powershell
(Get-Content entrypoint.sh -Raw) -replace "`r`n", "`n" | Set-Content entrypoint.sh -NoNewline
```

方法 2 - 配置 Git（推荐，一劳永逸）：
项目已包含 `.gitattributes` 文件，会自动处理行结束符。如果文件已经签出，需要重新签出：
```powershell
git rm --cached -r .
git reset --hard
```

方法 3 - 配置你的编辑器：
- VS Code: 右下角点击 "CRLF"，选择 "LF"
- Notepad++: Edit → EOL Conversion → Unix (LF)

### 2. "The 'USER' variable is not set" 警告

**原因**: 没有创建 `.env` 文件或文件中缺少 `USER` 变量。

**解决方法**:
```powershell
# 复制模板创建 .env 文件
Copy-Item env.template .env
```

### 2. cAdvisor 无法启动

**症状**: cAdvisor 容器反复重启或无法启动

**原因**: cAdvisor 在 Windows + Docker Desktop 环境下可能不完全兼容

**解决方法 1** - 使用 WSL2 后端:
1. 打开 Docker Desktop
2. Settings → General
3. 确保勾选 "Use the WSL 2 based engine"

**解决方法 2** - 禁用 cAdvisor（如果不需要容器级别监控）:

编辑 `dev.docker-compose.yaml` 或 `prod.docker-compose.yaml`，注释掉 cAdvisor 部分：

```yaml
# cadvisor:
#   image: gcr.io/cadvisor/cadvisor:latest
#   ...
```

或者在启动时排除它：
```powershell
docker compose -f dev.docker-compose.yaml up -d --scale cadvisor=0
```

### 3. 端口冲突

**症状**: 启动失败，提示端口已被占用

**解决方法**: 修改 `.env` 文件中的端口配置：

```bash
# 例如，将 Grafana 从 3000 改为 3001
GRAFANA_PORT=3001
```

### 4. 路径挂载问题

**症状**: 容器无法访问挂载的本地目录

**解决方法**: 在 Docker Desktop 中配置文件共享：
1. Settings → Resources → File Sharing
2. 添加项目目录路径
3. 点击 "Apply & Restart"

### 5. 权限问题

**症状**: 容器无法写入 data/ 目录

**解决方法**: 
```powershell
# 创建必要的目录
New-Item -ItemType Directory -Force -Path data/postgres
New-Item -ItemType Directory -Force -Path data/prometheus
New-Item -ItemType Directory -Force -Path data/grafana

# 如果问题依然存在，在 docker-compose.yaml 中添加 user 配置
# 例如: user: "0:0"  # 使用 root 用户（仅用于开发）
```

## 性能优化建议

### 使用 WSL2 后端

WSL2 提供更好的性能和兼容性：

1. 安装 WSL2: https://docs.microsoft.com/en-us/windows/wsl/install
2. 在 Docker Desktop 中启用 WSL2 后端
3. 将项目克隆到 WSL2 文件系统中（而不是 Windows 文件系统）

```bash
# 在 WSL2 中
cd ~
git clone <your-repo-url>
cd eduagent
cp env.template .env
docker compose -f dev.docker-compose.yaml up -d
```

### 资源限制配置

在 Docker Desktop 中配置资源限制：
1. Settings → Resources
2. 调整 CPU、Memory、Swap 等配置
3. 推荐配置:
   - CPU: 4 核
   - Memory: 8 GB
   - Swap: 2 GB

## 监控访问

- Grafana: http://localhost:3000
  - 用户名: `admin`
  - 密码: `admin`
- Prometheus: http://localhost:9090
- cAdvisor: http://localhost:8081 (如果已启用)

详细的监控配置请参考 [MONITORING.md](MONITORING.md)。

## 开发工作流

### 1. 进入开发容器

```powershell
docker compose -f dev.docker-compose.yaml exec eduagent-dev bash
```

### 2. 运行测试

```powershell
# 在容器内
pytest

# 或从外部直接执行
docker compose -f dev.docker-compose.yaml exec eduagent-dev pytest
```

### 3. 代码检查

```powershell
# Ruff 检查
docker compose -f dev.docker-compose.yaml exec eduagent-dev ruff check .

# Pyright 类型检查
docker compose -f dev.docker-compose.yaml exec eduagent-dev pyright
```

## 清理数据

### 清理容器和镜像

```powershell
# 停止并删除容器
docker compose -f dev.docker-compose.yaml down

# 同时删除 volumes（包括数据库数据）
docker compose -f dev.docker-compose.yaml down -v

# 清理未使用的镜像
docker image prune -a
```

### 清理监控数据

```powershell
Remove-Item -Recurse -Force data/prometheus/*
Remove-Item -Recurse -Force data/grafana/*
```

## 获取帮助

如果遇到其他问题：
1. 查看 [常见问题文档](TIPS.md)
2. 检查容器日志: `docker compose logs`
3. 在项目 Issues 中搜索或提交问题

## 相关链接

- [Docker Desktop 文档](https://docs.docker.com/desktop/windows/)
- [WSL2 文档](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker Compose 文档](https://docs.docker.com/compose/)

