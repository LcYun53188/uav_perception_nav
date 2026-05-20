# TF 坐标变换系统说明

本文档描述无人机视觉导航系统的 TF（坐标变换）树设计、帧定义、发布关系与配置方法。

---

## 1. TF 基本概念

TF 是 ROS 2 中管理多个坐标系（Frame）之间空间关系的核心库。每个传感器、机体部件、地图参考点都有自己的坐标系。TF 以**树状结构**维护它们之间的平移和旋转关系，使得系统中任意两个坐标系之间的变换都可以自动计算。

**关键约束**：
- 每个坐标系有且仅有一个父节点（Parent Frame）
- 不允许环路
- 违反以上规则会导致 TF 树解算失败

---

## 2. 坐标系定义

本系统使用以下坐标系，全部遵循 **ROS ENU 约定**（X-前, Y-左, Z-上）：

| 坐标系 | 含义 | 物理位置 |
|--------|------|----------|
| `map` | 全局固定参考系 | 世界坐标系原点（ENU 东北天） |
| `odom` | 里程计累计参考系 | 系统启动时与 map 重合，随漂移偏移 |
| `base_link` | 无人机机身中心 | 飞控 FCU 质心 |
| `oakd_imu_link` | OAK-D 相机 IMU 中心 | 相机物理安装位置 |
| `oakd_camera_optical_frame` | OAK-D 镜头光学中心 | 相机光学轴原点（点云参考系） |
| `gps_link` | GPS 天线 | GPS 天线物理位置 |

地面全向轮平台同样使用 `base_link` 作为车体坐标系：

```text
base_link.x：车体前方
base_link.y：车体左方
base_link.z：车体上方
yaw / angular.z：从上往下看逆时针为正
```

下位机如果接收车体系速度，也应按同一约定解释：

```text
vx > 0：前进
vy > 0：左移
wz > 0：逆时针旋转
```

---

## 3. TF 树拓扑

### 3.1 无 GPS 模式（默认）

```
map ──(静态恒等变换)──> odom ──(EKF_odom 动态)──> base_link ──(静态外参)──> oakd_imu_link ──(静态外参)──> oakd_camera_optical_frame
                                                      │
                                                      └──(静态外参)──> gps_link
```

### 3.2 GPS 模式

```
map ──(EKF_map 动态)──> odom ──(EKF_odom 动态)──> base_link ──(静态外参)──> oakd_imu_link ──(静态外参)──> oakd_camera_optical_frame
                                                      │
                                                      └──(静态外参)──> gps_link
```

### 3.3 变换详情

| 父帧 → 子帧 | 类型 | 发布者 | 说明 |
|-------------|------|--------|------|
| `map` → `odom` | 动态/静态 | GPS 模式: `ekf_filter_node_map`<br>无 GPS: `static_transform_publisher` | GPS 校正全局漂移；无 GPS 时为恒等变换 |
| `odom` → `base_link` | 动态 | `ekf_filter_node_odom` | 融合 VIO + IMU 的实时位姿 |
| `base_link` → `oakd_imu_link` | 静态 | `static_transform_publisher` | 相机安装外参（物理偏移量） |
| `oakd_imu_link` → `oakd_camera_optical_frame` | 静态 | `static_transform_publisher` | 相机内部 IMU 到镜头的标定 |
| `base_link` → `gps_link` | 静态 | `static_transform_publisher` | GPS 天线偏移 |
| `base_link` → `mid360_link` | 静态 | `static_transform_publisher` | MID360 安装外参（启用 MID360 或 LIO 时发布） |

### 3.4 地面全向轮与下位机坐标系

全向轮平台的推荐边界是：

```text
上位机：维护 map / odom / base_link，并完成导航、目标追踪、yaw 闭环
下位机：执行 vx / vy / wz，处理电机闭环、使能、急停和故障上报
```

默认不启用下位机世界坐标系，串口桥接节点把 `/nav/cmd_vel` 转成 `base_link` 后下发：

```yaml
mcu_velocity_frame: base_link
```

此模式要求下位机按 `base_link` 车体系解释速度，是最推荐的工程接口。

如果下位机无法改成车体系速度接口，必须继续按自己的漂移世界坐标系执行速度，可显式启用下位机坐标系补偿：

```yaml
mcu_velocity_frame: mcu_world
mcu_yaw_compensation_mode: yaw_error
mcu_yaw_reference_frame: odom   # 或 map，取决于上位机主定位参考系
require_feedback: true
require_mcu_yaw_for_mcu_world: true
```

启用后，`ground_serial_bridge` 使用：

```text
yaw_base  = 上位机 TF 中 base_link 在 odom/map 下的 yaw
yaw_mcu   = 下位机状态帧回传的 yaw
yaw_error = yaw_mcu - yaw_base
```

