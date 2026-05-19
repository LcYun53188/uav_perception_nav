# uav_vision_ws（统一使用 .venv）

本仓库提供针对 OAK‑D 相机、PX4 与可选 Livox MID360 激光雷达的感知、定位、局部建图、规划、安全监控和启动编排工具集，全部以项目虚拟环境 `.venv` 运行为约定。本文档已重构为更清晰的结构：快速上手 → 架构概览 → 安装/构建 → 运行/调试 → 配置/参数 → 可视化 → 测试/回放 → 坐标系/TF → 故障排查 → 项目结构。

## 当前状态

当前仓库的状态是“开发/仿真可用，硬件验收待补齐”：

- OAK-D 统一节点、VINS-Fusion 视觉惯导里程计、PX4 姿态/IMU/GPS 桥接、双级 EKF 状态融合、局部建图、安全监控、PX4 控制桥接与启动编排已实现；
- 导航栈已经形成点云 → 占用栅格 → `/nav/cmd_vel` → 安全监控 → PX4 桥接的完整管道；
- TF 树采用双级 EKF 架构，支持 GPS / 无 GPS 两种模式切换（`enable_gps` 参数）；
- 默认局部规划器已切换为 `se2_dwa_local_planner`，在二维平面采样 `vx/vy/yaw_rate`，并通过 PX4 velocity/yawspeed setpoint 输出；
- 已引入 MID360 接入链路：`livox_ros_driver2`、Livox-SDK2、FAST-LIO2、Livox CustomMsg 到 PointCloud2 转换、LIO 里程计接入和 OAK-D/MID360/both 点云源切换；
- MID360 相关第三方源码采用 `submodule + patches/vendor/*.patch` 管理，父仓库不直接保存这些第三方源码改动；
- `px4_msgs` 为可选依赖，缺失时桥接层会降级运行；
- 真机飞行验收、MID360 实机网络/外参标定、LIO 与 VIO 长时间一致性验证、3D 导航主方案仍在后续迭代中。

---

## 快速开始 (Quick Start)

按下面步骤从克隆到运行快速跑通。

克隆注意点：

- 不要用 GitHub/Gitee 的 ZIP 下载方式。ZIP 不包含 submodule 的 Git 元数据，后续无法可靠复刻第三方依赖。
- 推荐直接递归克隆；如果已经普通克隆，也必须执行 `git submodule update --init --recursive`。
- 第三方 submodule 拉取后不要手动提交其内部改动；本项目通过 `patches/vendor/*.patch` 记录适配。
- 之后所有 ROS / Python 命令优先使用 `./scripts/with_venv.sh`，保证使用项目 `.venv`。

1. 克隆仓库并进入工作区：

```bash
# 推荐：递归克隆，一次性拉取 px4_msgs、livox_ros_driver2、FAST_LIO_ROS2、Livox-SDK2 等 submodule
git clone --recurse-submodules <repo-url> uav_vision_ws
cd uav_vision_ws

# 如果已经用普通 git clone 拉取，则在仓库根目录补执行：
git submodule update --init --recursive
```

检查 submodule 是否正确：

```bash
git submodule status --recursive
git ls-files --stage src/livox_ros_driver2 src/FAST_LIO_ROS2 third_party/Livox-SDK2
```

三个 MID360 相关路径在 `git ls-files --stage` 中应显示为 `160000` 类型，而不是大量普通源码文件。

2. 初始化并激活虚拟环境：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv
uv pip install --python .venv/bin/python -e src/oakd_perception
uv pip install --python .venv/bin/python depthai
source .venv/bin/activate
```

3. 拉取第三方 submodule 并应用本项目 patch：

```bash
git submodule update --init --recursive
./scripts/apply_vendor_patches.sh
```

第二次执行 patch 脚本应显示 `Already applied ...`，这是正常状态：

```bash
./scripts/apply_vendor_patches.sh
```

4. 构建当前已实现的核心包：

```bash
./scripts/with_venv.sh colcon build --packages-select oakd_perception imu_fusion vins_fusion_ros2 robot_localization nav_mapping nav_planning nav_safety px4_comm_bridge nav_local uav_bringup px4_msgs
source install/setup.bash
```

如果需要 MID360 / FAST-LIO2：

```bash
./scripts/build_livox_sdk2.sh
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh colcon build \
  --packages-select livox_ros_driver2 fast_lio nav_mapping uav_bringup \
  --symlink-install
