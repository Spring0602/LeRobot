# Synthetic calibration fixtures

本目录仅供自动测试使用，不包含任何真实机械臂的标定结果。

每个 JSON 都有 `"synthetic": true` 标记。`calibration_files.py` 默认拒绝这些文件；
只有测试或显式传入 `--allow-synthetic` 的离线检查才会接受。

禁止将本目录复制到：

```text
lerobot-main/.cache/calibration/so101_two
```
