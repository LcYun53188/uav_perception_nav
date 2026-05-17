# VINS-Fusion ROS 2 配置代办

## 背景

本文件记录对 `src/VINS-Fusion-ros2` 的配置检查结论，以及后续需要修改或验证的事项。

OAK-D Pro W 的相机/IMU 标定、静止漂移排查和 EEPROM 参数导出流程见：

- `docs/OAKD_PRO_W_VINS_CALIBRATION.md`

当前检查范围：

- `src/VINS-Fusion-ros2/launch/vins_fusion_ros2.launch.py`
- `src/VINS-Fusion-ros2/launch/oakd_vins.launch.py`
- `src/VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml`
- `src/VINS-Fusion-ros2/config/oakd/left.yaml`
- `src/VINS-Fusion-ros2/config/oakd/right.yaml`
- `src/oakd_perception/oakd_perception/oakd_unified_node.py`

## 已确认状态

- `vins_fusion_ros2` 包已安装，`ros2 pkg` 可以发现 `vins_fusion_ros2_node`。
- `oakd_vins.launch.py` 会加载 OAK-D 配置文件 `config/oakd/oakd_stereo_imu_config.yaml`。
- OAK-D VINS 配置订阅的话题为：
  - `/oakd/imu/raw`
  - `/oakd/left/image_raw`
  - `/oakd/right/image_raw`
- `oakd_perception` 默认会发布上述图像和 IMU 话题，话题名称匹配。
- 使用 OAK-D 配置冷启动 VINS 节点时，节点可以读取配置并进入运行状态，日志中出现：
  - `USE_IMU: 1`
  - `STEREO: 1`
- `oakd_vins.launch.py` 已将 VINS 输出 frame 接入主 TF 语义：
  - `world_frame_id: odom`
  - `body_frame_id: oakd_imu_link`
  - `camera_frame_id: oakd_camera_optical_frame`
- VINS 自身 TF 仍 remap 到 `/vins/tf` 和 `/vins/tf_static`，主 `/tf` 由 `robot_localization` 与静态 TF 发布器负责。

## 当前 TF 配合方式

主 TF 树目标：

```text
map
└── odom
    └── base_link
        ├── oakd_imu_link
        │   └── oakd_camera_optical_frame
        └── gps_link
```

发布关系：

- `map -> odom`
  - 无 GPS：`uav_bringup/launch/ekf_launch.py` 发布静态恒等变换。
  - GPS：`ekf_filter_node_map` 发布动态变换。
- `odom -> base_link`
  - `ekf_filter_node_odom` 发布。
- `base_link -> oakd_imu_link`
  - `uav_bringup/launch/ekf_launch.py` 发布静态安装外参，目前仍是全零占位。
- `oakd_imu_link -> oakd_camera_optical_frame`
  - `oakd_perception/launch/oakd_unified.launch.py` 发布静态相机内部变换。
- `base_link -> gps_link`
  - `uav_bringup/launch/ekf_launch.py` 发布静态 GPS 安装外参，目前仍是全零占位。
- VINS-Fusion
  - `/vio/odometry` 使用 `header.frame_id=odom`、`child_frame_id=oakd_imu_link`。
  - VINS TF 被隔离到 `/vins/tf`，不进入主 TF 树，避免与 EKF 发布的 `odom -> base_link` 冲突。
- PX4 姿态
  - `px4_comm_bridge` 将 PX4 `VehicleAttitude` 转为 `/px4/attitude`。
  - `robot_localization` 从 `/px4/attitude` 融合 roll/pitch。
  - `/px4/imu` 只用于角速度与线加速度，不再作为 orientation 来源。

## 待修改项

### 1. 创建输出目录

当前 OAK-D VINS 配置中写死：

```yaml
output_path: "/home/nuc/output/"
pose_graph_save_path: "/home/nuc/output/pose_graph/"
```

但检查时 `/home/nuc/output` 不存在。需要创建目录：

```bash
mkdir -p /home/nuc/output/pose_graph
```

或将输出路径改到工作区内，例如：

```yaml
output_path: "/home/nuc/Program/uav_vision_ws/output/vins"
pose_graph_save_path: "/home/nuc/Program/uav_vision_ws/output/vins/pose_graph/"
```

### 2. 明确 OAK-D 启动入口

默认 `vins_fusion_ros2.launch.py` 使用 EuRoC mono+IMU 配置，并启用 `use_sim_time`。

实机 OAK-D 应使用：

```bash
ros2 launch vins_fusion_ros2 oakd_vins.launch.py
```

后续可以考虑：

- 将 README 中的运行命令改为 OAK-D 实机命令。
- 或新增更明确的脚本，例如 `scripts/run_vins_oakd.sh`。

### 3. 替换 OAK-D 相机内参

当前 `left.yaml` 和 `right.yaml` 使用简化内参：

```yaml
fx: 400.0
fy: 400.0
cx: 320.0
cy: 200.0
distortion: 0
```

这更像占位值，不应作为最终定位精度依据。

需要从 OAK-D 标定结果或实际标定流程中导出真实参数，并更新：

- `src/VINS-Fusion-ros2/config/oakd/left.yaml`
- `src/VINS-Fusion-ros2/config/oakd/right.yaml`

### 4. 验证并修正相机-IMU 外参

当前配置：

```yaml
estimate_extrinsic: 1
body_T_cam0: identity
body_T_cam1: x = 0.075
```

该配置可以作为初值，但不能证明外参正确。

需要确认：

- `body_T_cam0` 是否对应 VINS 代码期望的 body 到 camera 变换。
- OAK-D IMU 坐标系与 mono left/right 图像坐标系是否一致。
- baseline `0.075m` 是否匹配当前硬件型号。
- `base_link -> oakd_imu_link` 静态安装外参是否已实测并填入 `uav_bringup/launch/ekf_launch.py`。
- `base_link -> gps_link` 静态安装外参是否已实测并填入 `uav_bringup/launch/ekf_launch.py`。

### 5. 检查时间戳同步质量

VINS 配置启用了：

```yaml
estimate_td: 1
td: 0.00
```

需要手动验证左右图像与 IMU 时间戳是否稳定：

```bash
ros2 topic echo --once /oakd/left/image_raw/header
ros2 topic echo --once /oakd/right/image_raw/header
ros2 topic echo --once /oakd/imu/raw/header
ros2 topic hz /oakd/left/image_raw
ros2 topic hz /oakd/right/image_raw
ros2 topic hz /oakd/imu/raw
```

### 6. 验证 VINS 输出

启动 OAK-D：

```bash
ros2 launch oakd_perception oakd_unified.launch.py
```

启动 VINS：

```bash
ros2 launch vins_fusion_ros2 oakd_vins.launch.py
```

检查输出：

```bash
ros2 topic hz /image_track
ros2 topic hz /point_cloud
ros2 topic hz /imu_propagate
ros2 topic hz /vio/odometry
ros2 topic echo --once /vio/odometry
```

通过标准：

- `/image_track` 有跟踪图像输出。
- 移动相机后 `/vio/odometry` 开始发布。
- `/home/nuc/output/vio.csv` 或新的输出路径下生成结果文件。
- 轨迹方向、尺度、姿态变化符合实际运动。

## 当前未修改的内容

本次仅创建代办文件，未修改 VINS、OAK-D 或 launch 配置。