```

5. 启动对应系统：

- 启动默认导航栈：`./scripts/run_nav_stack.sh oakd`
- 启动 MID360 替代 OAK-D 点云避障：`./scripts/run_nav_stack.sh mid360`
- 启动 MID360 + FAST-LIO2 冗余里程计：`./scripts/run_nav_stack.sh mid360_lio`
- 启动纯 MID360/LIO 模式：`./scripts/run_nav_stack.sh mid360_only`

6. 打开 RViz：完整导航链路将 `Fixed Frame` 设为 `map`，再添加 `/local_map/occupancy`、`/perception/obstacle_points` 或当前点云源。

只看 OAK-D 或 MID360 单设备输出时，按 [docs/SENSOR_DEBUG_GUIDE.md](./docs/SENSOR_DEBUG_GUIDE.md) 的独立调试流程启动。

---

## 当前完成度与边界

当前仓库不是“只有感知底座”，而是已经形成了可运行的导航管线；但从算法完整性上看，它仍然处于“基础链路完成、规划策略原型化”的阶段。

已完成：

- OAK-D 统一节点与 IMU / 深度同进程采集；
- VINS-Fusion、PX4 姿态源与双级 EKF 定位链路；
- `nav_mapping`、`nav_planning`、`nav_safety`、`px4_comm_bridge`、`uav_bringup` 的基础集成；
- MID360 驱动、FAST-LIO2、Livox 点云转换、OAK-D/MID360 点云源切换和 LIO 里程计接入；
- MID360 第三方依赖的 submodule + patch 复刻流程；
- 系统级联调与单元/集成测试。

仍需补齐：

- 真机环境下 SE(2) DWA 参数整定、速度/偏航速率限幅与飞行验收；
- MID360 实机网络参数、外参、时间同步和 LIO 稳定性验收；
- 真机飞行前的完整验收；
- 更进一步的 3D 地图、ESDF 或体素导航。

详细对比见 [docs/PX4_NAVIGATION_STRATEGY.md](./docs/PX4_NAVIGATION_STRATEGY.md)。
MID360 + FAST-LIO2 接入见 [docs/MID360_FAST_LIO2_INTEGRATION.md](./docs/MID360_FAST_LIO2_INTEGRATION.md)，第三方依赖复刻流程见 [docs/SUBMODULE_PATCH_REPRODUCTION.md](./docs/SUBMODULE_PATCH_REPRODUCTION.md)。

---

## 本文档结构（目录）

- 概览
- 快速开始
- 架构说明
- 安装与构建
- 运行与启动
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
- `livox_ros_driver2`：接入 Livox MID360，发布 Livox CustomMsg 点云和 Livox IMU；
- `fast_lio`：可选激光惯性里程计，输出 `/lio/odometry` 供 EKF 融合；
- `nav_mapping`、`nav_planning`、`nav_safety`、`px4_comm_bridge`：提供局部建图、基础规划、安全监控与 PX4 数据/控制桥接；
- `uav_bringup`：统一启动编排与中央参数管理；
- 多个启动脚本与配置预设，便于在室内/户外/黑暗场景间切换。

推荐使用“一体化/统一节点”方案（在单进程中同时管理深度与 IMU），避免设备冲突（X_LINK_DEVICE_ALREADY_IN_USE）。OAK-D / MID360 单设备调试见 [docs/SENSOR_DEBUG_GUIDE.md](./docs/SENSOR_DEBUG_GUIDE.md)，架构说明见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

### 1.1 包职责与话题接口

下面汇总当前仓库主要功能包的职责，以及它们直接订阅/发布的话题。没有直接话题接口的包，说明其职责主要是启动编排、兼容层或消息定义。

| 包 | 职责 | 订阅 | 发布 |
|---|---|---|---|
| `oakd_perception` | OAK-D 图像、点云与原始 IMU 采集 | - | `/oakd/imu/raw`，`/oakd/left/image_raw`，`/oakd/right/image_raw`，`/oakd/points`，`/oakd/points_filtered` |
| `VINS-Fusion-ros2` | 双目视觉惯导里程计 | `/oakd/left/image_raw`，`/oakd/right/image_raw`，`/oakd/imu/raw` | `/vio/odometry`，`/vins/tf` |
| `robot_localization` | 双级 EKF 与 GPS 转换 | `/vio/odometry`，`/px4/attitude`，`/px4/imu`，可选 `/gps/fix`、`/lio/odometry` | `/odometry/local`，可选 `/odometry/global`、`/odometry/gps`，`/tf` |
| `imu_fusion` | OAK-D IMU 预融合/调试链路 | `/oakd/imu/raw` | `/oakd/imu/fused` |
| `livox_ros_driver2` | MID360 驱动 | - | `/livox/lidar`，`/livox/imu` |
| `fast_lio` | MID360 激光惯性里程计 | `/livox/lidar`，`/livox/imu` | `/lio/odometry`，`/lio/path` |
| `nav_mapping` | 点云转换、点云融合、局部占用栅格生成 | `/oakd/points_filtered`，`/livox/lidar`，`/mid360/points`，`/tf`，`/tf_static` | `/mid360/points`，`/perception/obstacle_points`，`/local_map/occupancy` |
| `nav_planning` | SE(2) DWA 二维局部规划与速度/偏航速率决策 | `/local_map/occupancy`，`/tf`，目标话题 | `/nav/cmd_vel` |
| `nav_safety` | 点云、TF、里程计与 PX4 状态安全监控 | `/oakd/points` 或 `/mid360/points` 或 `/perception/obstacle_points`，`/tf`，`/odometry/local` | `/nav/emergency`，`/nav/safety_status` |
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

可选 MID360：
MID360 → livox_ros_driver2 → /livox/lidar, /livox/imu
  ├─ /livox/lidar → livox_custom_to_pointcloud2 → /mid360/points
  ├─ /mid360/points 可替代或补充 /oakd/points_filtered 进入避障和局部建图
  └─ /livox/lidar + /livox/imu → FAST-LIO2 → /lio/odometry → EKF
```

