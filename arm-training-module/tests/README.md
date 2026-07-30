# 测试

运行全部软件测试：

```bash
cd "/mnt/hgfs/engineering_files/arm-training-module"
python -m unittest discover -s tests -v
```

`fixtures/calibration_synthetic/` 中的 JSON 只用于测试，均带 `synthetic` 标记，
不得复制到 LeRobot 的真实标定缓存。

动作安全测试不依赖 PyTorch、串口或机械臂，覆盖边界、越界、突变、NaN、Inf、
错误维度、控制频率、双臂拆分和真实范围缺失时拒绝输出。

测试将覆盖配置加载、数据字段转换、策略输入输出形状、坐标转换和安全限位。涉及真机的测试应显式标记，避免在普通测试中驱动机械臂。
