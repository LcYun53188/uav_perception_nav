# uav_vision_ws（统一使用 .venv）

本仓库提供针对 OAK‑D 相机的深度点云与 IMU 采集、融合与可视化工具集，全部以项目虚拟环境 `.venv` 运行为约定。本文档已重构为更清晰的结构：快速上手 → 架构概览 → 安装/构建 → 运行/调试 → 配置/参数 → 可视化 → 测试/回放 → 坐标系/TF → 故障排查 → 项目结构。

## 当前状态

当前仓库的状态是“开发/仿真可用，硬件验收待补齐”：

- OAK-D 统一节点、VINS-Fusion 视觉惯导里程计、PX4 姿态/IMU/GPS 桥接、双级 EKF 状态融合、局部建图、安全监控、PX4 控制桥接与启动编排已实现；
- 导航栈已经形成点云 → 占用栅格 → `/nav/cmd_vel` → 安全监控 → PX4 桥接的完整管道；
- TF 树采用双级 EKF 架构，支持 GPS / 无 GPS 两种模式切换（`enable_gps` 参数）；
- 默认局部规划器已切换为 `se2_dwa_local_planner`，在二维平面采样 `vx/vy/yaw_rate`，并通过 PX4 velocity/yawspeed setpoint 输出；
- `px4_msgs` 为可选依赖，缺失时桥接层会降级运行；
- 真机飞行验收、障碍物感知规划与 3D 导航主方案仍在后续迭代中。

---

## 快速开始 (Quick Start)

按下面三步快速跑通：