TF 树：`map → odom → base_link → oakd_imu_link → oakd_camera_optical_frame`

要点：
- 将 IMU 与深度放在同一进程（统一节点）避免 USB/设备冲突；
- 双级 EKF 架构：`ekf_odom` 发布 `odom→base_link`，`ekf_map` 发布 `map→odom`（GPS 校正）；
- VINS 自身 TF 被隔离到 `/vins/tf`，主 `/tf` 只由 EKF 与静态外参发布器维护；
- PX4 姿态通过 `/px4/attitude` 单独输入 EKF，`/px4/imu` 只承担角速度与线加速度输入；
- MID360 默认关闭，可通过 `enable_mid360`、`enable_lio` 和 `obstacle_pointcloud_source` 显式启用；
- 无 GPS 模式下 `map→odom` 为静态恒等变换，局部避障照常工作；
- 详细 TF 说明见 [docs/TF_FRAMES.md](./docs/TF_FRAMES.md)。

---

## 3. 安装与构建

本节简述关键步骤。详细信息见 [**docs/INSTALLATION.md**](./docs/INSTALLATION.md)。

### 3.1 快速步骤

```bash
# 0. 克隆仓库
git clone --recurse-submodules <repo-url> uav_vision_ws
cd uav_vision_ws

# 如果不是递归克隆，补拉 submodule
git submodule update --init --recursive

# 1. 安装 uv 并创建虚拟环境
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv .venv

# 2. 安装依赖
uv pip install --python .venv/bin/python -e src/oakd_perception depthai

# 3. 拉取 submodule 并应用第三方适配 patch
git submodule update --init --recursive
./scripts/apply_vendor_patches.sh

# 4. 构建 OAK-D/PX4/VIO/导航核心包
./scripts/with_venv.sh colcon build --packages-select oakd_perception imu_fusion vins_fusion_ros2 robot_localization nav_mapping nav_planning nav_safety px4_comm_bridge nav_local uav_bringup px4_msgs

# 5. 可选：构建 MID360 / FAST-LIO2
./scripts/build_livox_sdk2.sh
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh colcon build \
  --packages-select livox_ros_driver2 fast_lio nav_mapping uav_bringup \
  --symlink-install

# 6. 激活工作区
source install/setup.bash
```

