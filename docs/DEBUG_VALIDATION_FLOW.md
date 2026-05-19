# 调试链路与逐层验证流程

本文档用于按依赖关系逐层验证项目可行性。原则是：每一层只在上一层通过后继续；如果某层失败，先不要启动更高层，避免把传感器、TF、定位、规划问题混在一起。

OAK-D / MID360 单设备启动细节见 [SENSOR_DEBUG_GUIDE.md](./SENSOR_DEBUG_GUIDE.md)。

## 分层总览

| 层级 | 目标 | 启动入口 | 通过标准 |
|------|------|---------|---------|
| L0 | 环境、submodule、构建可用 | `colcon build` / `--show-args` | 包可编译，launch 参数能列出 |
| L1 | 单传感器数据可用 | OAK-D 或 MID360 独立启动 | 原始话题持续发布，频率稳定 |
| L2 | 单里程计可用 | VINS-Fusion 或 FAST-LIO2 | `/vio/odometry` 或 `/lio/odometry` 输出连续 |
| L3 | EKF 融合定位和 TF 可用 | `run_nav_stack.sh oakd` / `mid360_lio` / `mid360_only` | `/odometry/local`、`map -> odom -> base_link` 正常 |
| L4 | 避障点云进入局部地图 | `oakd` / `mid360` / `both` | `/local_map/occupancy` 随障碍变化 |
| L5 | 局部规划可用 | 导航栈 + 目标输入 | `/nav/cmd_vel` 非异常、方向合理 |
| L6 | 安全监控可用 | 导航栈 | `/nav/emergency` 状态符合障碍/超时情况 |
| L7 | PX4 桥接可用 | 导航栈 + PX4 | `/fmu/in/*` 有输出，offboard 前先地面验证 |
| L8 | 场景回放可复现 | ros2 bag | 离线回放能复现定位、地图和安全输出 |

## L0 环境与构建

```bash
cd /home/nuc/Program/uav_vision_ws
source .venv/bin/activate
source install/setup.bash

git submodule status --recursive
./scripts/with_venv.sh colcon build --packages-select uav_bringup --symlink-install
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh ros2 launch uav_bringup nav_stack.launch.py --show-args
```

如果启用 MID360 / FAST-LIO2，先确认：

```bash
./scripts/apply_vendor_patches.sh
./scripts/build_livox_sdk2.sh
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh colcon build \
  --packages-select livox_ros_driver2 fast_lio nav_mapping uav_bringup \
  --symlink-install
```

通过标准：

- `nav_stack.launch.py --show-args` 能列出 `enable_oakd_perception`、`enable_mid360`、`enable_lio`、`obstacle_pointcloud_source`。
- `git status --short` 中 MID360 相关 submodule 显示小写 `m` 属于 patch 已应用后的预期状态。

## L1 单传感器验证

### OAK-D

```bash
./scripts/run_oakd_unified.sh
```

另一个终端检查：

```bash
./scripts/with_venv.sh ros2 topic list | grep -E "/oakd/imu|/oakd/.*/image_raw|/oakd/points"
./scripts/with_venv.sh ros2 topic hz /oakd/imu/raw
./scripts/with_venv.sh ros2 topic hz /oakd/points
```

通过标准：

- `/oakd/imu/raw`、左右图像、`/oakd/points` 或 `/oakd/points_filtered` 持续存在。
- 没有 `X_LINK_DEVICE_ALREADY_IN_USE`。

### MID360

```bash
./scripts/run_nav_stack.sh mid360 enable_oakd_perception:=false enable_imu_fusion:=false enable_vins:=false
```

另一个终端检查：

```bash
./scripts/with_venv.sh ros2 topic list | grep -E "/livox|/mid360"
./scripts/with_venv.sh ros2 topic hz /livox/lidar
./scripts/with_venv.sh ros2 topic hz /livox/imu
./scripts/with_venv.sh ros2 topic hz /mid360/points
```

通过标准：

- `/livox/lidar` 和 `/livox/imu` 持续发布。
- `/mid360/points` 已由 `livox_custom_to_pointcloud2` 转换生成。
- RViz 中以 `mid360_link` 或 `map` 为 Fixed Frame 能看到点云。

## L2 单里程计验证

### VINS-Fusion

```bash
./scripts/run_nav_stack.sh oakd enable_gps:=false
```

检查：

```bash
./scripts/with_venv.sh ros2 topic hz /vio/odometry
./scripts/with_venv.sh ros2 topic echo /vio/odometry --once
```

通过标准：

- 相机轻微运动后 `/vio/odometry` 连续输出。
- 静止时位置漂移在可接受范围内，没有频繁重初始化。

### FAST-LIO2

```bash
./scripts/run_nav_stack.sh mid360_only
```

检查：

```bash
./scripts/with_venv.sh ros2 topic hz /lio/odometry
./scripts/with_venv.sh ros2 topic echo /lio/odometry --once
```

通过标准：

- `/lio/odometry` 持续输出。
- 初始姿态和移动方向与实际运动一致。

## L3 EKF 与 TF 验证

OAK-D VIO 定位链路：