并把上位机参考系速度旋转到下位机 `mcu_world` 后发送。这样真实车体旋转不会被误当成漂移；只有 `yaw_mcu` 与 `yaw_base` 的差值参与补偿。

下位机状态帧需包含 `yaw_mrad`。如果下位机 yaw 符号与 ROS 相反，设置：

```yaml
mcu_yaw_sign: -1.0
```

注意：`mcu_world` 是兼容方案，不应反向发布进 ROS 主 TF 树。上位机坐标仍以 LIO/EKF 发布的 `map/odom -> base_link` 为准。

---

## 4. 数据流与 TF 关系

```
                 ┌─────────────────┐
                 │  VINS-Fusion    │
                 │  (VIO 里程计)    │
                 │                 │
                 │  发布: /vio/odometry (nav_msgs/Odometry)
                 │  TF: 隔离到 /vins/tf（不影响主 TF 树）
                 └────────┬────────┘
                          │
                          ▼
┌──────────┐    ┌─────────────────────┐    ┌──────────────────┐
│ PX4 IMU  │───>│  EKF_odom           │    │  EKF_map         │
│ /px4/imu │    │  (robot_localization)│    │  (robot_localization)
│ frame:   │    │                     │    │                  │
│ base_link│    │  融合: VIO + IMU    │    │  融合: VIO+IMU+GPS│
└──────────┘    │  发布 TF:           │    │  发布 TF:        │
                │  odom → base_link   │    │  map → odom      │
                │  话题: /odometry/   │    │  话题: /odometry/ │
                │        local        │    │        global     │
                └─────────────────────┘    └──────────────────┘
                                                    ▲
                                                    │
                                           ┌────────┴────────┐
                                           │ navsat_transform │
                                           │ GPS WGS84→ENU   │
                                           │ /gps/fix →       │
                                           │ /odometry/gps   │
                                           └─────────────────┘
```

---

## 5. 配置与启动

### 5.1 启动方式

```bash
# 无 GPS 模式（默认）— 适用于室内/GPS 拒止环境
ros2 launch uav_bringup nav_stack.launch.py

# 等价于
ros2 launch uav_bringup nav_stack.launch.py enable_gps:=false

# GPS 模式 — 适用于室外有 GPS 信号环境
ros2 launch uav_bringup nav_stack.launch.py enable_gps:=true

# 单独启动 EKF（不启动导航栈）
ros2 launch uav_bringup ekf_launch.py enable_gps:=false
```

### 5.2 配置文件

| 文件 | 说明 |
|------|------|
| `uav_bringup/config/dual_ekf.yaml` | EKF_odom + EKF_map + NavSat 参数 |
| `uav_bringup/launch/ekf_launch.py` | EKF 节点 + 静态变换 launch 文件 |
| `uav_bringup/launch/nav_stack.launch.py` | 完整导航栈入口，包含 MID360 安装外参 launch 参数默认值 |
| `oakd_perception/launch/oakd_unified.launch.py` | OAK-D 统一节点 + `oakd_imu_link -> oakd_camera_optical_frame` 静态 TF |
| `VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml` | VINS 使用的 OAK-D IMU 到左右相机外参 |
| `FAST_LIO_ROS2/config/mid360.yaml` | FAST-LIO 使用的 MID360 LiDAR 到 IMU 外参 |

### 5.3 静态外参配置

本项目把“传感器装在飞机上的位置”和“传感器内部标定”分开配置。修改前先确认你要改的是哪一类：

| 目标 | TF / 参数 | 修改位置 |
|------|-----------|----------|
| 整台 OAK-D 相对机体的位置姿态 | `base_link -> oakd_imu_link` | `src/uav_bringup/launch/ekf_launch.py` |
| OAK-D 内部 IMU/机身帧到光学帧 | `oakd_imu_link -> oakd_camera_optical_frame` | `src/oakd_perception/launch/oakd_unified.launch.py` |
| VINS 内部 OAK-D IMU 到左右相机 | `body_T_cam0/body_T_cam1` | `src/VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml` |
| 整台 MID360 相对机体的位置姿态 | `base_link -> mid360_link` | `src/uav_bringup/launch/nav_stack.launch.py` 或启动参数 |
| FAST-LIO 内部 LiDAR 到 IMU | `extrinsic_T/extrinsic_R` | `src/FAST_LIO_ROS2/config/mid360.yaml` |

#### 5.3.1 OAK-D 机体安装外参

**OAK-D 安装外参**（`base_link → oakd_imu_link`）：

在 `ekf_launch.py` 中修改以下参数，单位为米和弧度：
```python
# arguments: [x, y, z, yaw, pitch, roll, parent_frame, child_frame]
# 坐标约定: ROS ENU (X-前, Y-左, Z-上)
arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'oakd_imu_link'],
```