说明：MID360 相关第三方源码由 submodule 固定版本，项目适配由 `patches/vendor/*.patch` 保存。复刻和维护方法见 [docs/SUBMODULE_PATCH_REPRODUCTION.md](./docs/SUBMODULE_PATCH_REPRODUCTION.md)。

### 3.2 克隆后运行前检查

如果是新机器或重新克隆，建议在构建前执行：

```bash
git status --short
git submodule status --recursive
./scripts/apply_vendor_patches.sh
```

判断标准：

- `git submodule status --recursive` 应列出 `src/px4_msgs`、`src/livox_ros_driver2`、`src/FAST_LIO_ROS2`、`src/FAST_LIO_ROS2/include/ikd-Tree`、`third_party/Livox-SDK2`。
- `./scripts/apply_vendor_patches.sh` 首次运行应显示 `Applied ...`，再次运行应显示 `Already applied ...`。
- `git status --short` 中如果看到 `m src/livox_ros_driver2`、`m src/FAST_LIO_ROS2`、`m third_party/Livox-SDK2`，这是 patch 已应用后的正常 submodule dirty 状态。
- 如果第三方目录为空或只有少量文件，说明 submodule 没拉全，执行 `git submodule update --init --recursive`。
- 如果是 ZIP 下载得到的目录，建议删除后重新用 `git clone --recurse-submodules` 克隆。

### 3.3 完整配置指南

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

如果是首次部署或刚完成构建，请先确认这些包已经编译成功：`oakd_perception`、`imu_fusion`、`vins_fusion_ros2`、`robot_localization`、`nav_mapping`、`nav_planning`、`nav_safety`、`px4_comm_bridge`、`nav_local`、`uav_bringup`。如果启用 MID360，还需要确认 `livox_ros_driver2`、`fast_lio` 已编译成功，且 `.deps/livox_sdk2` 已由 `scripts/build_livox_sdk2.sh` 生成。

推荐的调度关系由 `uav_bringup/launch/nav_stack.launch.py` 统一编排：

1. `oakd_perception`：启动 OAK-D 统一节点，发布图像、IMU 和点云；
2. `imu_fusion`：启动 OAK-D IMU 预融合节点，作为调试/备用输出；
3. `VINS-Fusion-ros2`：消费 OAK-D 双目图像与 IMU，发布 `/vio/odometry`；
4. `uav_bringup/ekf_launch.py`：启动 `robot_localization`，融合 VIO、PX4 姿态、PX4 IMU 和可选 GPS；
5. `nav_mapping` / `nav_planning` / `nav_safety`：使用主 TF、点云和定位输出完成建图、规划和安全监控；
6. `px4_comm_bridge`：接收 `/nav/cmd_vel` 与安全状态，输出 PX4 offboard 控制，同时发布 PX4 数据源。
7. 可选 `livox_ros_driver2` / `fast_lio`：启用 MID360 点云和 LIO 冗余里程计。

如果只调试 OAK-D 或 MID360 传感器，不需要启动完整导航栈，请看 [docs/SENSOR_DEBUG_GUIDE.md](./docs/SENSOR_DEBUG_GUIDE.md)。

### 4.1 导航栈

导航栈推荐通过脚本启动，减少手写 launch 参数：

