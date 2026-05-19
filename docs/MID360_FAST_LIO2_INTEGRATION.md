# MID360 + FAST-LIO2 接入指南

本文档说明如何在当前工作区接入 Livox MID360，并使用 FAST-LIO2 提供激光惯性里程计，同时让 MID360 点云替代或补充 OAK-D 深度点云用于避障和局部地图构建。

## 架构

默认链路：

```text
MID360
  -> livox_ros_driver2
  -> /livox/lidar                  livox_ros_driver2/CustomMsg
  -> /livox/imu                    sensor_msgs/Imu

/livox/lidar
  -> livox_custom_to_pointcloud2
  -> /mid360/points                sensor_msgs/PointCloud2
  -> local_map_builder / safety_monitor

/livox/lidar + /livox/imu
  -> FAST-LIO2
  -> /lio/odometry                 nav_msgs/Odometry
  -> robot_localization EKF
```

OAK-D 仍负责 VINS：

```text
OAK-D stereo + IMU -> VINS-Fusion -> /vio/odometry -> EKF
```

MID360 可以只用于避障，也可以通过 FAST-LIO2 提供与 VIO 并列的 LIO 定位输入。

## 源码依赖

当前工作区已引入：

```text
src/livox_ros_driver2
src/FAST_LIO_ROS2
third_party/Livox-SDK2
```

新环境拉取时执行：

```bash
git submodule update --init --recursive
./scripts/apply_vendor_patches.sh
```

submodule + patch 的完整复刻和维护流程见：

```text
docs/SUBMODULE_PATCH_REPRODUCTION.md
```

## 构建

所有命令统一使用项目虚拟环境包装脚本：

```bash
./scripts/with_venv.sh <command>
```

先构建 Livox-SDK2 到本地 `.deps/livox_sdk2`：

```bash
./scripts/build_livox_sdk2.sh
```

再构建 ROS 包：

```bash
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh colcon build \
  --packages-select livox_ros_driver2 fast_lio nav_mapping uav_bringup \
  --symlink-install
```

验证可执行文件：

```bash
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh ros2 pkg executables livox_ros_driver2
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh ros2 pkg executables fast_lio
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh ros2 pkg executables nav_mapping
```

应至少看到：

```text
livox_ros_driver2 livox_ros_driver2_node
fast_lio fastlio_mapping
nav_mapping livox_custom_to_pointcloud2
```

## 网络配置

修改：

```text
src/livox_ros_driver2/config/MID360_config.json
```

重点字段：

```json
"host_net_info": {
  "cmd_data_ip": "192.168.1.5",
  "push_msg_ip": "192.168.1.5",
  "point_data_ip": "192.168.1.5",
  "imu_data_ip": "192.168.1.5"
},
"lidar_configs": [
  {
    "ip": "192.168.1.12"
  }
]
```

其中：

- `host_net_info.*_ip`：机载电脑有线网口 IP。
- `lidar_configs[0].ip`：MID360 设备 IP。

示例：如果机载电脑网口是 `192.168.1.50`，MID360 是 `192.168.1.12`，则把所有 host IP 改成 `192.168.1.50`。

检查连通性：

```bash
ping 192.168.1.12
```

## 启动模式

### 1. 默认模式：只用 OAK-D 点云

```bash
./scripts/with_venv.sh ros2 launch uav_bringup nav_stack.launch.py
```

局部地图和安全监控使用：

```text
/oakd/points_filtered
```

### 2. MID360 替代 OAK-D 点云做避障

推荐使用脚本：

```bash
./scripts/run_nav_stack.sh mid360
```

等价的底层 launch：

```bash
./scripts/with_venv.sh ros2 launch uav_bringup nav_stack.launch.py \
  enable_mid360:=true \
  obstacle_pointcloud_source:=mid360
```

此模式下：

```text
/livox/lidar -> /mid360/points -> local_map_builder / safety_monitor
```

VINS 定位仍使用 OAK-D。

### 3. MID360 补充 OAK-D 点云

推荐使用脚本：

```bash
./scripts/run_nav_stack.sh both
```

等价的底层 launch：

