# 全向轮启动包说明

`omni_bringup` 是地面全向轮机器人的独立启动入口，不依赖 `uav_bringup`，也不会启动 `px4_comm_bridge`。

## 启动范围

默认启动：

- OAK-D 感知入口，可通过参数关闭
- `nav_mapping/local_map_builder`
- `nav_planning/se2_dwa_local_planner`
- `nav_safety/safety_monitor`

可选启动：

- MID360 点云链路
- DWB bridge
- `ground_serial_bridge` 串口底盘桥接

## 常用命令

仅启动全向轮导航层，不发送到底盘：

```bash
./scripts/with_venv.sh ros2 launch omni_bringup omni_nav.launch.py
```

启用串口底盘桥接：

```bash
./scripts/with_venv.sh ros2 launch omni_bringup omni_nav.launch.py enable_ground_serial_bridge:=true
```

使用 MID360 作为障碍点云：

```bash
./scripts/with_venv.sh ros2 launch omni_bringup omni_nav.launch.py enable_mid360:=true obstacle_pointcloud_source:=mid360
```

同时使用 OAK-D 和 MID360：

```bash
./scripts/with_venv.sh ros2 launch omni_bringup omni_nav.launch.py enable_mid360:=true obstacle_pointcloud_source:=both
```

## 主要话题

输入：

```text
/oakd/points_filtered
/mid360/points
/nav/goal_pose
```

输出：

```text
/local_map/occupancy
/nav/cmd_vel
/nav/emergency
/nav/safety_status
```

启用底盘桥接后，`ground_serial_bridge` 应订阅：

```text
/nav/cmd_vel
/nav/emergency
/nav/safety_status
```

串口桥接节点发布：

```text
/base/state
/base/status
/base/diagnostics
```

`ground_serial_bridge` 会在串口发送前把 `/nav/cmd_vel` 按 `header.frame_id` 转到 `command_output_frame`，默认是 `base_link`。因此下位机不需要维护自己的世界坐标系，也不应按下位机漂移的世界系解释速度方向。

推荐约定：

```text
上位机导航/定位：维护 map、odom、base_link
串口桥接：把 map/odom 速度转成 base_link 车体系速度
下位机：只按车体系 vx、vy、wz 控制电机
```

如果 TF 不可用，桥接节点会下发 0 速度，避免继续按错误方向执行。

如果下位机无法改成车体系速度接口，仍然必须按自己的漂移世界系执行速度，则可以开启动态补偿：

```yaml
mcu_velocity_frame: mcu_world
require_feedback: true
require_mcu_yaw_for_mcu_world: true
```

此模式要求下位机状态帧在原 10 字节 payload 后追加：

```text
yaw_mrad int16
```

完整状态 payload 变为：

```text
enabled uint8
estop uint8
vx_mm_s int16
vy_mm_s int16
wz_mrad_s int16
fault_code uint16
yaw_mrad int16
```

补偿流程：

```text
上位机 /nav/cmd_vel
  -> TF 转 mcu_yaw_reference_frame，例如 odom/map
  -> 从 TF 获取 yaw_base
  -> 从下位机状态帧获取 yaw_mcu
  -> 计算 yaw_error = yaw_mcu - yaw_base
  -> 使用 yaw_error 转到 mcu_world
  -> 串口发送给下位机
```

对应配置：

```yaml
mcu_yaw_reference_frame: odom
mcu_yaw_compensation_mode: yaw_error
```

`yaw_base` 来自 `mcu_yaw_reference_frame -> base_link` 的 TF。车体真实旋转时，`yaw_base` 和 `yaw_mcu` 应该一起变化；只有二者的差值才作为下位机坐标漂移补偿。

如果你的下位机接口实际需要“先转成 `base_link`，再用下位机 yaw 直接转到下位机世界系”，可以切回：

```yaml
mcu_yaw_compensation_mode: mcu_yaw
```

如果下位机 yaw 符号相反，设置：

```yaml
mcu_yaw_sign: -1.0
```

如果下位机 yaw 有固定安装/初始偏差，可设置：

```yaml
mcu_yaw_offset_rad: 0.0
```

若希望启动时把当前下位机 yaw 视为 0，可设置：

```yaml
mcu_yaw_auto_zero: true
```

## 配置文件

- `src/omni_bringup/config/omni_nav_stack.yaml`
- `src/omni_bringup/config/ground_serial_bridge.yaml`
- `src/ground_serial_bridge/config/ground_serial_bridge.yaml`

`omni_nav_stack.yaml` 中的速度、加速度、避障半径已经按地面全向轮做了初始收敛。上车前仍需按底盘能力重新标定：

```text
max_vel_x
max_vel_y
max_yaw_rate
max_acc_x
max_acc_y
max_yaw_accel
robot_radius
stop_clearance
```

## 串口回传帧率

控制发送建议保持 `20-50Hz`。底盘状态回传建议不低于 `10Hz`，工程上更推荐 `20Hz`，这样故障码、使能状态和实际速度不会明显滞后。

`ground_serial_bridge` 默认 `require_feedback: false`，方便无回传协议时先调通速度下发。真实上车时建议改为：

```yaml
require_feedback: true
min_feedback_rate_hz: 10.0
feedback_timeout_sec: 0.3
```

启用后，如果底盘回传超时或统计帧率低于阈值，节点会进入 `FAULT` 并持续发送停车/急停帧。
