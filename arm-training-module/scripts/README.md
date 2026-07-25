# 脚本

计划按工作流组织脚本：

```text
check_devices.py   # 只读检查串口、稳定链接和访问权限（已实现）
device_config.py   # 校验序列号映射、udev 规则及在线别名（已实现）
stage1_preflight.py # 第一阶段只读总体验收（已实现）
calibration_files.py # 只读校验和备份标定文件（已实现）
calibrate.py       # 真实标定包装器（等待硬件和上游单臂隔离方案）
teleoperate.py     # 启动主从臂遥操作
record.py          # 采集示教数据
train.py           # 启动策略训练
evaluate.py        # 离线与真机评估
run_policy.py      # 真机策略推理
```

这些文件将在明确设备端口、相机数量和数据集命名后逐步实现。

稳定端口规则：

```bash
python scripts/device_config.py
chmod +x scripts/install_udev_rules.sh
./scripts/install_udev_rules.sh
python scripts/device_config.py --live
```

第一条命令只做离线一致性校验。安装规则和 `--live` 验证须在 Ubuntu
连接四块控制板后执行。正式规则使用 `dialout` 组和 `0660` 权限，不沿用旧规则的
`0777`。

第一阶段只读验收：

```bash
python scripts/stage1_preflight.py
```

返回码 `2` 表示仍有硬件验收项阻塞；脚本不会连接电机总线或发送动作。

设备盘点：

```bash
source "$HOME/lerobot-env/bin/activate"
cd "/mnt/hgfs/engineering_files/arm-training-module"
python scripts/check_devices.py
```

未发现候选串口时脚本返回状态码 `2`，表示等待硬件或 VMware USB 直通，不代表脚本异常。

标定文件状态与备份：

```bash
python scripts/calibration_files.py status
python scripts/calibration_files.py backup
```

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