这 6 个值表示 OAK-D 内置 IMU 原点相对 `base_link` 的安装位置和姿态：

- `x/y/z`：单位为米；`+X` 向前、`+Y` 向左、`+Z` 向上。
- `yaw/pitch/roll`：单位为弧度；顺序必须保持 `yaw pitch roll`。
- 当前全 0 表示 OAK-D 与 `base_link` 重合且姿态一致。

示例：OAK-D 在机体中心前方 10 cm、右侧 4 cm、上方 6 cm：

```python
arguments=['0.10', '-0.04', '0.06', '0', '0', '0', 'base_link', 'oakd_imu_link'],
```

> **重要**：同时需要在 PX4 QGC 参数中设置对应的 Lever Arm 补偿（NED 坐标系）：
> - `EKF2_EV_POS_X` = dx（与 ROS X 相同）
> - `EKF2_EV_POS_Y` = −dy（ROS Y 取反）
> - `EKF2_EV_POS_Z` = −dz（ROS Z 取反）

#### 5.3.2 OAK-D 内部 IMU 到光学帧

`oakd_perception/launch/oakd_unified.launch.py` 发布：

```text
oakd_imu_link -> oakd_camera_optical_frame
```

这不是整台 OAK-D 在机体上的安装位置，而是 OAK-D 内部 IMU/机身坐标系到相机光学坐标系的固定变换。当前参数：

```python
arguments=[
    '0', '0', '0',
    '1.57', '0', '3.14',
    'oakd_imu_link',
    'oakd_camera_optical_frame',
]
```

只有在更新 OAK-D 内部 IMU 到相机光学帧标定、或发现点云坐标轴翻转/方向错误时才修改这里。如果只是移动 OAK-D 的安装位置，应修改 `base_link -> oakd_imu_link`。

#### 5.3.3 VINS 的 OAK-D IMU 到相机外参

`VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml` 中：

```yaml
estimate_extrinsic: 0
body_T_cam0: ...
body_T_cam1: ...
```

这里的 `body_T_cam0/body_T_cam1` 是 VINS 内部使用的 `oakd_imu_link` 到左/右相机的刚体变换，不是 OAK-D 相对无人机机体的安装外参。它应与 `oakd_imu_link -> oakd_camera_optical_frame` 的方向语义保持一致。

#### 5.3.4 MID360 机体安装外参

`nav_stack.launch.py` 提供 MID360 安装参数：

```text
mid360_x mid360_y mid360_z mid360_yaw mid360_pitch mid360_roll
```

这组参数发布：

```text
base_link -> mid360_link
```

示例：MID360 位于机体中心前方 8 cm、上方 5 cm：

```bash
./scripts/run_nav_stack.sh --odom-source vio --pointcloud-source mid360 mid360_x:=0.08 mid360_y:=0.0 mid360_z:=0.05
```

如果要把默认值固化到工程入口，修改 `src/uav_bringup/launch/nav_stack.launch.py` 的 `LAUNCH_DEFAULTS`。如果只针对一次实验，优先在启动命令里传参。

#### 5.3.5 FAST-LIO 的 MID360 LiDAR-IMU 外参

`FAST_LIO_ROS2/config/mid360.yaml` 中：

```yaml
mapping:
  extrinsic_est_en: true
  extrinsic_T: [ -0.011, -0.02329, 0.04412 ]
  extrinsic_R: [ 1., 0., 0.,
                 0., 1., 0.,
                 0., 0., 1.]
```

这是 FAST-LIO 内部的 LiDAR 到 IMU 外参，不是 `base_link -> mid360_link`。调试新设备时可以先保持 `extrinsic_est_en: true`，待 LIO 稳定后再用实测或标定结果固定 `extrinsic_T/R`。

---

## 6. 调试与验收流程

外参验收按层级推进：先确认传感器单独有数据，再确认静态 TF 数值，再把点云放到 `base_link` 或 `map` 下看物理方向是否正确，最后才接入 VIO/LIO、局部地图和规划器。不要在点云方向还没确认时直接调 EKF 或规划参数。

建议每次只改一组外参：

| 调试目标 | 启动范围 | 主要观察 |
|----------|----------|----------|
| OAK-D 点云轴向 | OAK-D 统一节点 | `/oakd/points_filtered` 在 `oakd_camera_optical_frame` 下方向是否正确 |
| OAK-D 机体安装外参 | OAK-D + EKF 静态 TF | `/oakd/points_filtered` 转到 `base_link` 后位置是否符合实物 |
| VINS 内部外参 | OAK-D + VINS | `/vio/odometry` 初始化、漂移、运动方向是否正常 |
| MID360 点云轴向 | MID360 驱动 + 转换节点 | `/mid360/points` 在 `mid360_link` 下方向是否正确 |
| MID360 机体安装外参 | MID360 + EKF 静态 TF | `/mid360/points` 转到 `base_link` 后位置是否符合实物 |
| FAST-LIO 内部外参 | MID360 + FAST-LIO2 | `/lio/odometry` 初始化、姿态、移动方向是否正常 |
| 全向轮下位机坐标 | `omni_bringup` + `ground_serial_bridge` | `/nav/cmd_vel` 下发后，vx/vy/wz 方向、yaw_error 与安全停车是否符合预期 |

