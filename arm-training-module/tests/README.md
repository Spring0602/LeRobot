# 测试

运行全部软件测试：

```bash
cd "/mnt/hgfs/engineering_files/arm-training-module"
python -m unittest discover -s tests -v
```

`fixtures/calibration_synthetic/` 中的 JSON 只用于测试，均带 `synthetic` 标记，
不得复制到 LeRobot 的真实标定缓存。

测试将覆盖配置加载、数据字段转换、策略输入输出形状、坐标转换和安全限位。涉及真机的测试应显式标记，避免在普通测试中驱动机械臂。