```bash
./scripts/with_venv.sh ros2 launch uav_bringup nav_stack.launch.py \
  enable_mid360:=true \
  obstacle_pointcloud_source:=both
```

此模式会启动点云合并节点：

```text
/oakd/points_filtered + /mid360/points -> /perception/obstacle_points
```

局部地图和安全监控统一订阅：

```text
/perception/obstacle_points
```

### 4. MID360 + FAST-LIO2 并列里程计

推荐使用脚本：

```bash
./scripts/run_nav_stack.sh mid360_lio
```

等价的底层 launch：

```bash
./scripts/with_venv.sh ros2 launch uav_bringup nav_stack.launch.py \
  enable_mid360:=true \
  enable_lio:=true \
  obstacle_pointcloud_source:=both
```

此模式额外启动 FAST-LIO2：

```text
/livox/lidar + /livox/imu -> fast_lio -> /lio/odometry
```

此模式下 VIO 与 LIO 不分主次，都是 EKF 的里程计输入：

```text
/vio/odometry
/lio/odometry
/px4/attitude
/px4/imu
```

当前 EKF 配置对 LIO 融合位置和速度，不融合 yaw，以降低 VIO/LIO 航向冲突风险。这是融合字段配置，不代表 LIO 是 VIO 的备用链路。

### 5. 纯 MID360/LIO 模式：关闭 OAK-D 和 VINS

如果当前任务不需要 OAK-D 图像、OAK-D 深度点云和 VINS，可显式关闭 OAK-D 相关节点：

推荐使用脚本：

```bash
./scripts/run_nav_stack.sh mid360_only
```

等价的底层 launch：

```bash
./scripts/with_venv.sh ros2 launch uav_bringup nav_stack.launch.py \
  enable_oakd_perception:=false \
  enable_imu_fusion:=false \
  enable_vins:=false \
  enable_mid360:=true \
  enable_lio:=true \
  obstacle_pointcloud_source:=mid360
```

此模式下：

```text
MID360 -> /livox/lidar -> /mid360/points -> local_map_builder / safety_monitor
MID360 -> /livox/lidar + /livox/imu -> FAST-LIO2 -> /lio/odometry -> EKF
```

注意：关闭 VINS 后，EKF 不再接收 `/vio/odometry`，定位由 `/lio/odometry` 以及可用的 PX4 姿态/IMU/GPS 输入承担。第一阶段建议先确认 `/lio/odometry` 稳定后再用于飞行。

## 关键 Launch 参数

```text
enable_oakd_perception:=false|true
enable_imu_fusion:=false|true
enable_vins:=false|true
enable_mid360:=false|true
enable_lio:=false|true
obstacle_pointcloud_source:=oakd|mid360|both

mid360_custom_topic:=/livox/lidar
mid360_pointcloud_topic:=/mid360/points
mid360_frame_id:=mid360_link

combined_pointcloud_topic:=/perception/obstacle_points
combined_pointcloud_frame:=base_link

lio_odom_topic:=/lio/odometry
lio_path_topic:=/lio/path
lio_config_file:=mid360.yaml

mid360_x:=0.0
mid360_y:=0.0
mid360_z:=0.0
mid360_yaw:=0.0
mid360_pitch:=0.0
mid360_roll:=0.0
```

## TF 和外参

`ekf_launch.py` 会在启用 MID360 或 LIO 时发布：

```text
base_link -> mid360_link
```

参数顺序：

```text
mid360_x mid360_y mid360_z mid360_yaw mid360_pitch mid360_roll
```

坐标约定：

```text
ROS ENU: X 前，Y 左，Z 上
```

示例：MID360 位于机体中心前方 8 cm、上方 5 cm：

```bash
mid360_x:=0.08 mid360_y:=0.0 mid360_z:=0.05
```

外参不准会导致：

- 合并点云错位。
- 局部地图障碍物偏移。
- LIO 和 VIO 进 EKF 后互相拉扯。

真实飞行前必须实测。

## 话题检查

MID360 驱动：

```bash
./scripts/with_venv.sh ros2 topic list | grep -E "/livox|/mid360"
./scripts/with_venv.sh ros2 topic hz /livox/lidar
./scripts/with_venv.sh ros2 topic hz /livox/imu
```