```bash
./scripts/run_nav_stack.sh oakd         # 默认 OAK-D + VINS
./scripts/run_nav_stack.sh gps          # OAK-D + VINS + GPS
./scripts/run_nav_stack.sh mid360       # MID360 替代 OAK-D 点云
./scripts/run_nav_stack.sh both         # OAK-D + MID360 点云融合
./scripts/run_nav_stack.sh mid360_lio   # OAK-D + MID360 + FAST-LIO2
./scripts/run_nav_stack.sh mid360_only  # 关闭 OAK-D/VINS，仅用 MID360 + FAST-LIO2
```

脚本后面可以继续追加 launch 参数，例如：

```bash
./scripts/run_nav_stack.sh mid360 mid360_x:=0.08 mid360_z:=0.05
```

也可以直接使用底层 launch 入口。`nav_stack.launch.py` 文件顶部的 `LAUNCH_DEFAULTS` 集中维护常用默认值：

```bash
# 无 GPS 模式（默认）
ros2 launch uav_bringup nav_stack.launch.py

# GPS 模式
ros2 launch uav_bringup nav_stack.launch.py enable_gps:=true

# MID360 替代 OAK-D 点云做避障和局部建图
ros2 launch uav_bringup nav_stack.launch.py \
  enable_mid360:=true \
  obstacle_pointcloud_source:=mid360

# OAK-D + MID360 点云融合做避障和局部建图
ros2 launch uav_bringup nav_stack.launch.py \
  enable_mid360:=true \
  obstacle_pointcloud_source:=both

# MID360 + FAST-LIO2 冗余里程计
ros2 launch uav_bringup nav_stack.launch.py \
  enable_mid360:=true \
  enable_lio:=true \
  obstacle_pointcloud_source:=both

# 纯 MID360/LIO 模式：关闭 OAK-D 感知、OAK-D IMU 融合和 VINS
ros2 launch uav_bringup nav_stack.launch.py \
  enable_oakd_perception:=false \
  enable_imu_fusion:=false \
  enable_vins:=false \
  enable_mid360:=true \
  enable_lio:=true \
  obstacle_pointcloud_source:=mid360
```

启动后的预期行为：

- `ekf_filter_node_odom` 融合 VIO + PX4 姿态 + PX4 IMU，发布 `odom→base_link` TF 和 `/odometry/local`；
- `px4_comm_bridge` 发布 `/px4/attitude`、`/px4/imu`、`/gps/fix`，其中姿态与 IMU 在 EKF 中分开融合；
- GPS 模式下 `ekf_filter_node_map` 额外融合 GPS，发布 `map→odom` TF 和 `/odometry/global`；
- `local_map_builder` 订阅 `/oakd/points_filtered`，通过 TF 投影生成 `/local_map/occupancy`；
- 启用 MID360 时，`local_map_builder` 和 `safety_monitor` 可改用 `/mid360/points` 或 `/perception/obstacle_points`；
- 启用 FAST-LIO2 时，FAST-LIO2 消费 `/livox/lidar` 和 `/livox/imu`，输出 `/lio/odometry`，EKF 第一版只融合 LIO 位置和速度；
- 关闭 OAK-D 时，应同时设置 `enable_oakd_perception:=false enable_imu_fusion:=false enable_vins:=false`，并把 `obstacle_pointcloud_source` 改为 `mid360`；
- `se2_dwa_local_planner` 消费局部栅格、目标与 TF，发布 `/nav/cmd_vel`，其中 `linear.x/y` 为 ENU 平面速度，`angular.z` 为 ENU yaw rate；
- `safety_monitor` 订阅 `/oakd/points` 并发布 `/nav/emergency`；
- `px4_comm_bridge` 桥接到 PX4，不可用时降级运行。

注意：旧 `local_planner` 仍保留为兼容/回退入口；统一导航栈默认使用 `se2_dwa_local_planner`。
MID360 网络、外参与排查步骤见 [docs/MID360_FAST_LIO2_INTEGRATION.md](./docs/MID360_FAST_LIO2_INTEGRATION.md)。

