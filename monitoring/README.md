# EduAgent 监控系统

本目录包含 Prometheus、Grafana 和 cAdvisor 的配置文件，用于监控 Docker 容器和主机系统。

## 组件说明

- **Prometheus**: 时序数据库，用于收集和存储指标数据
- **Grafana**: 可视化平台，用于创建监控仪表板
- **cAdvisor**: 容器监控工具，用于收集容器资源使用情况
- **Node Exporter**: 主机监控工具，用于收集主机系统指标

## 访问地址

启动 docker-compose 后，可以通过以下地址访问：

- Grafana: http://localhost:3000
  - 默认用户名: `admin`
  - 默认密码: `admin`（首次登录后会要求修改）
  
- Prometheus: http://localhost:9090

- cAdvisor: http://localhost:8081

## 目录结构

```
monitoring/
├── prometheus/
│   └── prometheus.yml          # Prometheus 配置文件
├── grafana/
│   └── provisioning/
│       ├── datasources/        # 数据源配置
│       │   └── datasource.yml
│       └── dashboards/         # 仪表板配置
│           ├── dashboard.yml
│           └── docker-container-metrics.json  # Docker 容器监控仪表板
└── README.md
```

## 可用仪表板

1. **Docker 容器和主机监控** - 显示所有容器和主机的关键指标：
   - 容器 CPU 使用率
   - 容器内存使用量
   - 容器网络 I/O
   - 容器磁盘 I/O
   - 运行中的容器数量
   - 主机 CPU/内存/磁盘使用率

## 自定义配置

### 添加新的监控目标

编辑 `prometheus/prometheus.yml` 文件，在 `scrape_configs` 部分添加新的 job。

### 导入额外的仪表板

1. 访问 Grafana
2. 点击 "+" -> "Import"
3. 输入仪表板 ID（例如，从 https://grafana.com/grafana/dashboards/ 获取）
4. 选择 Prometheus 作为数据源

推荐的仪表板：
- Docker Container & Host Metrics (ID: 179)
- Docker and system monitoring (ID: 893)
- Node Exporter Full (ID: 1860)

## 数据持久化

监控数据会持久化到以下目录：
- Prometheus: `./data/prometheus/`
- Grafana: `./data/grafana/`

这些目录已添加到 `.gitignore`，不会被提交到版本控制。


