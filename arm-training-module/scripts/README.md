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

