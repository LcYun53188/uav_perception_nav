# Foxglove 无固件验证布局

这份布局用于 `ros2 launch uav_bringup mock_px4_validation.launch.py` 场景。
目标是在没有真实 PX4 固件时，尽量完整地看见 OAK-D 感知、VINS、EKF、TF、规划、安全链路、PX4 mock 反馈和控制输出。

当前 mock 验证会启动：

- `px4_mock_node`：模拟 PX4 状态机反馈，发布 `/fmu/out/vehicle_status`。
- `fake_px4_sensors`：发布 `/px4/attitude`、`/px4/imu`、`/gps/fix`、`/px4/odom`。
- 常规 `nav_stack.launch.py`：启动 OAK-D、VINS、EKF、建图、规划、安全监控与 PX4 bridge。

限制：

- 这不是飞行动力学仿真。
- `/px4/attitude` 和 `/px4/imu` 是确定性假数据，只用于让 EKF 与 Foxglove 链路可视化。
- 真机 Offboard 接收、解锁、电机输出和飞控坐标转换仍必须用真实 PX4 或 SITL 验证。

## 1. 启动前确认

先确认以下节点会在同一个 ROS 2 图里出现：

- `px4_mock_node`
- `fake_px4_sensors`
- `px4_comm_bridge`
- `safety_monitor`
- `local_map_builder`
- `local_planner`
- `ekf_filter_node_odom`
- `map_to_odom_identity` 或 `ekf_filter_node_map`

如果开启 GPS 模式，还会多出：

- `ekf_filter_node_map`
- `navsat_transform`

## 2. 推荐面板布局

### 左侧: 3D 场景

放这些主题：

- `/tf`
- `/tf_static`
- `/oakd/points_filtered`
- `/local_map/occupancy`
- `/odometry/local`
- `/vio/odometry`

用途：

- 看 `map -> odom -> base_link` 是否连通
- 看 `base_link -> oakd_imu_link -> oakd_camera_optical_frame` 是否连通
- 看点云和局部栅格是否落在同一坐标系下
- 看局部栅格是否有障碍物
- 看静态外参是否正常发布

### 中间上方: Plot

放这些主题：

- `/nav/safety_status`
- `/nav/emergency`
- `/fmu/out/vehicle_status`
- `/px4/attitude`
- `/px4/imu`

建议展开的字段：

- `safety_status.data`
- `emergency.data`
- `VehicleStatus.arming_state`
- `VehicleStatus.nav_state`
- `/px4/attitude.pose.pose.orientation.x/y/z/w`
- `/px4/imu.angular_velocity.x/y/z`

用途：

- 看安全等级是否从 0 变成 1 或 2
- 看应急是否被触发
- 看 mock PX4 是否从 MANUAL 过渡到 ARMED、OFFBOARD、AUTO_LAND
- 看 fake PX4 姿态和 IMU 是否持续发布

### 中间下方: Raw Messages

放这些主题：

- `/px4/attitude`
- `/px4/imu`
- `/vio/odometry`
- `/odometry/local`
- `/fmu/in/vehicle_command`
- `/fmu/in/offboard_control_mode`
- `/fmu/in/trajectory_setpoint`
- `/nav/cmd_vel`

用途：

- 看控制桥是否在发 PX4 命令
- 看 offboard 心跳是否在持续
- 看规划器速度是否正常进入控制桥

### 右侧: Topic List 或 Message Inspector

重点盯这些主题：

- `/nav/cmd_vel`
- `/nav/safety_status`
- `/nav/emergency`
- `/fmu/out/vehicle_status`
- `/fmu/in/vehicle_command`
- `/px4/attitude`
- `/px4/imu`
- `/odometry/local`
- `/vio/odometry`
- `/px4/odom`
- `/oakd/points`
- `/oakd/points_filtered`

## 3. 一次验证要看的核心链路

### 链路 A: 规划到控制

观察顺序：

1. `/nav/cmd_vel` 出现速度命令
2. `/fmu/in/offboard_control_mode` 持续发心跳
3. `/fmu/in/trajectory_setpoint` 出现对应速度
4. `/fmu/in/vehicle_command` 出现 ARM 或 OFFBOARD 命令

