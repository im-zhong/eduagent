"""
EduAgent 监控模块

本模块提供基于 Prometheus 和 Grafana 的监控解决方案。

快速开始:
    1. 启动监控服务:
        docker-compose -f dev.docker-compose.yaml up -d
    
    2. 访问 Grafana 仪表板:
        http://localhost:3000 (admin/admin)
    
    3. 查看文档:
        eduagent/monitor/README.md

组件:
    - Prometheus: 时序数据库和监控系统
    - Grafana: 可视化仪表板
    - cAdvisor: Docker 容器监控

配置文件:
    - prometheus/prometheus.yml: Prometheus 配置
    - grafana/provisioning/: Grafana 自动配置
    - grafana/dashboards/: 预配置的仪表板

TODO(Zhou):
    2. design the monitoring metrics which other modules can use
    3. impl the monitoring module, which can be used by other modules to log metrics
"""

__version__ = "1.0.0"
__all__ = []