### 4.2 一键验证顺序

如果你想按最少步骤确认整个仓库的启动链路，建议使用下面这个顺序：

```bash
cd /home/nuc/Program/uav_vision_ws
source .venv/bin/activate
source install/setup.bash

# 导航栈
./scripts/run_nav_stack.sh oakd
```

检查点：

- `/oakd/imu/raw` 是否存在；
- `/vio/odometry` 是否在相机运动后输出；
- `/px4/attitude` 与 `/px4/imu` 是否存在，PX4 未连接时可先跳过；
- `/oakd/points`、`/oakd/points_filtered` 是否持续发布；
- 若启用 MID360，`/livox/lidar`、`/livox/imu`、`/mid360/points` 是否持续发布；
- 若启用 FAST-LIO2，`/lio/odometry` 是否稳定输出；
- `/odometry/local` 和 `map -> odom -> base_link` 是否正常；
- `/local_map/occupancy`、`/nav/cmd_vel`、`/nav/emergency` 是否正常；
- 若使用 PX4，再检查 `/fmu/in/*` 是否有消息。

如需单独确认 OAK-D 图像/点云/IMU、MID360 `/livox/lidar`、`/mid360/points`、FAST-LIO2 `/lio/odometry` 或 ros2 bag 录制，请使用 [docs/SENSOR_DEBUG_GUIDE.md](./docs/SENSOR_DEBUG_GUIDE.md)。

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

### 5.4 MID360 / LIO 关键参数

`uav_bringup/launch/nav_stack.launch.py` 提供以下参数：

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `enable_oakd_perception` | `true` | 是否启动 OAK-D 感知 pipeline |
| `enable_imu_fusion` | `true` | 是否启动 OAK-D IMU 预融合/调试 pipeline |
| `enable_vins` | `true` | 是否启动 OAK-D stereo VINS-Fusion VIO |
| `enable_mid360` | `false` | 是否启动 MID360 驱动和点云转换 |
| `enable_lio` | `false` | 是否启动 FAST-LIO2 并把 `/lio/odometry` 接入 EKF |
| `obstacle_pointcloud_source` | `oakd` | 避障点云源：`oakd`、`mid360`、`both` |
| `mid360_custom_topic` | `/livox/lidar` | Livox CustomMsg 输入 |
| `mid360_pointcloud_topic` | `/mid360/points` | MID360 转换后的 PointCloud2 |
| `combined_pointcloud_topic` | `/perception/obstacle_points` | `both` 模式下的融合点云 |
| `lio_odom_topic` | `/lio/odometry` | FAST-LIO2 输出里程计 |

MID360 驱动网络配置位于：

```text
src/livox_ros_driver2/config/MID360_config.json
```

需要根据机载电脑有线网口 IP 和 MID360 设备 IP 修改 `host_net_info` 与 `lidar_configs`。详细步骤见 [docs/MID360_FAST_LIO2_INTEGRATION.md](./docs/MID360_FAST_LIO2_INTEGRATION.md)。

---

## 6. 可视化（RViz）

```bash
./scripts/with_venv.sh rviz2
```

完整导航链路建议将 `Fixed Frame` 设为 `map`，并添加 `TF`、`/local_map/occupancy`、`/nav/cmd_vel`、`/nav/emergency`、当前避障点云源。OAK-D 或 MID360 单独观察的 RViz frame 与点云话题见 [docs/SENSOR_DEBUG_GUIDE.md](./docs/SENSOR_DEBUG_GUIDE.md)。

---

## 7. 测试与验证

### 7.1 在线系统检查

```bash
source install/setup.bash
./scripts/run_nav_stack.sh oakd
./scripts/with_venv.sh ros2 topic list | grep -E "/vio/odometry|/px4/attitude|/px4/imu|/odometry/local"
./scripts/with_venv.sh ros2 topic list | grep -E "/local_map/occupancy|/nav/cmd_vel|/nav/emergency|/fmu/in/"
./scripts/with_venv.sh ros2 topic hz /vio/odometry
./scripts/with_venv.sh ros2 topic hz /odometry/local
./scripts/with_venv.sh ros2 topic hz /nav/cmd_vel
./scripts/with_venv.sh ros2 topic hz /nav/emergency
```