### 6.1 全向轮下位机坐标调试流程

调试顺序必须先轴向、再 yaw、再目标追踪：

1. 使用默认车体系模式：

   ```yaml
   mcu_velocity_frame: base_link
   ```

2. 手动发布 `base_link` 速度，确认轴向：

   ```text
   vx > 0：前进
   vy > 0：左移
   wz > 0：逆时针旋转
   ```

3. 检查上位机 TF：

   ```bash
   ./scripts/with_venv.sh ros2 run tf2_ros tf2_echo odom base_link
   ```

   若使用 `map` 作为主参考，则检查：

   ```bash
   ./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map base_link
   ```

4. 若必须启用下位机世界系：

   ```yaml
   mcu_velocity_frame: mcu_world
   mcu_yaw_compensation_mode: yaw_error
   require_feedback: true
   ```

   同时确认下位机状态帧持续回传 `yaw_mrad`。

5. 原地逆时针旋转，观察：

   ```text
   yaw_base 应增加
   yaw_mcu  应按同符号增加
   yaw_error 不应持续发散
   ```

   如果 `yaw_mcu` 符号相反，设置 `mcu_yaw_sign: -1.0`。

6. 边平移边旋转，观察 `/base/status` 中的 `vx_mps`、`vy_mps`、`wz_radps` 是否平滑，无突跳。

### 6.2 全向轮下位机坐标验收标准

验收通过条件：

- `base_link` 轴向符合实物：`x` 前、`y` 左、`z` 上。
- `vx > 0` 前进、`vy > 0` 左移、`wz > 0` 逆时针旋转。
- `mcu_velocity_frame: base_link` 模式下，不依赖下位机世界坐标即可稳定执行速度。
- 若启用 `mcu_world`，`yaw_mcu` 与 `yaw_base` 同方向变化，`yaw_error` 只反映下位机漂移，不反映真实车体旋转。
- `require_feedback: true` 时，底盘状态回传低于阈值或超时后进入停车/故障状态。
- TF 不可用时，`ground_serial_bridge` 不继续发送旧方向速度，应下发 0 速度。
- 下位机 `world_x/world_y/world_yaw` 不发布为 ROS 主 TF，不参与 `map/odom -> base_link` 权威定位。

### 6.3 通用 TF 检查命令

所有命令建议在工作区根目录执行：

```bash
cd /home/nuc/Program/uav_vision_ws
source install/setup.bash
```

查看 TF 树：

```bash
# 生成 TF 树 PDF（最常用）
./scripts/with_venv.sh ros2 run tf2_tools view_frames

# 实时查看关键变换
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map base_link
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link oakd_imu_link
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link mid360_link

# 查看所有 TF 广播
./scripts/with_venv.sh ros2 topic echo /tf
./scripts/with_venv.sh ros2 topic echo /tf_static
```

通过标准：

- `view_frames` 中每个 frame 只有一个父节点。
- 无 GPS 模式下存在 `map -> odom -> base_link`。
- 启用 OAK-D 时存在 `base_link -> oakd_imu_link -> oakd_camera_optical_frame`。
- 启用 MID360 或 LIO 时存在 `base_link -> mid360_link`。
- 静态外参的平移值与实测安装值一致，单位为米。

### 6.4 OAK-D 单独调试

先只启动 OAK-D 统一节点，不启动完整导航栈：

```bash
src/oakd_perception/scripts/run_oakd_balance.sh
```

另开终端检查数据频率和 frame_id：

```bash
./scripts/with_venv.sh ros2 topic hz /oakd/imu/raw
./scripts/with_venv.sh ros2 topic hz /oakd/left/image_raw
./scripts/with_venv.sh ros2 topic hz /oakd/right/image_raw
./scripts/with_venv.sh ros2 topic hz /oakd/points_filtered
./scripts/with_venv.sh ros2 topic echo --once /oakd/imu/raw/header
./scripts/with_venv.sh ros2 topic echo --once /oakd/points_filtered/header
```

通过标准：

- `/oakd/imu/raw` 持续发布，`header.frame_id` 为 `oakd_imu_link`。
- `/oakd/left/image_raw` 和 `/oakd/right/image_raw` 持续发布。
- `/oakd/points_filtered` 或 `/oakd/points` 持续发布，`header.frame_id` 为 `oakd_camera_optical_frame`。
- 没有 `X_LINK_DEVICE_ALREADY_IN_USE`，即没有多个进程同时占用 OAK-D。

