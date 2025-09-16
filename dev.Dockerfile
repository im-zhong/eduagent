# 因为咱们做cicd的时候使用的是咱们自己制作的一个poetry镜像
# 相应的咱们这里制作的镜像最好也基于同一个镜像
# https://docs.docker.com/reference/dockerfile/
FROM python:3.13.7-bookworm

# create user-specific images
# 感觉组是没有必要的，因为一个用户也可能属于多个组，没必要
ARG UID
ARG USER

# 安装 sudo 和必要的工具
# 只有安装了sudo 才有 /etc/sudoers的配置文件
RUN apt update && \
    apt install -y sudo curl && \
    apt autoremove -y && \
    apt clean

# 允许 sudo 组用户无需密码（开发环境专用）
# 覆盖原来的sudo配置，一般是需要密码的
# dev版本的镜像是有这个sudo权限的
# 但是build版本是没有的
# dev的container只有开发环境下，也就是通过dev container才会用
# 所以咱们可以写两个Dockerfile
# 一个是普通的
# 一个是dev
# 然后我们直接build deploy 都是普通的
# 只有dev版本的才会用dev 也就是才有这个命令
RUN echo "%sudo ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/10-nopasswd

# 创建用户和组（确保容器内有 useradd 或 adduser 命令）
# RUN getent group ${GROUP} || groupadd -g ${GID} ${GROUP}
RUN useradd -u ${UID} -m ${USER} -s /bin/bash && \
    usermod -aG sudo ${USER}

USER ${USER}

# 这个工具应该在切换用户之后再进行安装才对
# The RUN instruction will execute any commands to create a new layer on top of the current image.
# RUN python -m pip install poetry==2.1.1
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# add $HOME/.local/bin to your PATH
ENV PATH="/home/${USER}/.local/bin:${PATH}"
# 可能由于docker的overlayfs实现，即使.cache和.venv都挂载到宿主机上，uv仍然无法进行硬连接
# 设置 uv 默认使用 copy 模式
ENV UV_LINK_MODE=copy

# 首先这个镜像要包含本项目的所有代码
# 为了方便，咱们这里直接将整个项目的代码都拷贝到镜像中
# 所有的日志都输出到前台，不要输出到文件里面
# 这样所有的日志都可以通过docker来管理

# The WORKDIR instruction sets the working directory for any RUN, CMD, ENTRYPOINT, COPY and ADD instructions that follow it in the Dockerfile.
WORKDIR /home/${USER}/eduagent

# The COPY instruction copies new files or directories from <src> and adds them to the filesystem of the image at the path <dest>.
# You can use a .dockerignore file to exclude files or directories from the build context.
# COPY . .

# The EXPOSE instruction informs Docker that the container listens on the specified network ports at runtime.
# You can specify whether the port listens on TCP or UDP, and the default is TCP if you don't specify a protocol.
# EXPOSE 8000

# An ENTRYPOINT allows you to configure a container that will run as an executable.
# 必须启动一个进程，否则容器启动就会立刻退出
ENTRYPOINT ["./entrypoint.sh"]

# The CMD instruction sets the command to be executed when running a container from an image.
CMD [ "help" ]
