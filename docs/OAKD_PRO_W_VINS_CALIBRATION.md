# OAK-D Pro W 与 VINS-Fusion 标定指南

本文记录 OAK-D Pro W 接入 `src/VINS-Fusion-ros2` 时必须确认的标定项，以及静止时 `/path` 或 `/vio/odometry` 剧烈漂移的排查顺序。

适用范围：

- OAK-D Pro W 发布 `/oakd/left/image_raw`、`/oakd/right/image_raw`、`/oakd/imu/raw`
- VINS-Fusion 使用 `src/VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml`
- OAK-D 感知节点使用 `src/oakd_perception/oakd_perception/oakd_unified_node.py`

## 1. 为什么不能忽略标定

VINS-Fusion 同时使用视觉重投影约束和 IMU 预积分约束。静止时如果配置正确，视觉约束会抑制 IMU bias 带来的积分漂移；如果相机内参、畸变、左右目外参、相机-IMU 外参或时间戳错误，系统会把模型误差解释成真实运动。

常见表现：

- OAK-D 静止不动，`/path` 持续快速偏移
- `/vio/odometry.pose.pose.position` 在数秒内达到数米、数十米甚至更大
- `/vio/odometry.twist.twist.linear` 静止时仍有明显速度
- `/image_track` 有特征，但轨迹方向和尺度不可信

需要区分两类误差：

- 小误差：几毫米平移误差、轻微内参误差，通常表现为慢漂或尺度不准。
- 致命误差：IMU 到相机旋转错误、宽视场原始图像却按零畸变 pinhole 使用、左右目 baseline 方向错误、时间戳抖动，通常表现为静止快速发散。

## 2. 当前涉及的配置文件

VINS 配置：

- `src/VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml`
- `src/VINS-Fusion-ros2/config/oakd/left.yaml`
- `src/VINS-Fusion-ros2/config/oakd/right.yaml`

OAK-D 发布端：

- `src/oakd_perception/oakd_perception/oakd_unified_node.py`
- `src/oakd_perception/launch/oakd_unified.launch.py`
- `src/oakd_perception/config/outdoor_low_power.yaml`

TF 文档：

- `docs/TF_FRAMES.md`

## 3. 必须标定或确认的参数

### 3.1 左右目内参

写入：

- `left.yaml`
- `right.yaml`

字段：

```yaml
model_type: PINHOLE
image_width: 640
image_height: 400
distortion_parameters:
  k1: ...
  k2: ...
  p1: ...
  p2: ...
projection_parameters:
  fx: ...
  fy: ...
  cx: ...
  cy: ...
```

注意：

- OAK-D Pro W 是宽视场 stereo，相机原始图不能长期按 `distortion=0` 的 pinhole 占位值使用。
- 如果发布的是 DepthAI rectified left/right，可临时使用零畸变 pinhole 近似，但仍建议从 EEPROM 或离线标定导出 rectified 后的有效内参。

### 3.2 左右目外参与 baseline

写入：

- `oakd_stereo_imu_config.yaml` 的 `body_T_cam0`
- `oakd_stereo_imu_config.yaml` 的 `body_T_cam1`

OAK-D Pro W 标称 stereo baseline 为约 `0.075 m`。baseline 方向必须和 VINS 使用的相机坐标系、body 坐标系一致。方向错会导致尺度和运动方向错误。

### 3.3 相机-IMU 外参

写入：

- `oakd_stereo_imu_config.yaml` 的 `body_T_cam0`
- `oakd_stereo_imu_config.yaml` 的 `body_T_cam1`
- `oakd_unified.launch.py` 中 `oakd_imu_link -> oakd_camera_optical_frame` 静态 TF

要求：

- VINS 内部 `body_T_cam*` 和 ROS TF 语义必须一致。
- `oakd_imu_link -> oakd_camera_optical_frame` 不应与 `body_T_cam0` 表示相反或不同的旋转。
- 在未完成真实标定前，建议 `estimate_extrinsic: 0`，避免静止初始化时在线估计发散。

### 3.4 IMU bias 与噪声