```bash
./scripts/run_nav_stack.sh oakd
```

OAK-D VIO + MID360 LIO 并列融合链路：

```bash
./scripts/run_nav_stack.sh mid360_lio
```

纯 MID360/LIO 链路：

```bash
./scripts/run_nav_stack.sh mid360_only
```

检查：

```bash
./scripts/with_venv.sh ros2 topic hz /odometry/local
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map base_link
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link oakd_imu_link
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link mid360_link
```

通过标准：

- `/odometry/local` 持续输出。
- `map -> odom -> base_link` 连通。
- 启用 OAK-D 时 `base_link -> oakd_imu_link -> oakd_camera_optical_frame` 连通。
- 启用 MID360 时 `base_link -> mid360_link` 连通，外参方向正确。

## L4 避障点云与局部地图

分别验证三种点云源：

```bash
./scripts/run_nav_stack.sh oakd
./scripts/run_nav_stack.sh mid360
./scripts/run_nav_stack.sh both
```

检查：

```bash
./scripts/with_venv.sh ros2 topic hz /local_map/occupancy
./scripts/with_venv.sh ros2 topic echo /local_map/occupancy --once
```

RViz 添加：

```text
TF
/oakd/points_filtered
/mid360/points
/perception/obstacle_points
/local_map/occupancy
```

通过标准：

- `oakd` 模式下 `/local_map/occupancy` 能反映 OAK-D 前方障碍。
- `mid360` 模式下局部地图来自 `/mid360/points`。
- `both` 模式下 `/perception/obstacle_points` 持续发布，局部地图不因某一路短暂丢帧立即失效。

## L5 局部规划

在 L4 通过后检查规划输出：

```bash
./scripts/with_venv.sh ros2 topic hz /nav/cmd_vel
./scripts/with_venv.sh ros2 topic echo /nav/cmd_vel --once
```

通过标准：

- 有目标且安全状态允许时，`/nav/cmd_vel` 有非零速度输出。
- 无目标、地图超时或触发急停时，速度输出应降为安全值。
- `linear.x/y` 符合 ENU 平面运动预期，`angular.z` 符合 yaw rate 预期。

## L6 安全监控

检查：

```bash
./scripts/with_venv.sh ros2 topic echo /nav/emergency
./scripts/with_venv.sh ros2 topic echo /nav/safety_status --once
```

通过标准：

- 点云、TF、里程计正常时 `/nav/emergency` 不应误触发。
- 遮挡近距离障碍、断开点云或停止定位输入时，应进入安全状态。

## L7 PX4 桥接

仅在前面层级都通过后再连接 PX4。地面阶段先检查话题，不直接起飞：

```bash
./scripts/with_venv.sh ros2 topic list | grep -E "/px4|/fmu/in"
./scripts/with_venv.sh ros2 topic echo /px4/attitude --once
./scripts/with_venv.sh ros2 topic echo /px4/imu --once
./scripts/with_venv.sh ros2 topic list | grep "/fmu/in"
```

通过标准：

- PX4 输入 `/px4/attitude`、`/px4/imu` 可用。
- `/fmu/in/*` 控制话题有输出。
- Offboard 前确认 `/nav/emergency` 为安全状态，且 `/nav/cmd_vel` 不异常。

## L8 Bag 录制与回放

系统级记录：

```bash
./scripts/with_venv.sh ros2 bag record -o nav_validation \
  /vio/odometry /lio/odometry /odometry/local \
  /oakd/points_filtered /mid360/points /perception/obstacle_points \
  /local_map/occupancy /nav/cmd_vel /nav/emergency \
  /tf /tf_static
```

回放：

```bash
./scripts/with_venv.sh ros2 bag play nav_validation
```

通过标准：

- 回放中能复现定位、TF、局部地图和安全状态。
- 若在线失败但回放正常，优先查硬件、网络、时间同步。
- 若回放也失败，优先查算法参数、TF、话题名和 frame_id。

## 推荐执行顺序

OAK-D VIO 链路：

```text
L0 -> L1 OAK-D -> L2 VINS -> L3 EKF/TF -> L4 oakd map -> L5 planner -> L6 safety -> L7 PX4
```

MID360 替代点云：

```text
L0 -> L1 MID360 -> L4 mid360 map -> L6 safety -> L5 planner
```

MID360 + FAST-LIO2 LIO 链路：

```text
L0 -> L1 MID360 -> L2 FAST-LIO2 -> L3 EKF/TF -> L4 map -> L5 planner -> L6 safety
```

双点云融合：

```text
L0 -> L1 OAK-D + L1 MID360 -> L4 both map -> L5 planner -> L6 safety
```

VIO 和 LIO 在定位层是并列关系：`/vio/odometry` 与 `/lio/odometry` 都是 EKF 的里程计输入，是否启用由当前模式决定，不把其中一路定义为另一边的主/备。每次只改变一个变量：点云源、是否启用 VINS、是否启用 LIO、是否启用 GPS、是否关闭 OAK-D。这样可以快速判断问题来自硬件、里程计、TF、局部地图、规划还是 PX4 桥接。