#### 6.4.1 OAK-D RViz 配置

启动 RViz：

```bash
./scripts/with_venv.sh rviz2
```

仅调试 OAK-D 点云轴向时：

- `Global Options -> Fixed Frame` 设置为 `oakd_camera_optical_frame`。
- 添加 `PointCloud2`，Topic 选择 `/oakd/points_filtered`。
- 可额外添加 `/oakd/points` 对比过滤前点云。

接入 TF 链路后：

- `Fixed Frame` 改为 `base_link` 或 `map`。
- 添加 `TF` 显示，确认 `base_link -> oakd_imu_link -> oakd_camera_optical_frame` 连通。
- 添加 `PointCloud2`，Topic 选择 `/oakd/points_filtered`。

OAK-D 方向验收动作：

- 在相机前方 1 m 左右放置纸箱或墙面，点云应出现在相机前方。
- 将物体移到无人机左侧，切到 `base_link` 后点云应主要落在 `+Y`。
- 将物体抬高，切到 `base_link` 后点云应主要落在 `+Z`。
- 如果在 `oakd_camera_optical_frame` 下已经上下或左右翻转，优先检查 `oakd_imu_link -> oakd_camera_optical_frame`。
- 如果在 `oakd_camera_optical_frame` 下正确，但切到 `base_link` 后整体偏移或旋转，检查 `base_link -> oakd_imu_link`。

#### 6.4.2 OAK-D Foxglove 配置

Foxglove 推荐通过 ROS 2 原生连接或 `foxglove_bridge` 连接同一个 ROS_DOMAIN_ID。若使用 bridge：

```bash
./scripts/with_venv.sh ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765
```

然后在 Foxglove 中连接：

```text
ws://localhost:8765
```

Foxglove 3D 面板配置：

- 添加 `/tf` 和 `/tf_static`。
- Fixed Frame 先选 `oakd_camera_optical_frame` 做单传感器检查。
- 接入 EKF 后 Fixed Frame 改为 `base_link` 或 `map`。
- 添加 PointCloud 话题 `/oakd/points_filtered`。
- 添加 Raw Messages 面板，观察 `/oakd/imu/raw/header` 和 `/oakd/points_filtered/header`。

Foxglove 通过标准与 RViz 相同：点云在相机自身坐标系下方向正确，转到 `base_link` 后与无人机前后左右上下方向一致。

### 6.5 OAK-D 机体安装外参验收

启动 OAK-D + EKF/TF 链路：

```bash
./scripts/run_nav_stack.sh enable_gps:=false
```

如果只想看静态 TF，不需要完整规划栈：

```bash
./scripts/with_venv.sh ros2 launch uav_bringup ekf_launch.py enable_gps:=false
```

检查 TF：

```bash
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link oakd_imu_link
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link oakd_camera_optical_frame
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map oakd_camera_optical_frame
```

通过标准：

- `base_link -> oakd_imu_link` 的 `translation` 与尺量安装值一致。
- `rotation` 与安装姿态一致；正常正装且 OAK-D 机身坐标与 `base_link` 一致时为 0。
- RViz/Foxglove Fixed Frame 为 `base_link` 时，前方障碍在 `+X`，左侧障碍在 `+Y`，上方障碍在 `+Z`。
- Fixed Frame 为 `map` 时，点云随无人机姿态变化仍能稳定落在正确方向。

修改位置：

```text
src/uav_bringup/launch/ekf_launch.py
base_link -> oakd_imu_link
```

注意：这里不要填 `body_T_cam0/body_T_cam1`，也不要填 `oakd_imu_link -> oakd_camera_optical_frame` 的旋转。

### 6.6 VINS 外参与里程计验收

启动 OAK-D VINS 链路：

```bash
./scripts/run_nav_stack.sh enable_gps:=false
```

检查 VINS 和 EKF 输出：

```bash
./scripts/with_venv.sh ros2 topic hz /vio/odometry
./scripts/with_venv.sh ros2 topic echo --once /vio/odometry
./scripts/with_venv.sh ros2 topic hz /odometry/local
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map base_link
```

验收动作：

- 静止 30 秒，观察 `/vio/odometry` 是否连续，位置漂移不应快速发散。
- 手持或固定机体缓慢向前移动，`/vio/odometry` 与 `/odometry/local` 的主运动方向应为 `+X`。
- 左移时主运动方向应为 `+Y`，上抬时主运动方向应为 `+Z`。
- 小角度 yaw 旋转时，姿态变化方向应与实际旋转一致。

通过标准：

