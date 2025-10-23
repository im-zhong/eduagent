# EduAgent 监控系统文档

本文档介绍如何使用 Prometheus 和 Grafana 监控 EduAgent 系统的容器和服务。

## 📋 目录

- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [访问监控服务](#访问监控服务)
- [配置说明](#配置说明)
- [仪表板说明](#仪表板说明)
- [自定义配置](#自定义配置)
- [常见问题](#常见问题)

## 🏗️ 系统架构

监控系统由以下组件组成：

```
┌─────────────────┐
│   Grafana       │ ← 可视化仪表板 (端口 3000)
│   Dashboard     │
└────────┬────────┘
         │
         ↓ 查询数据
┌─────────────────┐
│   Prometheus    │ ← 时序数据库 (端口 9090)
│   TSDB          │
└────────┬────────┘
         │
         ↓ 抓取指标
┌─────────────────┐
│   cAdvisor      │ ← 容器指标收集器 (端口 8080)
│                 │
└────────┬────────┘
         │
         ↓ 监控
┌─────────────────────────────────────┐
│  Docker 容器                         │
│  - eduagent-api                     │
│  - eduagent-ui                      │
│  - eduagent-db                      │
│  - ...                              │
└─────────────────────────────────────┘
```

### 组件说明

1. **cAdvisor**: 收集 Docker 容器的 CPU、内存、网络、磁盘等指标
2. **Prometheus**: 存储时序数据，提供强大的查询语言 PromQL
3. **Grafana**: 提供美观的可视化仪表板和告警功能

## 🚀 快速开始

### 1. 启动开发环境

```bash
# 启动所有服务（包括监控系统）
docker-compose -f dev.docker-compose.yaml up -d

# 查看服务状态
docker-compose -f dev.docker-compose.yaml ps

# 查看监控服务日志
docker-compose -f dev.docker-compose.yaml logs -f prometheus grafana cadvisor
```

### 2. 启动生产环境

```bash
# 启动所有服务（包括监控系统）
docker-compose -f prod.docker-compose.yaml up -d

# 查看服务状态
docker-compose -f prod.docker-compose.yaml ps
```

### 3. 环境变量配置（可选）

在项目根目录创建 `.env` 文件，自定义端口和认证信息：

```bash
# Grafana 配置
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your_secure_password

# Prometheus 配置
PROMETHEUS_PORT=9090

# cAdvisor 配置
CADVISOR_PORT=8080
```

## 🌐 访问监控服务

### Grafana 仪表板

- **访问地址**: http://localhost:3000
- **默认用户名**: `admin`
- **默认密码**: `admin`（首次登录后会要求修改）

**功能特性**：
- 📊 Docker 容器监控仪表板（已预配置）
- 📈 实时指标可视化
- 🔔 告警规则配置
- 📱 多种通知渠道支持

### Prometheus 控制台

- **访问地址**: http://localhost:9090
- **功能**: 
  - 查询时序数据
  - 查看抓取目标状态
  - 测试 PromQL 查询
  - 查看告警规则

### cAdvisor Web UI

- **访问地址**: http://localhost:8080
- **功能**: 
  - 实时容器资源使用情况
  - 容器性能分析
  - 历史数据图表

## ⚙️ 配置说明

### Prometheus 配置

配置文件: `eduagent/monitor/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s        # 每 15 秒抓取一次指标
  evaluation_interval: 15s    # 每 15 秒评估一次告警规则

scrape_configs:
  - job_name: 'prometheus'    # Prometheus 自监控
  - job_name: 'cadvisor'      # Docker 容器监控
```

**关键参数**：
- `scrape_interval`: 指标抓取频率，越小越精确但占用更多资源
- `storage.tsdb.retention.time`: 数据保留时间，默认 30 天

### Grafana 数据源配置

配置文件: `eduagent/monitor/grafana/provisioning/datasources/datasource.yml`

Prometheus 数据源已自动配置，无需手动添加。

### Grafana 仪表板配置

配置文件: `eduagent/monitor/grafana/provisioning/dashboards/dashboard.yml`

仪表板会自动从 `eduagent/monitor/grafana/dashboards/` 目录加载。

## 📊 仪表板说明

### Docker Host & Container Overview

**仪表板 ID**: 10619  
**文件位置**: `eduagent/monitor/grafana/dashboards/docker-monitoring.json`

**主要监控指标**：

1. **系统级指标**
   - CPU 使用率
   - 内存使用率
   - 磁盘使用率
   - 网络流量

2. **容器级指标**
   - 每个容器的 CPU 使用情况
   - 每个容器的内存使用情况
   - 容器网络 I/O
   - 容器磁盘 I/O
   - 容器运行状态

3. **性能指标**
   - CPU 限流统计
   - 内存 OOM 事件
   - 网络丢包率
   - 磁盘延迟

### 如何使用仪表板

1. 登录 Grafana (http://localhost:3000)
2. 导航到 **Dashboards** → **Browse**
3. 选择 **EduAgent** 文件夹
4. 打开 **Docker Host & Container Overview** 仪表板

**仪表板功能**：
- 🔍 按容器名称过滤
- ⏱️ 自定义时间范围
- 📌 固定关键指标
- 💾 保存自定义视图
- 📤 导出为 PDF/PNG

## 🛠️ 自定义配置

### 添加新的监控目标

编辑 `eduagent/monitor/prometheus/prometheus.yml`，添加新的抓取配置：

```yaml
scrape_configs:
  # 监控 EduAgent API 应用
  - job_name: 'eduagent-api'
    static_configs:
      - targets: ['eduagent-api:8000']
        labels:
          service: 'eduagent-api'
          environment: 'production'
```

**注意**: 应用需要暴露 `/metrics` 端点（Prometheus 格式）

### 添加 PostgreSQL 监控

1. 在 docker-compose 文件中添加 postgres-exporter：

```yaml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter:v0.15.0
  restart: unless-stopped
  environment:
    DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@eduagent-db:5432/${POSTGRES_DB}?sslmode=disable"
  ports:
    - "9187:9187"
  networks:
    - eduagent-network
  depends_on:
    - eduagent-db
```

2. 在 Prometheus 配置中添加抓取任务：

```yaml
scrape_configs:
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

### 导入其他 Grafana 仪表板

1. 访问 [Grafana 仪表板市场](https://grafana.com/grafana/dashboards/)
2. 找到合适的仪表板，记下 ID
3. 在 Grafana UI 中：**Dashboards** → **Import** → 输入仪表板 ID
4. 选择 Prometheus 数据源并导入

**推荐仪表板**：
- [893](https://grafana.com/grafana/dashboards/893) - Docker Monitoring
- [1860](https://grafana.com/grafana/dashboards/1860) - Node Exporter Full
- [9628](https://grafana.com/grafana/dashboards/9628) - PostgreSQL Database

### 配置告警

创建告警规则文件 `eduagent/monitor/prometheus/alerts/container-alerts.yml`：

```yaml
groups:
  - name: container_alerts
    interval: 30s
    rules:
      # 容器内存使用超过 80%
      - alert: HighMemoryUsage
        expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.name }} 内存使用率过高"
          description: "{{ $labels.name }} 内存使用率 {{ $value }}%"

      # 容器 CPU 使用超过 80%
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "容器 {{ $labels.name }} CPU 使用率过高"
```

在 Prometheus 配置中启用告警规则：

```yaml
rule_files:
  - "alerts/*.yml"
```

## 🔧 常见问题

### Q1: Grafana 无法访问？

**解决方案**：
```bash
# 检查 Grafana 容器状态
docker-compose -f dev.docker-compose.yaml ps grafana

# 查看 Grafana 日志
docker-compose -f dev.docker-compose.yaml logs grafana

# 确保端口未被占用
netstat -ano | findstr :3000  # Windows
lsof -i :3000                 # Linux/Mac
```

### Q2: Prometheus 无法抓取 cAdvisor 数据？

**解决方案**：
```bash
# 检查 cAdvisor 是否运行
curl http://localhost:8080/metrics

# 查看 Prometheus 目标状态
# 访问 http://localhost:9090/targets
```

### Q3: 仪表板显示 "No Data"？

**可能原因**：
1. Prometheus 数据源配置错误
2. 数据还未收集（等待 15-30 秒）
3. 时间范围选择不当

**解决方案**：
- 在 Grafana 中检查数据源连接状态
- 调整仪表板时间范围到 "Last 5 minutes"
- 在 Prometheus UI 中测试查询

### Q4: 如何备份 Grafana 仪表板？

**方案 1 - 导出 JSON**：
1. 打开仪表板
2. 点击右上角设置图标
3. 选择 "JSON Model"
4. 复制 JSON 并保存到文件

**方案 2 - 备份数据目录**：
```bash
# 备份 Grafana 数据
tar -czf grafana-backup.tar.gz ./data/grafana/

# 恢复数据
tar -xzf grafana-backup.tar.gz -C ./data/
```

### Q5: 如何减少监控数据占用的磁盘空间？

**调整 Prometheus 数据保留时间**：

编辑 docker-compose 文件中的 Prometheus 命令：

```yaml
command:
  - '--storage.tsdb.retention.time=7d'  # 改为 7 天
```

**调整抓取频率**：

编辑 `prometheus.yml`：

```yaml
global:
  scrape_interval: 30s  # 从 15s 改为 30s
```

### Q6: Windows 上 cAdvisor 无法启动？

cAdvisor 在 Windows 上可能有兼容性问题。**解决方案**：

1. 使用 WSL2 + Docker Desktop
2. 或者使用 Windows 特定的监控工具，如 [wmi-exporter](https://github.com/prometheus-community/windows_exporter)

### Q7: Windows 上 Grafana/Prometheus 容器不断重启，日志显示权限错误？

**问题症状**：
```
GF_PATHS_DATA='/var/lib/grafana' is not writable.
mkdir: can't create directory '/var/lib/grafana/plugins': Permission denied
```

或者 Prometheus 日志显示：
```
err="open /prometheus/queries.active: permission denied"
panic: Unable to create mmap-ed active query log
```

**根本原因**：
在 Windows + Docker Desktop + WSL2 环境下，Docker 卷挂载会遇到文件权限问题。容器内的非 root 用户无法写入挂载的 Windows 目录。

**解决方案**：

在 `dev.docker-compose.yaml` 和 `prod.docker-compose.yaml` 中，为 Grafana 和 Prometheus 服务添加 `user: root`：

```yaml
# Prometheus 配置
prometheus:
  image: prom/prometheus:v2.54.1
  restart: unless-stopped
  hostname: prometheus.eduagent
  user: root  # ← 添加这一行
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    ...

# Grafana 配置
grafana:
  image: grafana/grafana:11.2.2
  restart: unless-stopped
  hostname: grafana.eduagent
  user: root  # ← 添加这一行
  ports:
    - "${GRAFANA_PORT:-3000}:3000"
  ...
```

**应用修复**：
```bash
# 1. 停止所有容器
docker-compose -f dev.docker-compose.yaml down

# 2. 重新启动
docker-compose -f dev.docker-compose.yaml up -d

# 3. 检查状态（等待 10-15 秒）
docker-compose -f dev.docker-compose.yaml ps
```

**验证**：
- 访问 http://localhost:3000 应该能正常打开 Grafana
- 访问 http://localhost:9090 应该能正常打开 Prometheus

**注意**：这个问题只在 Windows 环境下出现，Linux 和 macOS 通常不需要这个配置。

## 📚 扩展阅读

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [cAdvisor GitHub](https://github.com/google/cadvisor)
- [PromQL 查询语言教程](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana 仪表板最佳实践](https://grafana.com/docs/grafana/latest/best-practices/)

## 🤝 贡献

如果你发现问题或有改进建议，欢迎提交 Issue 或 Pull Request！

---

**最后更新**: 2025-10-16  
**维护者**: EduAgent Team