写入：

- `oakd_stereo_imu_config.yaml` 中 `acc_n`、`gyr_n`、`acc_w`、`gyr_w`

静止 IMU 一定有 bias。IMU 漂移会影响 VINS，但正常情况下视觉约束会限制漂移。如果视觉标定错误，IMU bias 会被放大为快速位姿发散。

检查：

```bash
scripts/with_venv.sh ros2 topic echo /oakd/imu/raw --field linear_acceleration
scripts/with_venv.sh ros2 topic echo /oakd/imu/raw --field angular_velocity
scripts/with_venv.sh ros2 topic hz /oakd/imu/raw
```

静止时：

- 加速度模长应接近 `9.8 m/s^2`
- 角速度应接近 0，但会有小 bias
- 发布频率应稳定，当前 OAK-D 实测常见约 `250 Hz`

### 3.5 时间戳同步

VINS 对时间戳非常敏感。不要用 USB 接收时刻代替采集时刻。

OAK-D 发布端应优先使用 DepthAI packet/frame 的 device timestamp，并把左右图用同一个采集时间戳发布。

建议在标定完成前保持：

```yaml
estimate_td: 0
td: 0.00
```

等图像和 IMU 时间戳稳定后，再评估是否开启 `estimate_td`。

## 4. 从 OAK-D EEPROM 读取标定

先停止占用 OAK-D 的节点：

```bash
pkill -f oakd_unified_node
pkill -f vins_fusion_ros2_node
pkill -f rviz2
```

读取设备标定：

```bash
cd /home/nuc/Program/uav_vision_ws
scripts/with_venv.sh python3 - <<'PY'
import depthai as dai

device = dai.Device()
calib = device.readCalibration()

print("device:", device.getDeviceName())
print("LEFT K 640x400:")
print(calib.getCameraIntrinsics(dai.CameraBoardSocket.LEFT, 640, 400))
print("RIGHT K 640x400:")
print(calib.getCameraIntrinsics(dai.CameraBoardSocket.RIGHT, 640, 400))
print("LEFT -> RIGHT extrinsics:")
print(calib.getCameraExtrinsics(dai.CameraBoardSocket.LEFT, dai.CameraBoardSocket.RIGHT))

for socket in (dai.CameraBoardSocket.LEFT, dai.CameraBoardSocket.RIGHT):
    try:
        print(f"IMU -> {socket.name} extrinsics:")
        print(calib.getImuToCameraExtrinsics(socket))
    except Exception as exc:
        print(f"IMU -> {socket.name} extrinsics unavailable: {exc}")
PY
```

如果该命令因权限失败，需要在本机 shell 中直接执行，或允许 Codex 在沙箱外访问设备。

## 5. 写入 VINS 配置

### 5.1 内参

将 EEPROM 输出的 `K` 写入：

- `left.yaml`
- `right.yaml`

映射关系：

```text
fx = K[0][0]
fy = K[1][1]
cx = K[0][2]
cy = K[1][2]
```

如果使用 rectified 图像：

- 畸变参数通常可先设为 0
- 但应确认 EEPROM 读取的内参对应当前输出分辨率和 rectification 后图像

### 5.2 body_T_cam

`body_T_cam0/body_T_cam1` 必须表示 VINS body 坐标系到相机坐标系的刚体变换。当前工程中 body 语义为 `oakd_imu_link`。

外参修改位置要区分清楚：

| 内容 | 修改位置 | 含义 |
|------|----------|------|
| `base_link -> oakd_imu_link` | `src/uav_bringup/launch/ekf_launch.py` | 整台 OAK-D 相对无人机机体的安装位置和姿态 |
| `oakd_imu_link -> oakd_camera_optical_frame` | `src/oakd_perception/launch/oakd_unified.launch.py` | OAK-D 内部 IMU/机身坐标系到相机光学坐标系 |
| `body_T_cam0/body_T_cam1` | `src/VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml` | VINS 内部使用的 IMU 到左右相机外参 |

