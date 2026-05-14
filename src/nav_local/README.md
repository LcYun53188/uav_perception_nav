# nav_local

本包为 `nav` 本地导航原型骨架，包含以下 ROS2 节点：

- `local_map_builder`：从 `/oakd/points` 生成局部 2D 占据栅格（原型）
- `local_planner`：基于局部栅格生成短期速度命令 `/nav/cmd_vel`
- `px4_offboard_ctrl`：接收 `/nav/cmd_vel` 并转发到 PX4（stub）
- `safety_monitor`：简单传感器/近障检测，发布 `/nav/emergency`

启动示例：

```bash
# 构建 workspace
colcon build --packages-select nav_local

# 启动本地导航原型
ros2 launch nav_local nav_local.launch.py
```