### 链路 B: 安全到应急

观察顺序：

1. `/nav/safety_status` 升高到 2
2. `/nav/emergency` 变成 true
3. `/fmu/in/vehicle_command` 触发 LAND 或 RTL
4. `/fmu/out/vehicle_status` 的 `nav_state` 进入 LAND / RTL 相关状态

### 链路 C: PX4 mock 闭环

观察顺序：

1. `px4_comm_bridge` 收到 `/nav/cmd_vel`
2. `px4_mock_node` 收到 `/fmu/in/vehicle_command`
3. `px4_mock_node` 发布 `/fmu/out/vehicle_status`
4. `px4_state_machine` 推进到 ARM、OFFBOARD、FLYING

### 链路 D: fake PX4 传感器到 EKF

观察顺序：

1. `fake_px4_sensors` 发布 `/px4/attitude`
2. `fake_px4_sensors` 发布 `/px4/imu`
3. `ekf_filter_node_odom` 输出 `/odometry/local`
4. `/tf` 中出现 `map -> odom -> base_link`

### 链路 E: OAK-D 到 VINS 到 EKF

观察顺序：

1. `/oakd/left/image_raw` 和 `/oakd/right/image_raw` 有频率
2. `/oakd/imu/raw` 有频率
3. 移动相机后 `/vio/odometry` 有输出
4. `/odometry/local` 和 `/tf` 持续更新

## 4. 建议的 Foxglove 视图组合

### 方案 1: 标准验证台

- 左: 3D
- 中上: Plot
- 中下: Raw Messages
- 右: Topic List

适合第一次看整条链路。

### 方案 2: 故障注入台

- 左: 3D
- 中: Plot
- 右上: `/nav/emergency`
- 右下: `/fmu/out/vehicle_status`

适合做点云丢失、TF 丢失、命令超时验证。

### 方案 3: 状态机调试台

- 左: `/fmu/out/vehicle_status`
- 中: `/fmu/in/vehicle_command`
- 右: `/nav/safety_status`

适合盯状态转移。

## 5. 关键判断标准

### 正常

- `/tf` 中能看到 `map -> odom -> base_link`
- `/nav/cmd_vel` 有输入时，`/fmu/in/trajectory_setpoint` 也有输出
- `VehicleStatus.arming_state` 能从 DISARMED 走到 ARMED
- `VehicleStatus.nav_state` 能进入 OFFBOARD

### 异常

- `/tf` 断开或 `map -> base_link` 不连续
- `/nav/safety_status` 一直是 2
- `/nav/emergency` 一直是 true
- `/fmu/in/vehicle_command` 没有出现，说明控制桥没接上
- `/fmu/out/vehicle_status` 没有变化，说明 mock PX4 没在工作

## 6. 无固件验证步骤

1. 启动验证环境：

   ```bash
   cd /home/nuc/Program/uav_vision_ws
   source install/setup.bash
   ros2 launch uav_bringup mock_px4_validation.launch.py enable_gps:=false
   ```

2. 启动 Foxglove Bridge：

   ```bash
   source install/setup.bash
   ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765
   ```

3. 在 Foxglove 连接：

   ```text
   ws://localhost:8765
   ```

4. 添加上面推荐的 3D、Plot、Raw Messages、Topic List 面板。
5. 如需强制触发控制链路，可手工发布 `/nav/cmd_vel`。
6. 观察 `/fmu/in/vehicle_command` 和 `/fmu/out/vehicle_status` 是否变化。
7. 观察 `/px4/attitude`、`/px4/imu`、`/odometry/local` 和 `/tf` 是否持续更新。

## 7. 你最应该保存的布局

建议保存一个 Workspace，名称可以是：

- `uav_validation_mock_px4`

里面至少保留：

- 3D 面板
- Plot 面板
- Raw Messages 面板
- Topic List 面板

这样后面做 W2-D10-D11 行为验证时可以直接复用。

## 8. 中文版 Foxglove 逐步配置

下面按中文版界面来配，尽量对应实际按钮名称。

### 8.1 新建工作区

