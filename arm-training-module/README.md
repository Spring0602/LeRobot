# 园林机器人机械臂训练模块

本项目负责园林场景下机械臂的示教数据采集、策略训练、真机推理、抓取执行和结果评估。底层训练与设备能力复用同级目录中的 `../lerobot-main`，项目业务代码与 LeRobot 上游源码保持分离。

## 目录结构

```text
arm-training-module/
├── configs/       # 机械臂、相机、数据采集及训练参数
├── scripts/       # 标定、遥操作、采集、训练、评估与部署脚本
├── ros2_ws/src/   # ROS 2 功能包（后续集成目标检测与抓取闭环）
├── datasets/      # 本地示教数据；仅提交说明和小型元数据
├── outputs/       # 模型检查点、日志和评估结果
├── tests/         # 模块测试
└── docs/          # 设计、操作和实验记录
```

## 与 LeRobot 环境连接

在 Ubuntu 中进入已经配置好的 Python/Conda 环境，然后以可编辑模式安装同级 LeRobot：

```bash
cd /path/to/工程文件/lerobot-main
pip install -e ".[feetech]"
```

完成后，在本项目任意脚本中均可使用 `lerobot`：

```python
from lerobot.common.policies.diffusion.modeling_diffusion import DiffusionPolicy
```

## 建议实施顺序

1. 在 `configs/` 固化 SO-101 双臂、串口和相机配置。
2. 在 `scripts/` 完成设备检查、标定和遥操作验证。
3. 采集枯枝/垃圾抓取示教数据，并记录任务、场景和成功标准。
4. 使用 ACT 或 Diffusion Policy 建立第一版模仿学习基线。
5. 完成真机推理和抓取成功率评估。
6. 在 `ros2_ws/src/` 接入目标检测、坐标转换及抓取反馈节点。

## 第一阶段状态

第一阶段可离线完成的开发任务已完成。四块控制板的序列号和稳定端口映射已从
原 Jetson 规则恢复，详情及 Ubuntu 验收命令见
`docs/第一阶段开发验收报告.md`。真实标定、遥操作和相机画面验收仍需实体硬件。

当前无法接触实体设备时，后续工作按
`docs/无硬件软件开发计划.md` 执行；该计划使用模拟数据和离线测试推进软件开发，
不会把模拟结果当作真机验收。

## 数据管理约定

- 大型数据集、视频、模型权重和训练日志不提交 Git。
- 数据集应保留任务说明、采集参数、版本和统计信息。
- 密钥、设备私有配置及绝对路径不要写入仓库。
