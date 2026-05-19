# OAK-D / MID360 独立调试指南

本文档用于单独调试 OAK-D 相机和 Livox MID360。系统级启动、导航栈模式和项目总览见根目录 `README.md`。

## 通用准备

在工作区根目录执行：

```bash
cd /home/nuc/Program/uav_vision_ws
source .venv/bin/activate
source install/setup.bash
```

推荐所有 ROS / Python 命令都通过：

```bash
./scripts/with_venv.sh <command>
```

## OAK-D 独立调试

### 场景预设脚本

项目提供四个 OAK-D 场景预设脚本：

| 脚本 | 被动立体 | 主动立体 | 场景 |
|------|---------|---------|------|
| `run_oakd_outdoor.sh` | yes | no | 户外强光、低功耗 |
| `run_oakd_indoor.sh` | yes | yes | 室内弱光、高精度 |
| `run_oakd_balance.sh` | yes | yes | 平衡模式 |
| `run_oakd_active_max.sh` | no | yes | 黑暗环境、最高密度 |

常用入口：

```bash
./scripts/run_oakd_unified.sh
```

或直接运行某个预设：

```bash
./scripts/run_oakd_balance.sh
./scripts/run_oakd_outdoor.sh
./scripts/run_oakd_indoor.sh
./scripts/run_oakd_active_max.sh
```

### 手动传参

```bash
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node --ros-args \
  -p enable_passive_stereo:=true \
  -p enable_active_stereo:=true \
  -p ir_intensity:=800 \
  -p sampling_step:=2 \
  -p min_depth:=200 \
  -p max_depth:=5000
```

也可以直接使用统一节点 launch：

```bash
./scripts/with_venv.sh ros2 launch oakd_perception oakd_unified.launch.py \
  enable_passive_stereo:=true \
  enable_active_stereo:=true \
  ir_intensity:=1000 \
  pointcloud_frequency:=30
```

### 预期话题

```text
/oakd/imu/raw
/oakd/left/image_raw
/oakd/right/image_raw
/oakd/points
/oakd/points_filtered
```

检查：

```bash
./scripts/with_venv.sh ros2 topic list | grep -E "/oakd/points|/oakd/imu|/oakd/.*/image_raw"
./scripts/with_venv.sh ros2 topic hz /oakd/points
./scripts/with_venv.sh ros2 topic hz /oakd/imu/raw
```

### IMU 预融合调试

OAK-D 自身 IMU 链路：

```text
/oakd/imu/raw -> imu_fusion -> /oakd/imu/fused
```

启动：

```bash
./scripts/run_oakd_unified.sh
./scripts/run_imu_fusion_tf.sh
```

注意：不要让旧的 `imu_tf_broadcaster` 向主 `/tf` 发布 `map -> oakd_imu_link`，否则 `oakd_imu_link` 会同时拥有 EKF 静态链路和 IMU 动态链路两个父帧。

### OAK-D RViz

```bash
./scripts/with_venv.sh rviz2
```

建议：

- 仅调试 OAK-D 点云时，`Fixed Frame` 可设为 `oakd_camera_optical_frame`。
- 完整导航链路中，`Fixed Frame` 设为 `map`。
- 添加 `PointCloud2`，选择 `/oakd/points_filtered` 或 `/oakd/points`。

### OAK-D 常见问题

- `ModuleNotFoundError: depthai`：确认 `.venv` 中已安装 `depthai`。
- `X_LINK_DEVICE_ALREADY_IN_USE`：使用 `oakd_unified_node`，或确保只有一个进程访问 OAK-D。
- 没有点云：检查 USB 连接、DepthAI 权限、`/oakd/left/image_raw` 和 `/oakd/right/image_raw` 是否存在。
- RViz 不显示点云：检查话题、`Fixed Frame` 和 TF 链路。

## MID360 独立调试

### 构建前置

MID360 相关第三方源码通过 submodule + patch 管理：

```bash
git submodule update --init --recursive
./scripts/apply_vendor_patches.sh
./scripts/build_livox_sdk2.sh
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh colcon build \
  --packages-select livox_ros_driver2 fast_lio nav_mapping uav_bringup \
  --symlink-install
source install/setup.bash
```

### 网络配置

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

- `host_net_info.*_ip`：机载电脑有线网口 IP。
- `lidar_configs[0].ip`：MID360 设备 IP。

连通性检查：

```bash
ping 192.168.1.12
```

### 启动 MID360 点云链路

推荐使用导航栈脚本：

```bash
./scripts/run_nav_stack.sh mid360
```

只看 MID360 相关话题：

```bash
./scripts/with_venv.sh ros2 topic list | grep -E "/livox|/mid360"
./scripts/with_venv.sh ros2 topic hz /livox/lidar
./scripts/with_venv.sh ros2 topic hz /livox/imu
./scripts/with_venv.sh ros2 topic hz /mid360/points
```

链路：

```text
/livox/lidar -> livox_custom_to_pointcloud2 -> /mid360/points
```

### 启动 MID360 + FAST-LIO2

OAK-D + MID360 + LIO：

```bash
./scripts/run_nav_stack.sh mid360_lio
```

纯 MID360/LIO 模式：

```bash
./scripts/run_nav_stack.sh mid360_only
```

检查：

```bash
./scripts/with_venv.sh ros2 topic hz /lio/odometry
./scripts/with_venv.sh ros2 topic echo /lio/odometry --once
```

### MID360 TF 与外参

默认发布：

```text
base_link -> mid360_link
```

外参参数：

```text
mid360_x mid360_y mid360_z mid360_yaw mid360_pitch mid360_roll
```

示例：

```bash
./scripts/run_nav_stack.sh mid360 mid360_x:=0.08 mid360_y:=0.0 mid360_z:=0.05
```

检查 TF：

```bash
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link mid360_link
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map mid360_link
```

### MID360 RViz

```bash
./scripts/with_venv.sh rviz2
```

建议：

- `Fixed Frame`：完整导航链路使用 `map`，单独观察可用 `mid360_link`。
- 添加 `PointCloud2`，选择 `/mid360/points`。
- `both` 模式下添加 `/perception/obstacle_points`。

### MID360 常见问题

- 没有 `/livox/lidar`：检查 MID360 上电、网口 IP、`MID360_config.json` 中 host IP 和设备 IP。
- 有 `/livox/lidar` 但没有 `/mid360/points`：确认 `enable_mid360:=true` 且 `obstacle_pointcloud_source:=mid360` 或 `both`。
- 有 `/mid360/points` 但局部地图为空：检查 `base_link -> mid360_link` TF、点云 `frame_id` 和 `local_map_builder` 的输入话题。
- FAST-LIO2 无 `/lio/odometry`：确认 `/livox/lidar` 和 `/livox/imu` 同时存在，且 `enable_lio:=true`。
- LIO 与 VIO/EKF 差异大：先单独观察 `/vio/odometry` 和 `/lio/odometry`，确认外参、时间同步和初始化方向。

## 录制与回放

OAK-D：

```bash
./scripts/with_venv.sh ros2 bag record -o oakd_debug \
  /oakd/points_filtered /oakd/imu/raw /vio/odometry /odometry/local /tf /tf_static
```

MID360：

```bash
./scripts/with_venv.sh ros2 bag record -o mid360_debug \
  /livox/lidar /livox/imu /mid360/points /lio/odometry /odometry/local /tf /tf_static
```

回放：

```bash
./scripts/with_venv.sh ros2 bag play <bag_dir>
```
