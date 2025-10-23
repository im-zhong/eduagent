# 监控系统快速入门指南

## 🚀 5 分钟快速开始

### 步骤 1: 启动监控系统

```bash
# 开发环境
docker-compose -f dev.docker-compose.yaml up -d

# 生产环境
docker-compose -f prod.docker-compose.yaml up -d
```

### 步骤 2: 访问 Grafana

1. 打开浏览器访问: http://localhost:3000
2. 使用默认凭据登录:
   - 用户名: `admin`
   - 密码: `admin`
3. 首次登录后修改密码（或点击"Skip"跳过）

### 步骤 3: 查看仪表板

1. 点击左侧菜单 **☰** → **Dashboards**
2. 选择 **Docker Host & Container Overview**
3. 即可看到所有容器的实时监控数据！

## 📊 你将看到什么

- **系统概览**: CPU、内存、磁盘使用情况
- **容器列表**: 所有运行中的容器及其资源使用
- **网络流量**: 实时网络 I/O 统计
- **性能图表**: 历史趋势和峰值分析

## 🔍 常用访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Grafana | http://localhost:3000 | 可视化仪表板 |
| Prometheus | http://localhost:9090 | 时序数据库 |
| cAdvisor | http://localhost:8080 | 容器监控 |

## ⚙️ 自定义端口（可选）

在项目根目录创建 `.env` 文件：

```bash
GRAFANA_PORT=3000
PROMETHEUS_PORT=9090
CADVISOR_PORT=8080

# 修改 Grafana 管理员密码
GRAFANA_ADMIN_PASSWORD=your_secure_password
```

## 🛑 停止监控系统

```bash
# 停止所有服务
docker-compose -f dev.docker-compose.yaml down

# 停止并删除数据卷（谨慎使用）
docker-compose -f dev.docker-compose.yaml down -v
```

## ❓ 遇到问题？

查看完整文档: [README.md](./README.md)

---

**快速开始完成！** 🎉 现在你可以实时监控 EduAgent 系统了。



