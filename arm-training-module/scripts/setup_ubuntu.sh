#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODULE_ROOT="$(dirname -- "$SCRIPT_DIR")"
WORKSPACE_ROOT="$(dirname -- "$MODULE_ROOT")"
LEROBOT_ROOT="${LEROBOT_ROOT:-$WORKSPACE_ROOT/lerobot-main}"
VENV_DIR="${LEROBOT_VENV:-$HOME/lerobot-env}"
PYPI_INDEX_URL="${PYPI_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
TORCH_WHEEL_URL="${TORCH_WHEEL_URL:-https://mirrors.aliyun.com/pytorch-wheels/cpu/torch-2.6.0%2Bcpu-cp310-cp310-linux_x86_64.whl}"
TORCHVISION_WHEEL_URL="${TORCHVISION_WHEEL_URL:-https://mirrors.aliyun.com/pytorch-wheels/cpu/torchvision-0.21.0%2Bcpu-cp310-cp310-linux_x86_64.whl}"

if [[ ! -f "$LEROBOT_ROOT/pyproject.toml" ]]; then
    echo "未找到 LeRobot: $LEROBOT_ROOT" >&2
    echo "如果目录不在模块同级，请设置 LEROBOT_ROOT 后重试。" >&2
    exit 1
fi

echo "LeRobot 目录: $LEROBOT_ROOT"
echo "虚拟环境目录: $VENV_DIR"

sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    ffmpeg \
    git \
    libgl1 \
    libglib2.0-0 \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv

if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install \
    --upgrade pip setuptools wheel \
    --index-url "$PYPI_INDEX_URL" \
    --timeout 1000 \
    --retries 20

# 阿里云 PyTorch 镜像是 Wheel 文件目录，不是 pip Simple Index，因此使用 Wheel 直链。
python -m pip install \
    "$TORCH_WHEEL_URL" \
    "$TORCHVISION_WHEEL_URL" \
    --index-url "$PYPI_INDEX_URL" \
    --timeout 1000 \
    --retries 20

python -m pip install \
    --editable "$LEROBOT_ROOT[feetech,dev,test]" \
    ruff \
    --index-url "$PYPI_INDEX_URL" \
    --timeout 1000 \
    --retries 20

python "$SCRIPT_DIR/verify_environment.py"

echo
echo "环境安装完成。以后打开终端先执行："
echo "source \"$VENV_DIR/bin/activate\""
