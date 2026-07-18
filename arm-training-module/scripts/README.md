# 脚本

计划按工作流组织脚本：

```text
check_devices.py   # 检查串口、相机和机械臂连接
calibrate.py       # 启动机械臂标定
teleoperate.py     # 启动主从臂遥操作
record.py          # 采集示教数据
train.py           # 启动策略训练
evaluate.py        # 离线与真机评估
run_policy.py      # 真机策略推理
```

这些文件将在明确设备端口、相机数量和数据集命名后逐步实现。

## Ubuntu 环境安装

在 Ubuntu 共享目录中执行：

```bash
cd "/mnt/hgfs/engineering_files/arm-training-module"
chmod +x scripts/setup_ubuntu.sh
./scripts/setup_ubuntu.sh
```

脚本默认使用同级的 `../lerobot-main`，并在 `~/lerobot-env` 创建虚拟环境。可通过环境变量覆盖：

```bash
LEROBOT_ROOT="$HOME/workspace/lerobot-main" \
LEROBOT_VENV="$HOME/lerobot-env" \
./scripts/setup_ubuntu.sh
```

默认通过阿里云 Wheel 直链安装适用于 Ubuntu x86_64、Python 3.10 的 CPU 版 PyTorch 2.6.0 和 torchvision 0.21.0，适合没有 CUDA 直通的 VMware；其余 Python 依赖默认使用阿里云 PyPI 镜像。若 Python 版本、系统架构或计算后端不同，可通过 `TORCH_WHEEL_URL` 和 `TORCHVISION_WHEEL_URL` 覆盖对应文件地址。

仅检查现有环境：

```bash
source "$HOME/lerobot-env/bin/activate"
python scripts/verify_environment.py
```