### 7.2 录制与离线回放（ros2 bag）

```bash
./scripts/with_venv.sh ros2 bag record -o nav_test /vio/odometry /odometry/local /local_map/occupancy /nav/cmd_vel /nav/emergency /tf /tf_static
./scripts/with_venv.sh ros2 bag play nav_test
```

OAK-D / MID360 专项 bag 录制列表见 [docs/SENSOR_DEBUG_GUIDE.md](./docs/SENSOR_DEBUG_GUIDE.md)。

### 7.3 常用调试命令

```bash
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
- 导航栈持续发布零速度：检查 `/local_map/occupancy` 是否超时、`map→base_link` TF 是否存在，以及 `/nav/emergency` 是否为 true。
- VS Code Git 显示 `src/livox_ros_driver2` 等子仓库有改动：这是 vendor patch 已应用后的正常 submodule dirty 状态，父仓库通过 `patches/vendor/*.patch` 管理这些改动。

OAK-D 设备占用、DepthAI、点云显示、MID360 网络、`/mid360/points`、FAST-LIO2 `/lio/odometry` 等传感器专项问题见 [docs/SENSOR_DEBUG_GUIDE.md](./docs/SENSOR_DEBUG_GUIDE.md)。

---

## 10. 项目文件结构

```
uav_vision_ws/
├── src/oakd_perception/                  # OAK-D 统一节点（IMU + 深度 + 点云）
├── src/imu_fusion/                       # OAK-D IMU 预融合/调试链路
├── src/VINS-Fusion-ros2/                 # 双目视觉惯导里程计（VIO）
├── src/robot_localization/               # 双级 EKF 状态融合
├── src/livox_ros_driver2/                # MID360 驱动（submodule + vendor patch）
├── src/FAST_LIO_ROS2/                    # FAST-LIO2 ROS2 版本（submodule + vendor patch）
├── src/nav_mapping/                      # 点云到局部占用栅格
├── src/nav_planning/                     # 基础局部规划策略
├── src/nav_safety/                       # 安全监控与紧急信号
├── src/px4_comm_bridge/                  # PX4 数据/控制桥接（姿态 + IMU + GPS + 控制）
├── src/uav_bringup/                      # 导航栈启动编排
│   ├── launch/ekf_launch.py             #   双级 EKF + GPS 开关 + 静态外参
│   ├── launch/nav_stack.launch.py       #   完整导航栈入口
│   └── config/dual_ekf.yaml             #   EKF + NavSat 配置
├── src/px4_msgs/                         # PX4 消息定义（可选依赖）
├── third_party/Livox-SDK2/               # Livox SDK2（submodule + vendor patch）
├── patches/vendor/                       # 第三方 submodule 本项目适配补丁
├── scripts/                              # 快速启动脚本与工具
│   ├── run_nav_stack.sh                  #   导航栈模式化启动入口
│   ├── apply_vendor_patches.sh           #   应用第三方 patch
│   └── build_livox_sdk2.sh               #   构建 Livox-SDK2 到 .deps/
├── docs/                                 # 文档
│   ├── TF_FRAMES.md                     #   TF 坐标变换系统说明
│   ├── ARCHITECTURE.md                  #   系统架构设计
│   ├── MID360_FAST_LIO2_INTEGRATION.md  #   MID360 + FAST-LIO2 接入
│   ├── SENSOR_DEBUG_GUIDE.md            #   OAK-D / MID360 独立调试
│   ├── SUBMODULE_PATCH_REPRODUCTION.md  #   submodule + patch 复刻流程
│   └── ...
└── README.md
```

---

## 附录：配置文件位置

`src/oakd_perception/config/` 包含预设 YAML，可直接修改或拷贝为自定义配置并在脚本/launch 中引用。

---
