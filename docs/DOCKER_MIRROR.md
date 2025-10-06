# Docker 镜像加速配置指南

如果你在拉取 Docker 镜像时遇到网络问题（超时、连接失败等），可以配置镜像加速器。

## Windows Docker Desktop 配置

### 方法 1: 通过 Docker Desktop GUI 配置

1. 打开 Docker Desktop
2. 点击右上角的 ⚙️ (Settings)
3. 选择 **Docker Engine**
4. 在 JSON 配置中添加镜像源：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://docker.nju.edu.cn"
  ]
}
```

5. 点击 **Apply & restart**

### 方法 2: 直接编辑配置文件

配置文件位置: `C:\Users\你的用户名\.docker\daemon.json`

如果文件不存在，创建它并添加以下内容：

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://docker.nju.edu.cn"
  ]
}
```

保存后重启 Docker Desktop。

## 可用的镜像源

### 国内镜像源（2024-2025 可用）

| 镜像源 | 地址 | 说明 |
|--------|------|------|
| DaoCloud | https://docker.m.daocloud.io | 推荐，稳定 |
| Docker Proxy | https://dockerproxy.com | 社区维护 |
| 中科大 | https://docker.mirrors.ustc.edu.cn | 教育网友好 |
| 南京大学 | https://docker.nju.edu.cn | 教育网友好 |

**注意**: 阿里云、腾讯云等商业云服务商的镜像加速器通常需要注册账号获取专属地址。

### 阿里云镜像加速器（推荐）

1. 访问 https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
2. 登录阿里云账号（没有的话需要注册）
3. 获取你的专属加速器地址（形如 `https://xxxxx.mirror.aliyuncs.com`）
4. 按照上面的方法配置到 Docker 中

## 验证配置

### 1. 检查配置是否生效

打开 PowerShell 运行：

```powershell
docker info | Select-String "Registry Mirrors" -Context 0,5
```

或者：

```powershell
docker info
```

在输出中查找 `Registry Mirrors` 部分，应该能看到你配置的镜像源。

### 2. 测试拉取镜像

```powershell
docker pull hello-world
```

如果能成功拉取，说明配置生效。

## 重新构建 EduAgent

配置好镜像加速后，重新构建项目：

```powershell
# 清理之前失败的构建
docker compose -f dev.docker-compose.yaml down

# 重新构建并启动
docker compose -f dev.docker-compose.yaml up -d --build
```

## 使用代理（可选）

如果你有代理服务器，也可以配置 Docker 使用代理：

### 配置方法

在 Docker Engine 配置中添加：

```json
{
  "proxies": {
    "http-proxy": "http://proxy.example.com:8080",
    "https-proxy": "http://proxy.example.com:8080",
    "no-proxy": "localhost,127.0.0.1"
  },
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ]
}
```

## 替代方案：使用国内基础镜像

如果镜像加速仍然不理想，可以修改 Dockerfile 使用国内镜像源。

### 修改 Python 镜像源

编辑 `dev.Dockerfile`，在安装依赖前添加：

```dockerfile
# 使用清华大学 PyPI 镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 使用国内 APT 镜像源

在 `dev.Dockerfile` 中添加：

```dockerfile
# 使用阿里云 Debian 镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
```

## 常见问题

### Q: 配置后仍然很慢怎么办？

A: 尝试以下方法：
1. 多配置几个镜像源
2. 使用代理
3. 在网络较好的时间段（如凌晨）拉取镜像
4. 考虑使用离线镜像包

### Q: 某些镜像源无法访问？

A: 镜像源可能会失效或维护，可以：
1. 从列表中删除失效的源
2. 尝试其他可用的源
3. 使用阿里云或腾讯云的专属加速器

### Q: 如何查看当前使用的镜像源？

A: 运行 `docker info` 查看 `Registry Mirrors` 部分。

### Q: 企业内网环境怎么办？

A: 咨询你的网络管理员，可能需要：
1. 配置企业代理
2. 使用企业内部的 Docker 镜像仓库
3. 配置防火墙规则

## 相关链接

- [Docker 官方文档 - Registry Mirrors](https://docs.docker.com/registry/recipes/mirror/)
- [DaoCloud 镜像站](https://github.com/DaoCloud/public-image-mirror)
- [阿里云容器镜像服务](https://cr.console.aliyun.com/)