1. 打开 Foxglove。
2. 进入 `工作区`。
3. 点击 `新建工作区`。
4. 命名为 `uav_validation_mock_px4`。
5. 保存。

### 8.2 连接数据源

1. 点击左上角 `连接`。
2. 选择当前 ROS 2 数据源。
3. 确认状态栏显示连接成功。
4. 打开话题列表，确认能看到：
   - `/tf`
   - `/tf_static`
   - `/nav/cmd_vel`
   - `/nav/safety_status`
   - `/nav/emergency`
   - `/px4/attitude`
   - `/px4/imu`
   - `/odometry/local`
   - `/fmu/out/vehicle_status`

### 8.3 添加 3D 面板

1. 点击 `添加面板`。
2. 选择 `3D`。
3. 在右侧配置区添加数据：
   - `Transforms` → `/tf`
   - `Static Transforms` → `/tf_static`
   - `PointCloud2` → `/oakd/points_filtered`
   - `Occupancy Grid` → `/local_map/occupancy`
   - `Odometry` → `/odometry/local`
   - `Odometry` → `/vio/odometry`
4. 如果界面提供 `固定坐标系`，优先选 `map`。
5. 如果提供 `参考帧`，设置为 `base_link`。

你要确认的点：

- 机器人模型或坐标轴在移动时方向正确。
- `map -> odom -> base_link` 没断。
- 地图栅格和 TF 位置一致。

### 8.4 添加 Plot 面板

1. 点击 `添加面板`。
2. 选择 `图表`。
3. 分别添加下面主题：
   - `/nav/safety_status`
   - `/nav/emergency`
   - `/fmu/out/vehicle_status`
   - `/px4/attitude`
   - `/px4/imu`
4. 对单值类型，直接选择 `data` 字段。
5. 对 `VehicleStatus`，展开并勾选：
   - `arming_state`
   - `nav_state`

建议：

- `nav/safety_status` 用一条线看等级变化。
- `nav/emergency` 用布尔值看应急是否触发。
- `arming_state` 和 `nav_state` 放同一张图，便于看状态机跳转。

### 8.5 添加 Raw Messages 面板

1. 点击 `添加面板`。
2. 选择 `原始消息`。
3. 依次添加：
   - `/nav/cmd_vel`
   - `/px4/attitude`
   - `/px4/imu`
   - `/vio/odometry`
   - `/odometry/local`
   - `/fmu/in/offboard_control_mode`
   - `/fmu/in/trajectory_setpoint`
   - `/fmu/in/vehicle_command`
4. 如果可以过滤显示，只保留最新消息。

你要重点看：

- `/nav/cmd_vel` 有没有被发出。
- `/fmu/in/trajectory_setpoint` 是否跟着变化。
- `/fmu/in/vehicle_command` 是否出现 ARM、OFFBOARD、LAND 命令。

### 8.6 添加 话题列表 面板

1. 点击 `添加面板`。
2. 选择 `话题列表`。
3. 置顶或收藏这些话题：
   - `/nav/cmd_vel`
   - `/nav/safety_status`
   - `/nav/emergency`
   - `/px4/attitude`
   - `/px4/imu`
   - `/vio/odometry`
   - `/odometry/local`
   - `/fmu/out/vehicle_status`
   - `/fmu/in/vehicle_command`

这个面板主要用于快速确认某个话题是否在发。

### 8.7 建议的检查顺序

1. 先看 `话题列表`，确认所有关键话题都存在。
2. 再看 `3D`，确认 TF 和地图正常。
3. 再看 `图表`，确认安全状态和 PX4 状态变化。
4. 最后看 `原始消息`，确认控制命令确实发到了下游。

### 8.8 你这套环境的最小验收

在 mock 验证环境里，满足下面几条就算 Foxglove 配置正确：

- `/tf` 中能看到 `map -> odom -> base_link`
- `/px4/attitude` 和 `/px4/imu` 持续发布
- `/odometry/local` 持续发布
- `/nav/cmd_vel` 发出后，`/fmu/in/trajectory_setpoint` 有响应
- `/nav/safety_status` 变成 `2` 后，`/nav/emergency` 变成 `true`
- `/fmu/out/vehicle_status` 的 `arming_state` 和 `nav_state` 有变化
