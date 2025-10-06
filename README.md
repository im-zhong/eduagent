# EduAgent

[![codecov](https://codecov.io/gh/im-zhong/eduagent/branch/main/graph/badge.svg)](https://codecov.io/gh/im-zhong/eduagent)

Education Agent: An Intelligent Question Generation System

Assist educators and learners by automatically generating educational questions from text materials or knowledge bases. It leverages natural language processing (NLP) and modern AI models to create meaningful and context-aware questions.

## Quick Start

### 0. 配置 Docker 镜像加速（中国大陆用户必须）

如果你在中国大陆，**必须先配置 Docker 镜像加速器**，否则无法拉取镜像。

1. 打开 Docker Desktop → Settings → Docker Engine
2. 添加以下配置：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

3. 点击 Apply & restart

详细配置方法见 [Docker 镜像加速配置指南](docs/DOCKER_MIRROR.md)

### 1. 配置环境变量

**Windows PowerShell:**
```powershell
Copy-Item env.template .env
```

**Linux/Mac:**
```bash
cp env.template .env
```

根据需要编辑 `.env` 文件修改配置。

### 2. 启动服务

**开发环境:**
```bash
docker compose -f dev.docker-compose.yaml up -d
```

**生产环境:**
```bash
docker compose -f prod.docker-compose.yaml up -d
```

### 3. 访问应用

- **API**: http://localhost:8000
- **UI**: http://localhost:8501
- **Grafana 监控**: http://localhost:3000 (用户名: admin, 密码: admin)
- **Prometheus**: http://localhost:9090

## 监控系统

项目集成了 Prometheus + Grafana + cAdvisor 监控系统，可以实时监控容器和主机性能。详见 [监控文档](docs/MONITORING.md)。

## 文档

- [Docker 镜像加速配置](docs/DOCKER_MIRROR.md) 🚀 中国大陆用户必读
- [Windows 系统配置指南](docs/WINDOWS_SETUP.md) ⭐ Windows 用户必读
- [监控系统使用指南](docs/MONITORING.md)
- [开发提示](docs/TIPS.md)
- [贡献指南](CONTRIBUTOR.md)

## Contributors

YunX xyiu.run@gmail.com  
Eon-Flight eon3209036707@gmail.com  
G_shang_hui 271278430@qq.com  
Zhou lz4530_j@163.com