如果只是移动 OAK-D 在飞机上的安装位置，只修改 `base_link -> oakd_imu_link`；不要修改 `body_T_cam0/body_T_cam1`。只有当 OAK-D 内部 IMU-相机标定更新，或确认当前光学帧方向/左右目 baseline 错误时，才修改本节矩阵。

写入前必须确认 EEPROM 的 `getImuToCameraExtrinsics()` 返回方向。如果返回的是 `IMU -> Camera`，通常可直接作为 `body_T_cam` 初值；如果返回的是 `Camera -> IMU`，需要取逆。

矩阵格式：

```yaml
body_T_cam0: !!opencv-matrix
   rows: 4
   cols: 4
   dt: d
   data: [ r00, r01, r02, tx,
           r10, r11, r12, ty,
           r20, r21, r22, tz,
           0.,  0.,  0.,  1. ]
```

配置原则：

- `body_T_cam0`：IMU/body 到左目相机
- `body_T_cam1`：IMU/body 到右目相机
- `body_T_cam1` 和 `body_T_cam0` 的相对平移应体现约 `0.075 m` baseline
- `oakd_unified.launch.py` 的静态 TF 应与 `body_T_cam0` 的旋转一致

## 6. 推荐验证流程

### 6.1 只启动 OAK-D

```bash
src/oakd_perception/scripts/run_oakd_outdoor.sh
```

检查：

```bash
scripts/with_venv.sh ros2 topic hz /oakd/left/image_raw
scripts/with_venv.sh ros2 topic hz /oakd/right/image_raw
scripts/with_venv.sh ros2 topic hz /oakd/imu/raw
scripts/with_venv.sh ros2 topic echo --once /oakd/left/image_raw/header
scripts/with_venv.sh ros2 topic echo --once /oakd/right/image_raw/header
scripts/with_venv.sh ros2 topic echo --once /oakd/imu/raw/header
```

通过标准：

- 左右图频率接近，时间戳同步
- IMU 持续发布
- `frame_id` 分别为 `oakd_camera_optical_frame` 和 `oakd_imu_link`

### 6.2 清理重复 VINS 节点

启动 VINS 前确认没有残留同名节点：

```bash
scripts/with_venv.sh ros2 node list
```

如果出现多个：

```bash
pkill -f vins_fusion_ros2_node
pkill -f rviz2
```

重复 VINS 节点会导致 `/vio/odometry` 上多个 publisher 同时发布，表现为 odometry 在正常小值和巨大异常值之间交替。

### 6.3 启动 VINS

```bash
scripts/with_venv.sh ros2 launch vins_fusion_ros2 oakd_vins.launch.py
```

检查：

```bash
scripts/with_venv.sh ros2 topic hz /image_track
scripts/with_venv.sh ros2 topic hz /vio/odometry
scripts/with_venv.sh ros2 topic echo /vio/odometry --field pose.pose.position
scripts/with_venv.sh ros2 topic echo /vio/odometry --field twist.twist.linear
```

静止通过标准：

- `/image_track` 有稳定跟踪图像
- `/vio/odometry` 不应在数秒内达到数米以上
- `twist.twist.linear` 不应长期维持米/秒级速度
- `/path` 不应快速向单方向漂移

## 7. 当前工程状态记录

截至 2026-05-17，本工程已做过以下临时缓解：

- VINS 的 `world_frame_id` 使用 `odom`
- RViz Fixed Frame 改为 `odom`
- OAK-D 发布端优先使用 DepthAI device timestamp
- 左右图像改为发布 `StereoDepth` rectified left/right
- `estimate_extrinsic` 暂设为 0
- `estimate_td` 暂设为 0
- OAK-D Pro W 的 `left.yaml/right.yaml` 使用按标称 FOV 估算的临时内参

仍未完成：

- 未读取并写入 OAK-D EEPROM 真实内参
- 未写入真实 `IMU -> left/right camera` 外参
- 未做 Kalibr 等离线相机-IMU 联合标定
- 未实测 `base_link -> oakd_imu_link` 安装外参

因此，当前 `/vio/odometry` 只能用于链路调试，不能作为飞控闭环定位源。