- `/vio/odometry` 持续输出，没有频繁重初始化。
- `/odometry/local` 持续输出，`map -> odom -> base_link` 连通。
- `/vio/odometry.child_frame_id` 与当前 VINS body 语义一致，项目中应为 `oakd_imu_link`。
- VINS 的 TF 输出仍隔离在 `/vins/tf`，不会向主 `/tf` 引入 `world/body/camera` 冲突。

如果失败，按顺序检查：

1. OAK-D 左右图像和 IMU 频率是否稳定。
2. `src/VINS-Fusion-ros2/config/oakd/oakd_stereo_imu_config.yaml` 中 `body_T_cam0/body_T_cam1` 是否和 OAK-D 内部光学帧方向一致。
3. `estimate_extrinsic` 是否符合当前测试目标；静态验收建议保持 `0`。
4. 图像和 IMU 时间戳是否存在明显不同步。

### 6.7 MID360 单独调试

MID360 需要先确认网口 IP 和驱动配置正确。主要配置文件：

```text
src/livox_ros_driver2/config/MID360_config.json
```

只启动 MID360 点云链路，不启动 OAK-D/VINS：

```bash
./scripts/run_nav_stack.sh --odom-source lio --pointcloud-source mid360
```

另开终端检查数据：

```bash
./scripts/with_venv.sh ros2 topic list | grep -E "/livox|/mid360"
./scripts/with_venv.sh ros2 topic hz /livox/lidar
./scripts/with_venv.sh ros2 topic hz /livox/imu
./scripts/with_venv.sh ros2 topic hz /mid360/points
./scripts/with_venv.sh ros2 topic echo --once /mid360/points/header
```

通过标准：

- `/livox/lidar` 和 `/livox/imu` 持续发布。
- `/mid360/points` 已由 `livox_custom_to_pointcloud2` 转换生成。
- `/mid360/points.header.frame_id` 为 `mid360_link`。
- RViz/Foxglove 中 Fixed Frame 为 `mid360_link` 时能看到稳定点云。

#### 6.7.1 MID360 RViz 配置

启动 RViz：

```bash
./scripts/with_venv.sh rviz2
```

仅调试 MID360 点云轴向时：

- `Global Options -> Fixed Frame` 设置为 `mid360_link`。
- 添加 `PointCloud2`，Topic 选择 `/mid360/points`。

接入 TF 链路后：

- `Fixed Frame` 改为 `base_link` 或 `map`。
- 添加 `TF` 显示，确认 `base_link -> mid360_link` 连通。
- 添加 `PointCloud2`，Topic 选择 `/mid360/points`。
- 如果使用双点云源，额外添加 `/perception/obstacle_points`。

MID360 方向验收动作：

- 在机体前方放置墙面或大纸箱，切到 `base_link` 后点云应主要落在 `+X`。
- 物体在机体左侧时点云应主要落在 `+Y`。
- 高处物体应主要落在 `+Z`。
- 如果 Fixed Frame 为 `mid360_link` 时点云正常，但切到 `base_link` 后方向或位置错误，检查 `base_link -> mid360_link`。

#### 6.7.2 MID360 Foxglove 配置

Foxglove 3D 面板配置：

- 添加 `/tf` 和 `/tf_static`。
- Fixed Frame 先选 `mid360_link` 做单传感器检查。
- 接入 TF 后 Fixed Frame 改为 `base_link` 或 `map`。
- 添加 PointCloud 话题 `/mid360/points`。
- 若使用 `both` 模式，添加 `/perception/obstacle_points`。
- 添加 Raw Messages 面板，观察 `/mid360/points/header`、`/livox/imu` 和 `/livox/lidar`。

通过标准：

- 点云在 `mid360_link` 下稳定。
- 点云转到 `base_link` 后，实物方向与 ROS ENU 机体系一致。
- `/tf_static` 中只有一个 `base_link -> mid360_link` 发布者语义，不出现重复父帧。

### 6.8 MID360 机体安装外参验收

`base_link -> mid360_link` 可通过 launch 参数临时覆盖，适合现场试外参：

```bash
./scripts/run_nav_stack.sh --odom-source lio --pointcloud-source mid360 \
  mid360_x:=0.08 \
  mid360_y:=0.0 \
  mid360_z:=0.05 \
  mid360_yaw:=0.0 \
  mid360_pitch:=0.0 \
  mid360_roll:=0.0
```

检查 TF：

```bash
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link mid360_link
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map mid360_link
```

通过标准：

- `base_link -> mid360_link` 的 `translation` 与实测安装值一致。
- `yaw/pitch/roll` 与 MID360 实际安装姿态一致。
- `/mid360/points` 切到 `base_link` 后，障碍物相对机体的位置不反、不整体旋转 90/180 度。
- `/local_map/occupancy` 使用 MID360 输入时，栅格障碍与点云方向一致。

固化默认值的位置：

