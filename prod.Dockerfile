# production dockerfile, build a user specific image
# refs:
#   - https://docs.docker.com/reference/dockerfile/

FROM python:3.13.7-bookworm

ARG UID
ARG USER

# 安装 sudo 和必要的工具
# 只有安装了sudo 才有 /etc/sudoers的配置文件
RUN apt update && \
    apt install -y curl ncat && \
    apt autoremove -y && \
    apt clean

# 创建用户并设置默认用户
RUN useradd -u ${UID} -m ${USER} -s /bin/bash
USER ${USER}

# The RUN instruction will execute any commands to create a new layer on top of the current image.
# 安装uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# add $HOME/.local/bin to your PATH
ENV PATH="/home/${USER}/.local/bin:${PATH}"
# 由于docker的overlayfs实现，即使.cache和.venv都挂载到宿主机上，uv仍然无法进行硬连接
# 设置 uv 默认使用 copy 模式
ENV UV_LINK_MODE=copy

# The WORKDIR instruction sets the working directory for any RUN, CMD, ENTRYPOINT, COPY and ADD instructions that follow it in the Dockerfile.
WORKDIR /home/${USER}/eduagent

# An ENTRYPOINT allows you to configure a container that will run as an executable.
# 必须启动一个进程，否则容器启动就会立刻退出
ENTRYPOINT ["./entrypoint.sh"]

# The CMD instruction sets the command to be executed when running a container from an image.
CMD [ "help" ]