点云转换：

```bash
./scripts/with_venv.sh ros2 topic hz /mid360/points
./scripts/with_venv.sh ros2 topic info /mid360/points
```

FAST-LIO2：

```bash
./scripts/with_venv.sh ros2 topic hz /lio/odometry
./scripts/with_venv.sh ros2 topic echo /lio/odometry --once
```

局部地图：

```bash
./scripts/with_venv.sh ros2 topic hz /local_map/occupancy
```

TF：

```bash
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link mid360_link
```

## FAST-LIO2 配置

默认配置：

```text
src/FAST_LIO_ROS2/config/mid360.yaml
```

关键项：

```yaml
common:
  lid_topic: "/livox/lidar"
  imu_topic: "/livox/imu"

preprocess:
  lidar_type: 1
  scan_line: 4
  blind: 0.5
  scan_rate: 10

mapping:
  extrinsic_est_en: true
  extrinsic_T: [ -0.011, -0.02329, 0.04412 ]
  extrinsic_R: [ 1., 0., 0.,
                 0., 1., 0.,
                 0., 0., 1.]
```

第一阶段建议：

- 先保持 `extrinsic_est_en: true`，确认 LIO 能跑通。
- 跑稳后用实测或标定外参替换 `extrinsic_T/R`，再评估是否关掉在线估计。
- `blind` 不要太小，无人机桨叶/机体附近点云应过滤掉。

## 常见问题

### 找不到 `livox_lidar_sdk_shared`

现象：

```text
Could not find livox_lidar_sdk_shared
```

处理：

```bash
./scripts/build_livox_sdk2.sh
./scripts/with_venv.sh env | grep LIVOX_SDK2_ROOT
```

确认：

```text
.deps/livox_sdk2/lib/liblivox_lidar_sdk_shared.so
```

存在。

### 没有 `/livox/lidar`

检查：

- MID360 是否上电。
- 网线是否连接到正确网口。
- `MID360_config.json` 中 host IP 是否是机载电脑网口 IP。
- MID360 IP 是否正确。
- 防火墙是否阻挡 UDP 端口。

### 有 `/livox/lidar`，没有 `/mid360/points`

确认启动参数：

```bash
enable_mid360:=true obstacle_pointcloud_source:=mid360
```

或：

```bash
enable_mid360:=true obstacle_pointcloud_source:=both
```

转换节点只在 `obstacle_pointcloud_source` 为 `mid360` 或 `both` 时启动。

### 有 `/mid360/points`，局部地图为空

检查 TF：

```bash
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map mid360_link
```

如果 TF 不通，检查：

- EKF 是否在发布 `map/odom/base_link`。
- `base_link -> mid360_link` 是否发布。
- 点云 `frame_id` 是否是 `mid360_link`。

### FAST-LIO2 无 `/lio/odometry`

检查：

```bash
./scripts/with_venv.sh ros2 topic hz /livox/lidar
./scripts/with_venv.sh ros2 topic hz /livox/imu
```

FAST-LIO2 同时需要点云和 IMU。只有点云没有 IMU 时不会正常输出里程计。

### EKF 输出抖动

常见原因：

- VIO 和 LIO 坐标系不一致。
- MID360 外参不准。
- LIO 初始化方向和 VINS/EKF 初始方向不一致。
- 时间戳不同步。

第一阶段建议先单独观察 `/vio/odometry` 和 `/lio/odometry`，确认两者趋势一致后再启用 `enable_lio:=true`。

## 推荐落地顺序

1. 只启动 MID360 驱动，确认 `/livox/lidar` 和 `/livox/imu`。
2. 启动 `obstacle_pointcloud_source:=mid360`，确认 `/mid360/points` 和局部地图。
3. 启动 `obstacle_pointcloud_source:=both`，确认 `/perception/obstacle_points`。
4. 单独启用 FAST-LIO2，确认 `/lio/odometry` 稳定。
5. 最后启用 `enable_lio:=true`，让 EKF 同时融合 VIO 与 LIO 两路并列里程计输入。