```text
src/uav_bringup/launch/nav_stack.launch.py
LAUNCH_DEFAULTS['mid360_x/y/z/yaw/pitch/roll']
```

### 6.9 FAST-LIO 外参与里程计验收

纯 MID360/LIO 模式：

```bash
./scripts/run_nav_stack.sh --odom-source lio --pointcloud-source mid360
```

OAK-D VIO + MID360 LIO 并列融合：

```bash
./scripts/run_nav_stack.sh --odom-source both --pointcloud-source both
```

检查：

```bash
./scripts/with_venv.sh ros2 topic hz /lio/odometry
./scripts/with_venv.sh ros2 topic echo --once /lio/odometry
./scripts/with_venv.sh ros2 topic hz /odometry/local
```

通过标准：

- `/lio/odometry` 持续输出。
- 静止时姿态稳定，没有明显倾斜发散或周期性震荡。
- 缓慢前移时主运动方向与机体 `+X` 一致。
- `--odom-source both --pointcloud-source both` 模式下 `/odometry/local` 连续，EKF 不因 LIO 输入异常跳变。

FAST-LIO 内部外参修改位置：

```text
src/FAST_LIO_ROS2/config/mid360.yaml
mapping.extrinsic_T
mapping.extrinsic_R
```

注意：`extrinsic_T/R` 是 FAST-LIO 内部 LiDAR-IMU 外参，不是 `base_link -> mid360_link`。如果点云相对机体位置错，但 `/lio/odometry` 自身稳定，优先查 `base_link -> mid360_link`；如果 `/lio/odometry` 初始化失败、姿态发散或移动方向错，再查 `extrinsic_T/R`、时间同步和 MID360 IMU 数据。

### 6.10 联合链路验收

按使用模式分别启动：

```bash
# OAK-D VIO + OAK-D 点云避障
./scripts/run_nav_stack.sh

# MID360 点云替代 OAK-D 点云避障
./scripts/run_nav_stack.sh --odom-source vio --pointcloud-source mid360

# OAK-D 点云 + MID360 点云融合避障
./scripts/run_nav_stack.sh --odom-source vio --pointcloud-source both

# OAK-D VIO + MID360 FAST-LIO2 作为额外里程计
./scripts/run_nav_stack.sh --odom-source both --pointcloud-source both

# 纯 MID360 + FAST-LIO2
./scripts/run_nav_stack.sh --odom-source lio --pointcloud-source mid360
```

检查关键话题：

```bash
./scripts/with_venv.sh ros2 topic hz /odometry/local
./scripts/with_venv.sh ros2 topic hz /local_map/occupancy
./scripts/with_venv.sh ros2 topic hz /nav/cmd_vel
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map base_link
```

RViz 或 Foxglove 联合显示建议：

- Fixed Frame 设置为 `map`。
- 添加 `TF`。
- 添加 `/oakd/points_filtered`。
- 添加 `/mid360/points`。
- `both` 模式添加 `/perception/obstacle_points`。
- 添加 `/local_map/occupancy`。
- 添加 `/odometry/local`，必要时添加 `/vio/odometry` 和 `/lio/odometry` 对比。

最终通过标准：

- TF 树无断链、无重复父帧。
- OAK-D 点云、MID360 点云和局部地图在 `map` 下方向一致。
- 障碍物放在机体前方时，局部地图障碍也出现在前方。
- 移动机体或传感器后，点云和 `/odometry/local` 连续，不出现大幅跳变。
- `/nav/cmd_vel` 的方向与目标和障碍关系一致，没有因外参反向导致的错误避障。

### 6.11 常见问题排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| `No TF available from oakd_camera_optical_frame to map` | TF 链路不完整 | 检查所有静态变换是否启动；用 `view_frames` 查看断点 |
| TF 树中出现 `world`/`body` 帧 | VINS-Fusion 的 TF 未隔离 | 确认 `oakd_vins.launch.py` 中 remap 了 `/tf` → `/vins/tf` |
| `oakd_imu_link` 有两个父帧 | `imu_tf_broadcaster` 仍在运行 | 确认 `imu_fusion.launch.py` 中已移除 TF 广播节点 |
| `robot_localization` 报 `imu_link` 帧找不到 | PX4 IMU 的 `frame_id` 未更新 | 确认 `converters.py` 中 `frame_id` 已改为 `base_link` |
| 点云在 RViz 中位置偏移 | 相机外参未校准 | 测量并填入 `base_link→oakd_imu_link` 的实际偏移量 |
| `/mid360/points` 有数据但 Fixed Frame 为 `base_link` 不显示 | 缺少 `base_link -> mid360_link` | 确认以 `enable_mid360:=true` 或 `enable_lio:=true` 启动 EKF launch |
| `/livox/lidar` 有数据但没有 `/mid360/points` | 转换节点未启动 | 使用 `run_nav_stack.sh --odom-source vio --pointcloud-source mid360`，或确认 `obstacle_pointcloud_source:=mid360/both` |
| `/lio/odometry` 不输出 | FAST-LIO 输入不完整 | 确认 `/livox/lidar` 和 `/livox/imu` 都有频率 |
| 点云在传感器自身 frame 下正确，转到 `base_link` 后方向错误 | 机体安装外参错误 | 检查 `base_link -> oakd_imu_link` 或 `base_link -> mid360_link` |
| 里程计方向错误但点云方向正确 | VINS/FAST-LIO 内部外参或时间同步问题 | 检查 `body_T_cam*`、`extrinsic_T/R` 和传感器时间戳 |