1. 初始化并激活虚拟环境：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv
uv pip install --python .venv/bin/python -e src/oakd_perception
uv pip install --python .venv/bin/python depthai
source .venv/bin/activate
```

2. 构建当前已实现的核心包：

```bash
./scripts/with_venv.sh colcon build --packages-select oakd_perception imu_fusion vins_fusion_ros2 robot_localization nav_mapping nav_planning nav_safety px4_comm_bridge nav_local uav_bringup px4_msgs
source install/setup.bash
```

3. 启动对应系统：

- 仅看 OAK-D 感知：`./scripts/run_oakd_unified.sh`
- 启动导航栈：`ros2 launch uav_bringup nav_stack.launch.py`

4. 打开 RViz：按脚本提示将 `Fixed Frame` 设为 `map`，再添加 `/oakd/points` 或 `/local_map/occupancy` 显示。

---

## 当前完成度与边界

当前仓库不是“只有感知底座”，而是已经形成了可运行的导航管线；但从算法完整性上看，它仍然处于“基础链路完成、规划策略原型化”的阶段。

已完成：

- OAK-D 统一节点与 IMU / 深度同进程采集；
- VINS-Fusion、PX4 姿态源与双级 EKF 定位链路；
- `nav_mapping`、`nav_planning`、`nav_safety`、`px4_comm_bridge`、`uav_bringup` 的基础集成；
- 系统级联调与单元/集成测试。

仍需补齐：

- 真机环境下 SE(2) DWA 参数整定、速度/偏航速率限幅与飞行验收；
- 真机飞行前的完整验收；
- 更进一步的 3D 地图、ESDF 或体素导航。

详细对比见 [docs/PX4_NAVIGATION_STRATEGY.md](./docs/PX4_NAVIGATION_STRATEGY.md)。

---

## 本文档结构（目录）

- 概览
- 快速开始
- 架构说明
- 安装与构建
- 运行与启动
  - 快速启动脚本
  - 手动运行示例
  - 统一节点（IMU + 深度）
  - IMU 与姿态链路
- 配置与参数
- 可视化（RViz）
- 测试与验证（在线/离线）
- 坐标系与 TF 说明
- 故障排查
- 项目文件结构
- 附录：配置文件位置

---

## 1. 概览

本仓库提供：

- `oakd_perception`：负责 OAK‑D 设备的深度点云与原始 IMU 采集（包含可配置的立体深度参数）；
- `VINS-Fusion-ros2`：接收 OAK-D 双目图像与 OAK-D IMU，输出 VIO 里程计；
- `robot_localization`：接收 VIO、PX4 姿态、PX4 IMU 与可选 GPS，输出主定位 TF 与里程计；
- `imu_fusion`：接收 OAK-D 原始 IMU，输出 `/oakd/imu/fused`，当前作为调试/备用链路，不发布主 TF；
- `nav_mapping`、`nav_planning`、`nav_safety`、`px4_comm_bridge`：提供局部建图、基础规划、安全监控与 PX4 数据/控制桥接；
- `uav_bringup`：统一启动编排与中央参数管理；
- 多个启动脚本与配置预设，便于在室内/户外/黑暗场景间切换。

推荐使用“一体化/统一节点”方案（在单进程中同时管理深度与 IMU），避免设备冲突（X_LINK_DEVICE_ALREADY_IN_USE）。详见后文“统一节点”节与 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

### 1.1 包职责与话题接口

下面汇总当前仓库主要功能包的职责，以及它们直接订阅/发布的话题。没有直接话题接口的包，说明其职责主要是启动编排、兼容层或消息定义。

| 包 | 职责 | 订阅 | 发布 |
|---|---|---|---|
| `oakd_perception` | OAK-D 图像、点云与原始 IMU 采集 | - | `/oakd/imu/raw`，`/oakd/left/image_raw`，`/oakd/right/image_raw`，`/oakd/points`，`/oakd/points_filtered` |
| `VINS-Fusion-ros2` | 双目视觉惯导里程计 | `/oakd/left/image_raw`，`/oakd/right/image_raw`，`/oakd/imu/raw` | `/vio/odometry`，`/vins/tf` |
| `robot_localization` | 双级 EKF 与 GPS 转换 | `/vio/odometry`，`/px4/attitude`，`/px4/imu`，可选 `/gps/fix` | `/odometry/local`，可选 `/odometry/global`、`/odometry/gps`，`/tf` |
| `imu_fusion` | OAK-D IMU 预融合/调试链路 | `/oakd/imu/raw` | `/oakd/imu/fused` |
| `nav_mapping` | 点云投影与局部占用栅格生成 | `/oakd/points_filtered`，`/tf`，`/tf_static` | `/local_map/occupancy` |
| `nav_planning` | SE(2) DWA 二维局部规划与速度/偏航速率决策 | `/local_map/occupancy`，`/tf`，目标话题 | `/nav/cmd_vel` |
| `nav_safety` | 点云、TF、里程计与 PX4 状态安全监控 | `/oakd/points`，`/tf`，`/odometry/local` | `/nav/emergency`，`/nav/safety_status` |
| `px4_comm_bridge` | PX4 数据/控制桥接与看门狗 | `/nav/cmd_vel`，`/nav/emergency`，`/nav/safety_status`，PX4 uORB ROS 话题 | `/px4/odom`，`/px4/imu`，`/px4/attitude`，`/gps/fix`，`/fmu/in/*` |
| `nav_local` | 向后兼容层（转发旧入口到新包） | - | - |
| `uav_bringup` | 统一启动编排与参数管理 | - | - |
| `px4_msgs` | PX4 消息定义包 | - | - |

说明：

- `px4_comm_bridge` 会在 `px4_msgs` 可用时开启 PX4 相关订阅/发布，不可用时自动降级；
- `nav_local` 目前只保留兼容入口，不承担新的业务逻辑；
- `uav_bringup` 主要负责 launch 与配置聚合，不直接发布业务话题。

---

## 2. 架构说明

简要架构（逻辑视图）：

```
单一 OAK-D 设备
      ↓
  DAI Pipeline (单进程)
   ├─ IMU 采样 → /oakd/imu/raw  (400Hz)
   ├─ 左右目图像 → /oakd/left/image_raw, /oakd/right/image_raw
   └─ 深度处理 → /oakd/points, /oakd/points_filtered  (~20Hz)

VIO 链路：   双目图像 + /oakd/imu/raw → VINS-Fusion → /vio/odometry
PX4 数据：   PX4 uORB ROS 话题 → px4_comm_bridge → /px4/attitude, /px4/imu, /gps/fix
定位链路：   /vio/odometry + /px4/attitude + /px4/imu [+ /gps/fix] → 双级 EKF → TF(map→odom→base_link)
导航链路：   /oakd/points_filtered + 主 TF → /local_map/occupancy → SE(2) DWA → /nav/cmd_vel → px4_comm_bridge → PX4 velocity/yawspeed
```

TF 树：`map → odom → base_link → oakd_imu_link → oakd_camera_optical_frame`

要点：
- 将 IMU 与深度放在同一进程（统一节点）避免 USB/设备冲突；
- 双级 EKF 架构：`ekf_odom` 发布 `odom→base_link`，`ekf_map` 发布 `map→odom`（GPS 校正）；
- VINS 自身 TF 被隔离到 `/vins/tf`，主 `/tf` 只由 EKF 与静态外参发布器维护；
- PX4 姿态通过 `/px4/attitude` 单独输入 EKF，`/px4/imu` 只承担角速度与线加速度输入；
- 无 GPS 模式下 `map→odom` 为静态恒等变换，局部避障照常工作；
- 详细 TF 说明见 [docs/TF_FRAMES.md](./docs/TF_FRAMES.md)。

---

## 3. 安装与构建

本节简述关键步骤。详细信息见 [**docs/INSTALLATION.md**](./docs/INSTALLATION.md)。

### 3.1 快速步骤

```bash
# 1. 安装 uv 并创建虚拟环境
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv

# 2. 安装依赖
uv pip install --python .venv/bin/python -e src/oakd_perception depthai

# 3. 构建核心包
./scripts/with_venv.sh colcon build --packages-select oakd_perception imu_fusion vins_fusion_ros2 robot_localization nav_mapping nav_planning nav_safety px4_comm_bridge nav_local uav_bringup px4_msgs

# 4. 激活工作区
source install/setup.bash
```

### 3.2 完整配置指南

所有细节（环境激活、依赖管理、VS Code 配置、故障排查等）请查阅 [**docs/INSTALLATION.md**](./docs/INSTALLATION.md)。

---

## 4. 运行与启动

本节集中说明启动脚本、手动运行示例，以及统一节点与 IMU 链路的使用方式。

### 4.0 启动前准备

启动前建议先完成以下检查：

```bash
cd /home/nuc/Program/uav_vision_ws
source .venv/bin/activate
source install/setup.bash
```

如果是首次部署或刚完成构建，请先确认这些包已经编译成功：`oakd_perception`、`imu_fusion`、`vins_fusion_ros2`、`robot_localization`、`nav_mapping`、`nav_planning`、`nav_safety`、`px4_comm_bridge`、`nav_local`、`uav_bringup`。

推荐的调度关系由 `uav_bringup/launch/nav_stack.launch.py` 统一编排：

1. `oakd_perception`：启动 OAK-D 统一节点，发布图像、IMU 和点云；
2. `imu_fusion`：启动 OAK-D IMU 预融合节点，作为调试/备用输出；
3. `VINS-Fusion-ros2`：消费 OAK-D 双目图像与 IMU，发布 `/vio/odometry`；
4. `uav_bringup/ekf_launch.py`：启动 `robot_localization`，融合 VIO、PX4 姿态、PX4 IMU 和可选 GPS；
5. `nav_mapping` / `nav_planning` / `nav_safety`：使用主 TF、点云和定位输出完成建图、规划和安全监控；
6. `px4_comm_bridge`：接收 `/nav/cmd_vel` 与安全状态，输出 PX4 offboard 控制，同时发布 PX4 数据源。

如果只调试 OAK-D 感知，可单独使用 `./scripts/run_oakd_unified.sh`。如果验证完整导航链路，优先使用 `ros2 launch uav_bringup nav_stack.launch.py`。

### 4.1 快速启动脚本（推荐）

项目提供四个场景预设脚本（位于 `scripts/`）：

| 脚本 | 被动立体 | 主动立体 | 场景 |
|------|---------|---------|------|
| `run_oakd_outdoor.sh` | ✓ | ✗ | 户外强光（低功耗） |
| `run_oakd_indoor.sh`  | ✓ | ✓ | 室内弱光（高精度） |
| `run_oakd_balance.sh` | ✓ | ✓ | 平衡模式（通用） |
| `run_oakd_active_max.sh` | ✗ | ✓ | 黑暗环境（最高密度） |

使用示例：

```bash
./scripts/run_oakd_balance.sh
```

每个脚本会：激活 `.venv` → 加载 ROS2 环境 → 读取 YAML 配置 → 启动点云发布节点。

适合的场景：

- `run_oakd_outdoor.sh`：户外光照充足、优先低功耗；
- `run_oakd_indoor.sh`：室内或弱光环境、优先精度；
- `run_oakd_balance.sh`：默认推荐模式；
- `run_oakd_active_max.sh`：黑暗环境、优先主动红外照明。

### 4.2 手动运行示例（可传参）

```bash
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node --ros-args \
  -p enable_passive_stereo:=true \
  -p enable_active_stereo:=true \
  -p ir_intensity:=800 \
  -p sampling_step:=2 \
  -p min_depth:=200 \
  -p max_depth:=5000
```

运行后列出话题以确认：

```bash
./scripts/with_venv.sh ros2 topic list | grep /oakd/points
```

### 4.3 统一节点（推荐：IMU + 深度同进程）

**问题**：旧架构中分别运行 IMU 节点和深度节点会引起设备被占用错误（X_LINK_DEVICE_ALREADY_IN_USE）。

**解决**：使用 `oakd_unified_node` 在单一进程中同时处理 IMU 与深度。

启动（推荐使用脚本）：

```bash
./scripts/run_oakd_unified.sh
```

`scripts/run_complete_system.sh` 是旧的 OAK-D + IMU 融合 + RViz 调试脚本，不是当前完整导航栈入口。完整调度请使用 `ros2 launch uav_bringup nav_stack.launch.py`。

统一节点常用参数示例：

```bash
./scripts/with_venv.sh ros2 launch oakd_perception oakd_unified.launch.py \
  enable_passive_stereo:=true enable_active_stereo:=true ir_intensity:=1000 pointcloud_frequency:=30
```

统一节点发布的主题（常见）：

- `/oakd/imu/raw` — 原始 IMU（Imu）约 400Hz
- `/oakd/left/image_raw`、`/oakd/right/image_raw` — 双目灰度图像，供 VINS 使用
- `/oakd/points` — 深度点云（PointCloud2）约 20Hz
- `/oakd/points_filtered` — 过滤后的深度点云，供建图/安全监控使用

### 4.4 IMU 与姿态链路

当前主定位链路中，姿态来源不是 `/px4/imu.orientation`，而是单独的 `/px4/attitude`：

```text
PX4 /fmu/out/vehicle_attitude
  → px4_comm_bridge
  → /px4/attitude
  → robot_localization pose0，仅融合 roll/pitch

PX4 /px4/vehicle_imu
  → px4_comm_bridge
  → /px4/imu
  → robot_localization imu0，仅融合角速度与线加速度
```

OAK-D 自身 IMU 链路仍保留：

```text
/oakd/imu/raw → imu_fusion → /oakd/imu/fused
```

该链路用于调试、预览和后续扩展；当前主 TF 树不依赖 `imu_fusion` 发布动态 TF。

手动调试 OAK-D IMU 预融合：

```bash
./scripts/run_oakd_unified.sh
./scripts/run_imu_fusion_tf.sh
```

注意：不要让旧的 `imu_tf_broadcaster` 向主 `/tf` 发布 `map -> oakd_imu_link`，否则 `oakd_imu_link` 会同时拥有 EKF 静态链路和 IMU 动态链路两个父帧。

### 4.5 导航栈

导航栈通过统一入口启动，支持 GPS / 无 GPS 两种模式：

```bash
# 无 GPS 模式（默认）
ros2 launch uav_bringup nav_stack.launch.py

# GPS 模式
ros2 launch uav_bringup nav_stack.launch.py enable_gps:=true
```

启动后的预期行为：

- `ekf_filter_node_odom` 融合 VIO + PX4 姿态 + PX4 IMU，发布 `odom→base_link` TF 和 `/odometry/local`；
- `px4_comm_bridge` 发布 `/px4/attitude`、`/px4/imu`、`/gps/fix`，其中姿态与 IMU 在 EKF 中分开融合；
- GPS 模式下 `ekf_filter_node_map` 额外融合 GPS，发布 `map→odom` TF 和 `/odometry/global`；
- `local_map_builder` 订阅 `/oakd/points_filtered`，通过 TF 投影生成 `/local_map/occupancy`；
- `se2_dwa_local_planner` 消费局部栅格、目标与 TF，发布 `/nav/cmd_vel`，其中 `linear.x/y` 为 ENU 平面速度，`angular.z` 为 ENU yaw rate；
- `safety_monitor` 订阅 `/oakd/points` 并发布 `/nav/emergency`；
- `px4_comm_bridge` 桥接到 PX4，不可用时降级运行。

注意：旧 `local_planner` 仍保留为兼容/回退入口；统一导航栈默认使用 `se2_dwa_local_planner`。

### 4.6 一键验证顺序

如果你想按最少步骤确认整个仓库的启动链路，建议使用下面这个顺序：

```bash
cd /home/nuc/Program/uav_vision_ws
source .venv/bin/activate
source install/setup.bash

# 1. OAK-D 感知
./scripts/run_oakd_unified.sh

# 2. 导航栈（另一个终端）
ros2 launch uav_bringup nav_stack.launch.py
```

检查点：

- `/oakd/imu/raw` 是否存在；
- `/vio/odometry` 是否在相机运动后输出；
- `/px4/attitude` 与 `/px4/imu` 是否存在，PX4 未连接时可先跳过；
- `/oakd/points`、`/oakd/points_filtered` 是否持续发布；
- `/odometry/local` 和 `map -> odom -> base_link` 是否正常；
- `/local_map/occupancy`、`/nav/cmd_vel`、`/nav/emergency` 是否正常；
- 若使用 PX4，再检查 `/fmu/in/*` 是否有消息。

---

## 5. 配置与参数

### 5.1 立体深度模式参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_passive_stereo` | bool | true | 被动立体（纹理匹配） |
| `enable_active_stereo`  | bool | false | 主动红外投影 |
| `ir_intensity`          | int  | 1600  | 红外强度（0-1600） |

### 5.2 点云过滤与下采样

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sampling_step` | int | 2 | 下采样步长（1=无） |
| `min_depth`     | int | 200 | 最小深度（mm） |
| `max_depth`     | int | 5000 | 最大深度（mm） |

### 5.3 预设配置文件

位置：`src/oakd_perception/config/`

- `outdoor_low_power.yaml` — 户外低功耗
- `indoor_high_precision.yaml` — 室内高精度
- `balanced_mode.yaml` — 平衡模式
- `active_stereo_max.yaml` — 黑暗场景最高密度

---

## 6. 可视化（RViz）

### 6.1 启动 RViz 并添加点云

```bash
./scripts/with_venv.sh rviz2
```

设置建议：

- `Fixed Frame`：`map`（完整导航链路）或 `oakd_camera_optical_frame`（仅调试 OAK-D 点云）；
- 添加 `PointCloud2`，选择 `/oakd/points_filtered` 或 `/oakd/points`；
- 调整 `Style`、`Size`（0.01–0.05m）、`Color Transformer`（Intensity/RGB/FlatColor）。

### 6.2 若要点云进入主 TF 树

- 确保 `oakd_unified.launch.py` 发布 `oakd_imu_link -> oakd_camera_optical_frame`；
- 确保 `ekf_launch.py` 发布 `map -> odom -> base_link -> oakd_imu_link`；
- 将 RViz `Fixed Frame` 设为 `map`；
- 添加 `TF` 显示以验证 frame 关系。

---

## 7. 测试与验证

### 7.1 在线系统检查

```bash
./scripts/run_oakd_unified.sh
source install/setup.bash
ros2 launch uav_bringup nav_stack.launch.py
./scripts/with_venv.sh ros2 topic list | grep -E "/oakd/points|/oakd/imu|/oakd/.*/image_raw"
./scripts/with_venv.sh ros2 topic list | grep -E "/vio/odometry|/px4/attitude|/px4/imu|/odometry/local"
./scripts/with_venv.sh ros2 topic list | grep -E "/local_map/occupancy|/nav/cmd_vel|/nav/emergency|/fmu/in/"
./scripts/with_venv.sh ros2 topic hz /oakd/points
./scripts/with_venv.sh ros2 topic hz /vio/odometry
./scripts/with_venv.sh ros2 topic hz /odometry/local
./scripts/with_venv.sh ros2 topic hz /nav/cmd_vel
./scripts/with_venv.sh ros2 topic hz /nav/emergency
```

### 7.2 录制与离线回放（ros2 bag）

```bash
./scripts/with_venv.sh ros2 bag record -o test_run /oakd/points_filtered /vio/odometry /odometry/local /tf /tf_static
# 停止录制后回放
./scripts/with_venv.sh ros2 bag play test_run_0.db3
```

### 7.3 常用调试命令

```bash
# 列出 oakd 相关进程
ps aux | grep oakd | grep -v grep
# 强制停止
pkill -9 -f "oakd"
# 检查 depthai
./scripts/with_venv.sh python -c "import depthai, sys; print('depthai', depthai.__version__)"
# 导出 TF 拓扑
./scripts/with_venv.sh ros2 run tf2_tools view_frames
```

---

## 8. 坐标系与 TF 说明

TF 树（双级 EKF 架构）：

```
map → odom → base_link → oakd_imu_link → oakd_camera_optical_frame
                 │
                 └→ gps_link
