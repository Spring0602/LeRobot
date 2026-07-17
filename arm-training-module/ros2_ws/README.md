# ROS 2 工作区

ROS 2 集成代码放在 `src/`。构建产生的 `build/`、`install/` 和 `log/` 已加入忽略规则。

计划包含以下功能包：

- `target_bridge`：接收目标类别、像素坐标或三维位置；
- `arm_policy`：封装 LeRobot 策略推理；
- `grasp_executor`：执行抓取/放置并发布结果反馈。

在功能包接口和消息类型确定前，不创建空的 ROS 2 package，以免过早固化架构。