---

## 7. 设计决策说明

### 7.1 为什么使用双级 EKF？

- **EKF_odom**（局部）：融合高频 VIO + IMU，提供平滑连续的 `odom→base_link`，用于实时避障和控制
- **EKF_map**（全局）：额外融合低频 GPS，周期性校正 `map→odom` 的累计漂移

分离的好处是：GPS 跳变不会直接影响局部定位的平滑性，避障等实时任务不受 GPS 质量波动影响。

### 7.2 为什么隔离 VINS-Fusion 的 TF？

VINS-Fusion 内部会发布 `world→body→camera` 的 TF 变换，其帧名（`world`、`body`、`camera`）与导航系统的标准帧名不同，且其位姿估计与 EKF 融合后的结果存在差异。如果两者同时写入 `/tf`，会导致：
- 帧名混乱
- 潜在的变换冲突

因此通过 remap 将 VINS 的 TF 输出到 `/vins/tf`，既避免冲突，又保留调试能力。

### 7.3 为什么移除 imu_tf_broadcaster？

`imu_tf_broadcaster` 发布 `map→oakd_imu_link` 的动态变换。在新架构中，从 `map` 到 `oakd_imu_link` 的路径已由 EKF + 静态外参链完整覆盖：

```
map → odom → base_link → oakd_imu_link
```

如果 `imu_tf_broadcaster` 同时发布 `map→oakd_imu_link`，`oakd_imu_link` 将有两个父帧，违反 TF 树规则。

### 7.4 PX4 IMU 的 frame_id 为什么设为 base_link？

PX4 飞控的 IMU 传感器物理上位于飞控板（FCU）中心，即 `base_link` 所在位置。将 `frame_id` 设为 `base_link` 后：
- `robot_localization` 无需查找额外的 TF 变换（`imu_link→base_link`）
- 消除了不存在的 `imu_link` 帧导致的 TF lookup 失败

---

## 8. 话题与帧 ID 对照表

| 话题 | 消息类型 | header.frame_id | 发布者 |
|------|----------|-----------------|--------|
| `/px4/imu` | `sensor_msgs/Imu` | `base_link` | px4_comm_bridge，角速度与线加速度 |
| `/px4/attitude` | `geometry_msgs/PoseWithCovarianceStamped` | `odom` | px4_comm_bridge，PX4 VehicleAttitude 转 ROS ENU 姿态 |
| `/vio/odometry` | `nav_msgs/Odometry` | `odom` | VINS-Fusion (remap, child: `oakd_imu_link`) |
| `/gps/fix` | `sensor_msgs/NavSatFix` | `gps_link` | px4_comm_bridge |
| `/odometry/local` | `nav_msgs/Odometry` | `odom` | ekf_filter_node_odom |
| `/odometry/global` | `nav_msgs/Odometry` | `map` | ekf_filter_node_map |
| `/odometry/gps` | `nav_msgs/Odometry` | `odom` | navsat_transform |
| `/oakd/imu/raw` | `sensor_msgs/Imu` | `oakd_imu_link` | oakd_unified_node |
| `/oakd/points_filtered` | `sensor_msgs/PointCloud2` | `oakd_camera_optical_frame` | oakd_unified_node |
| `/livox/lidar` | `livox_ros_driver2/CustomMsg` | 驱动内部设置 | livox_ros_driver2 |
| `/livox/imu` | `sensor_msgs/Imu` | 驱动内部设置 | livox_ros_driver2 |
| `/mid360/points` | `sensor_msgs/PointCloud2` | `mid360_link` | livox_custom_to_pointcloud2 |
| `/lio/odometry` | `nav_msgs/Odometry` | FAST-LIO 输出帧 | fast_lio_mapping |
| `/perception/obstacle_points` | `sensor_msgs/PointCloud2` | `base_link` | pointcloud_combiner |

---

## 更新记录

- **v2.0** (2026-05-17)：重构为双级 EKF 架构，修复 TF 树断裂与多父节点冲突
- **v1.0** (2026-05)：初版 TF 架构（单级 EKF + imu_tf_broadcaster）
