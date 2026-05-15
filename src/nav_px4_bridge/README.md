# nav_px4_bridge

PX4 Offboard 桥接包。

- 订阅: `/nav/cmd_vel`, `/nav/emergency`
- 发布: `/fmu/in/offboard_control_mode`, `/fmu/in/trajectory_setpoint`, `/fmu/in/vehicle_command`

当前实现：

- 持续发布 `OffboardControlMode` 和 `TrajectorySetpoint`
- 支持 `auto_arm` 选项
- 支持 `emergency_action = land|rtl|disarm`
- 默认把 ROS ENU 速度转换成 PX4 NED 速度

后续可继续补充：PX4 状态反馈、offboard 进入确认、失联保护和模式切换状态机。