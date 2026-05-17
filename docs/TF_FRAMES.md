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
| `uav_bringup/launch/nav_stack.launch.py` | 完整导航栈入口 |

### 5.3 静态外参配置

**相机安装外参**（`base_link → oakd_imu_link`）：

在 `ekf_launch.py` 中修改以下参数，单位为米和弧度：
```python
# arguments: [x, y, z, yaw, pitch, roll, parent_frame, child_frame]
# 坐标约定: ROS ENU (X-前, Y-左, Z-上)
arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'oakd_imu_link'],
```

> **重要**：同时需要在 PX4 QGC 参数中设置对应的 Lever Arm 补偿（NED 坐标系）：
> - `EKF2_EV_POS_X` = dx（与 ROS X 相同）
> - `EKF2_EV_POS_Y` = −dy（ROS Y 取反）
> - `EKF2_EV_POS_Z` = −dz（ROS Z 取反）

---

## 6. 调试与验证

### 6.1 查看 TF 树

```bash
# 生成 TF 树 PDF（最常用）
ros2 run tf2_tools view_frames

# 实时查看特定变换
ros2 run tf2_ros tf2_echo map base_link

# 查看所有 TF 广播
ros2 topic echo /tf
ros2 topic echo /tf_static
```

### 6.2 常见问题排查

| 现象 | 原因 | 解决方法 |
|------|------|----------|
| `No TF available from oakd_camera_optical_frame to map` | TF 链路不完整 | 检查所有静态变换是否启动；用 `view_frames` 查看断点 |
| TF 树中出现 `world`/`body` 帧 | VINS-Fusion 的 TF 未隔离 | 确认 `oakd_vins.launch.py` 中 remap 了 `/tf` → `/vins/tf` |
| `oakd_imu_link` 有两个父帧 | `imu_tf_broadcaster` 仍在运行 | 确认 `imu_fusion.launch.py` 中已移除 TF 广播节点 |
| `robot_localization` 报 `imu_link` 帧找不到 | PX4 IMU 的 `frame_id` 未更新 | 确认 `converters.py` 中 `frame_id` 已改为 `base_link` |
| 点云在 RViz 中位置偏移 | 相机外参未校准 | 测量并填入 `base_link→oakd_imu_link` 的实际偏移量 |

### 6.3 验证 TF 树完整性

```bash
# 验证关键变换链存在
ros2 run tf2_ros tf2_echo map oakd_camera_optical_frame
# 应输出有效变换，无超时错误

# 验证无重复父帧
ros2 run tf2_tools view_frames
# 检查生成的 PDF，确认每个帧仅有一个父帧
```

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

---

## 更新记录

- **v2.0** (2026-05-17)：重构为双级 EKF 架构，修复 TF 树断裂与多父节点冲突
- **v1.0** (2026-05)：初版 TF 架构（单级 EKF + imu_tf_broadcaster）