```

| 坐标系 | 含义 |
|--------|------|
| `map` | 全局固定参考系（ENU 东北天） |
| `odom` | 里程计累计参考系 |
| `base_link` | 无人机机身中心（飞控 FCU 质心） |
| `oakd_imu_link` | OAK-D 相机 IMU 中心 |
| `oakd_camera_optical_frame` | 相机镜头光学中心（点云参考系） |
| `gps_link` | GPS 天线位置 |

检查 TF：

```bash
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo map base_link
```

详细说明（帧定义、发布关系、配置方法、调试排查）请见 [**docs/TF_FRAMES.md**](./docs/TF_FRAMES.md)。

---

## 9. 故障排查

- 常见问题：ModuleNotFoundError: depthai → 确认 `.venv` 中安装 depthai（见第 3 节）。
- 设备冲突：优先使用统一节点或确保仅有一个进程访问设备。可用 `pkill` 停止冗余进程。
- RViz 不显示点云：检查话题 `/oakd/points`、Fixed Frame 与 TF 链路。
- 导航栈持续发布零速度：检查 `/local_map/occupancy` 是否超时、`map→base_link` TF 是否存在，以及 `/nav/emergency` 是否为 true。

常用排查命令见第 7 节。

---

## 10. 项目文件结构

```
uav_vision_ws/
├── src/oakd_perception/                  # OAK-D 统一节点（IMU + 深度 + 点云）
├── src/imu_fusion/                       # OAK-D IMU 预融合/调试链路
├── src/VINS-Fusion-ros2/                 # 双目视觉惯导里程计（VIO）
├── src/robot_localization/               # 双级 EKF 状态融合
├── src/nav_mapping/                      # 点云到局部占用栅格
├── src/nav_planning/                     # 基础局部规划策略
├── src/nav_safety/                       # 安全监控与紧急信号
├── src/px4_comm_bridge/                  # PX4 数据/控制桥接（姿态 + IMU + GPS + 控制）
├── src/uav_bringup/                      # 导航栈启动编排
│   ├── launch/ekf_launch.py             #   双级 EKF + GPS 开关 + 静态外参
│   ├── launch/nav_stack.launch.py       #   完整导航栈入口
│   └── config/dual_ekf.yaml             #   EKF + NavSat 配置
├── src/px4_msgs/                         # PX4 消息定义（可选依赖）
├── scripts/                              # 快速启动脚本与工具
├── docs/                                 # 文档
│   ├── TF_FRAMES.md                     #   TF 坐标变换系统说明
│   ├── ARCHITECTURE.md                  #   系统架构设计
│   └── ...
└── README.md
```

---

## 附录：配置文件位置

`src/oakd_perception/config/` 包含预设 YAML，可直接修改或拷贝为自定义配置并在脚本/launch 中引用。

---
