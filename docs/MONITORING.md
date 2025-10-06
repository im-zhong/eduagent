# EduAgent 监控系统使用指南

本文档介绍如何使用 Prometheus、Grafana 和 cAdvisor 监控 EduAgent 应用和容器。

## 快速开始

### 启动监控系统（开发环境）

```bash
# 启动所有服务（包括监控）
docker compose -f dev.docker-compose.yaml up -d

# 或者只启动监控相关服务
docker compose -f dev.docker-compose.yaml up -d prometheus grafana cadvisor node-exporter
```

### 启动监控系统（生产环境）

```bash
# 启动所有服务（包括监控）
docker compose -f prod.docker-compose.yaml up -d

# 或者只启动监控相关服务
docker compose -f prod.docker-compose.yaml up -d prometheus grafana cadvisor node-exporter
```

## 访问监控界面

### Grafana 仪表板
- **地址**: http://localhost:3000
- **默认用户名**: `admin`
- **默认密码**: `admin`

首次登录后，系统会要求你修改密码。

登录后，你可以在左侧菜单中找到：
- **Dashboards** → **Docker** → **Docker 容器和主机监控**

### Prometheus
- **地址**: http://localhost:9090
- 可以查询原始指标数据和创建自定义查询

### cAdvisor
- **地址**: http://localhost:8081
- 提供实时容器性能数据的详细视图

## 监控指标说明

### 容器指标
- **CPU 使用率**: 每个容器的 CPU 使用百分比
- **内存使用量**: 每个容器占用的内存大小
- **网络 I/O**: 容器的网络接收和发送速率
- **磁盘 I/O**: 容器的磁盘读写速率

### 主机指标
- **主机 CPU 使用率**: 整个主机的 CPU 使用情况
- **主机内存使用率**: 主机内存使用百分比
- **主机磁盘使用率**: 根分区磁盘使用百分比
- **运行中的容器数量**: 当前活跃的容器数

## 自定义配置

### 修改端口

在项目根目录创建 `.env` 文件，添加以下内容：

```bash
# Prometheus 端口（默认: 9090）
PROMETHEUS_PORT=9090

# Grafana 端口（默认: 3000）
GRAFANA_PORT=3000

# cAdvisor 端口（默认: 8081）
CADVISOR_PORT=8081

# Grafana 管理员账户
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password
```

### 添加新的监控目标

编辑 `monitoring/prometheus/prometheus.yml`，在 `scrape_configs` 部分添加新的 job：

```yaml
scrape_configs:
  # 示例：监控你的 FastAPI 应用
  - job_name: 'eduagent-api'
    static_configs:
      - targets: ['eduagent-api:8000']
    metrics_path: '/metrics'  # 你的应用需要暴露 /metrics 端点
```

重启 Prometheus 以应用更改：

```bash
docker compose -f dev.docker-compose.yaml restart prometheus
```

## 导入额外的仪表板

Grafana 社区提供了大量现成的仪表板，你可以轻松导入：

1. 访问 https://grafana.com/grafana/dashboards/
2. 搜索你需要的仪表板（如 "Docker", "Node Exporter"）
3. 记下仪表板 ID
4. 在 Grafana 中：
   - 点击左侧 "+" 图标
   - 选择 "Import"
   - 输入仪表板 ID
   - 选择 "Prometheus" 作为数据源
   - 点击 "Import"

### 推荐的仪表板

- **Node Exporter Full** (ID: 1860) - 完整的主机系统监控
- **Docker Container & Host Metrics** (ID: 179) - Docker 容器监控
- **cAdvisor exporter** (ID: 14282) - cAdvisor 详细指标

## 数据持久化

监控数据存储在以下目录：
- Prometheus: `./data/prometheus/` - 时序数据库
- Grafana: `./data/grafana/` - 仪表板配置和用户数据

这些目录已添加到 `.gitignore`，不会被提交到版本控制。

## 清理数据

如果需要清理监控数据：

```bash
# 停止服务
docker compose -f dev.docker-compose.yaml down

# 删除监控数据（保留配置）
rm -rf ./data/prometheus/*
rm -rf ./data/grafana/*

# 重新启动
docker compose -f dev.docker-compose.yaml up -d
```

## 常见问题

### Windows 系统下 cAdvisor 无法启动

cAdvisor 主要为 Linux 设计。在 Windows 上使用 Docker Desktop 时可能会遇到问题。解决方法：

1. 确保使用 WSL2 后端
2. 或者移除 cAdvisor 服务，使用 Docker Desktop 自带的监控功能

### Grafana 仪表板显示 "No Data"

1. 检查 Prometheus 是否正常运行：访问 http://localhost:9090
2. 在 Prometheus 中查询指标，如 `container_cpu_usage_seconds_total`
3. 确认数据源配置正确：Grafana → Configuration → Data Sources
4. 等待几分钟让数据收集

### 如何监控特定的容器

在 Grafana 仪表板中，可以通过容器名称过滤。或者修改 Prometheus 查询：

```promql
# 只监控 eduagent-api 容器
rate(container_cpu_usage_seconds_total{name="eduagent-api"}[1m]) * 100
```

## 性能影响

监控组件会占用一定的系统资源：
- **Prometheus**: ~200-500MB 内存
- **Grafana**: ~100-200MB 内存
- **cAdvisor**: ~50-100MB 内存
- **Node Exporter**: ~10-20MB 内存

如果在资源受限的环境中，可以选择性启动监控服务。

## 下一步

- 配置告警规则（Prometheus Alertmanager）
- 设置长期数据存储
- 集成到 CI/CD 流程
- 添加自定义应用指标

更多信息请参考：
- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [cAdvisor GitHub](https://github.com/google/cadvisor)


