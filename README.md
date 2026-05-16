# uav_vision_ws（统一使用 .venv）

本仓库提供针对 OAK‑D 相机的深度点云与 IMU 采集、融合与可视化工具集，全部以项目虚拟环境 `.venv` 运行为约定。本文档已重构为更清晰的结构：快速上手 → 架构概览 → 安装/构建 → 运行/调试 → 配置/参数 → 可视化 → 测试/回放 → 坐标系/TF → 故障排查 → 项目结构。

## 当前状态

当前仓库的状态是“开发/仿真可用，硬件验收待补齐”：

- OAK-D 统一节点、IMU 融合、TF 广播、局部建图、安全监控、PX4 桥接与启动编排已实现，并通过系统级验证；
- 导航栈已经形成点云 → 占用栅格 → `/nav/cmd_vel` → 安全监控 → PX4 桥接的完整管道；
- `local_planner` 仍是基础前向速度策略，不是障碍物感知的成熟局部规划器；
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
./scripts/with_venv.sh colcon build --packages-select oakd_perception imu_fusion nav_mapping nav_planning nav_safety nav_px4_bridge nav_local uav_bringup px4_msgs
source install/setup.bash
```

3. 启动对应系统：

- 仅看 OAK-D 感知与 IMU 联动：`./scripts/run_complete_system.sh`
- 启动导航栈：`ros2 launch uav_bringup nav_stack.launch.py`

4. 打开 RViz：按脚本提示将 `Fixed Frame` 设为 `map`，再添加 `/oakd/points` 或 `/local_map/occupancy` 显示。

---

## 当前完成度与边界

当前仓库不是“只有感知底座”，而是已经形成了可运行的导航管线；但从算法完整性上看，它仍然处于“基础链路完成、规划策略原型化”的阶段。

已完成：

- OAK-D 统一节点与 IMU / 深度同进程采集；
- `imu_fusion` 与 TF 广播链路；
- `nav_mapping`、`nav_planning`、`nav_safety`、`nav_px4_bridge`、`uav_bringup` 的基础集成；
- 系统级联调与单元/集成测试。

仍需补齐：

- 基于障碍物的真正局部规划器，例如 DWA / DWB；
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
  - IMU 融合链路
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
- `imu_fusion`：接收原始 IMU，输出融合后的姿态并广播 TF；
- `nav_mapping`、`nav_planning`、`nav_safety`、`nav_px4_bridge`：提供局部建图、基础规划、安全监控与 PX4 桥接；
- `uav_bringup`：统一启动编排与中央参数管理；
- 多个启动脚本与配置预设，便于在室内/户外/黑暗场景间切换。

推荐使用“一体化/统一节点”方案（在单进程中同时管理深度与 IMU），避免设备冲突（X_LINK_DEVICE_ALREADY_IN_USE）。详见后文“统一节点”节与 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

---

## 2. 架构说明

简要架构（逻辑视图）：

```
单一 OAK-D 设备
      ↓
  DAI Pipeline (单进程)
   ├─ IMU 采样 → /oakd/imu/raw  (400Hz)
   └─ 深度处理 → /oakd/points    (~20Hz)

上游：/oakd/imu/raw -> imu_fusion -> /imu (融合) -> imu_tf_broadcaster -> TF(map -> oakd_imu_link)

导航链路：/oakd/points_filtered -> /local_map/occupancy -> /nav/cmd_vel -> /nav/emergency -> PX4
```

要点：
- 将 IMU 与深度放在同一进程（统一节点）避免 USB/设备冲突；
- `imu_fusion` 负责从原始 IMU 出来姿态估计并广播 `map -> oakd_imu_link`；
- RViz 的 `Fixed Frame` 决定点云是否随 IMU 姿态旋转（`map` 时会跟随 TF）。
- 导航栈已经打通数据流，但 `local_planner` 仍是基础前向速度策略，尚未达到成熟避障规划器的算法完整度。

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
./scripts/with_venv.sh colcon build --packages-select oakd_perception imu_fusion nav_mapping nav_planning nav_safety nav_px4_bridge nav_local uav_bringup px4_msgs

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

如果是首次部署或刚完成构建，请先确认这些包已经编译成功：`oakd_perception`、`imu_fusion`、`nav_mapping`、`nav_planning`、`nav_safety`、`nav_px4_bridge`、`nav_local`、`uav_bringup`。

推荐的启动顺序是：

1. 先启动 OAK-D 统一节点，确保 `/oakd/imu/raw` 和 `/oakd/points` 正常发布；
2. 再启动 `imu_fusion`，确认 `/imu` 和 `map -> oakd_imu_link` 正常；
3. 最后启动导航栈，检查 `/local_map/occupancy`、`/nav/cmd_vel`、`/nav/emergency`。

如果你只想快速看完整联动，直接使用 `./scripts/run_complete_system.sh` 即可。

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
chmod +x scripts/run_complete_system.sh
./scripts/run_complete_system.sh

# 仅启动 OAK-D 统一节点
./scripts/run_oakd_unified.sh
```

统一节点常用参数示例：

```bash
./scripts/with_venv.sh ros2 launch oakd_perception oakd_unified.launch.py \
  enable_passive_stereo:=true enable_active_stereo:=true ir_intensity:=1000 pointcloud_frequency:=30
```

统一节点发布的主题（常见）：

- `/oakd/imu/raw` — 原始 IMU（Imu）约 400Hz
- `/oakd/points` — 深度点云（PointCloud2）约 20Hz

### 4.4 IMU 融合链路（上层）

建议架构：

- 统一节点发布 `/oakd/imu/raw`（原始 IMU）；
- `imu_fusion` 订阅原始 IMU，输出融合后 `/imu`（含 orientation），并由 `imu_tf_broadcaster` 广播 `map -> oakd_imu_link`。

手动启动链路示例：

```bash
# 统一节点（IMU+深度）
./scripts/run_oakd_unified.sh

# IMU 融合与 TF 广播
./scripts/run_imu_fusion_tf.sh
```

建议在两个终端中运行时遵循以下顺序：

1. 终端 A：先运行 `./scripts/run_oakd_unified.sh`；
2. 终端 B：再运行 `./scripts/run_imu_fusion_tf.sh`；
3. 等待 `map -> oakd_imu_link` 可见后，再打开 RViz 观察 `/oakd/points`。

### 4.5 导航栈（已实现，基础策略）

导航栈已经可通过统一入口启动，并完成以下链路：点云输入 → 局部占用栅格 → 速度命令 → 安全监控 → PX4 桥接。

启动示例：

```bash
source install/setup.bash
ros2 launch uav_bringup nav_stack.launch.py
```

启动后的预期行为：

- `local_map_builder` 订阅 `/oakd/points_filtered`，发布 `/local_map/occupancy`；
- `local_planner` 消费局部栅格并持续发布 `/nav/cmd_vel`；
- `safety_monitor` 订阅 `/oakd/points` 并发布 `/nav/emergency`；
- `px4_offboard_ctrl` 订阅速度与安全信号，并在 PX4 可用时发布 `fmu/in/*` 消息。

如果你在本机没有 PX4 消息依赖，`px4_offboard_ctrl` 会进入降级模式，这是预期行为。

当前导航栈节点：

- `/local_map_builder` — 点云投影与占用栅格生成
- `/local_planner` — 基础前向速度策略
- `/safety_monitor` — 点云超时与点密度监测
- `/px4_offboard_ctrl` — PX4 Offboard 桥接与看门狗

注意：这条链路已验证可用，但 `local_planner` 仍是原型级策略，后续应替换为真正的障碍物感知局部规划器。

### 4.6 一键验证顺序

如果你想按最少步骤确认整个仓库的启动链路，建议使用下面这个顺序：

```bash
cd /home/nuc/Program/uav_vision_ws
source .venv/bin/activate
source install/setup.bash

# 1. OAK-D 感知与 IMU
./scripts/run_complete_system.sh

# 2. 导航栈（另一个终端）
ros2 launch uav_bringup nav_stack.launch.py
```

检查点：

- `/oakd/imu/raw` 是否存在；
- `/imu` 是否存在且 TF 树可见；
- `/oakd/points`、`/oakd/points_filtered` 是否持续发布；
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

- `Fixed Frame`：`oakd_link`（仅点云）或 `map`（若启用 IMU 联动）；
- 添加 `PointCloud2`，选择 `/oakd/points`；
- 调整 `Style`、`Size`（0.01–0.05m）、`Color Transformer`（Intensity/RGB/FlatColor）。

### 6.2 若要点云随 IMU 姿态旋转

- 确保 `imu_fusion` 正常发布 `/imu` 并广播 `map -> oakd_imu_link`；
- 将 RViz `Fixed Frame` 设为 `map`；
- 添加 `TF` 显示以验证 frame 关系。

---

## 7. 测试与验证

### 7.1 在线系统检查

```bash
./scripts/run_complete_system.sh
source install/setup.bash
ros2 launch uav_bringup nav_stack.launch.py
./scripts/with_venv.sh ros2 topic list | grep -E "/oakd/points|/oakd/imu|/imu"
./scripts/with_venv.sh ros2 topic list | grep -E "/local_map/occupancy|/nav/cmd_vel|/nav/emergency|/fmu/in/"
./scripts/with_venv.sh ros2 topic hz /oakd/points
./scripts/with_venv.sh ros2 topic hz /imu
./scripts/with_venv.sh ros2 topic hz /nav/cmd_vel
./scripts/with_venv.sh ros2 topic hz /nav/emergency
```

### 7.2 录制与离线回放（ros2 bag）

```bash
./scripts/with_venv.sh ros2 bag record -o test_run /oakd/points /imu
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

常用 frame：

- `oakd_link`：深度点云发布时的相机机体坐标系；
- `oakd_imu_link`：IMU 原始数据和融合 TF 链中的默认 frame；
- `map`：全局世界坐标系（由上层定位或 `imu_fusion` 提供）。
- `camera_depth_optical_frame`：`nav_mapping` 中默认使用的点云源帧之一，具体取决于启动配置。

注意：ROS 中位置单位为米（m），但节点参数中 `min_depth`/`max_depth` 以毫米（mm）表示（换算 1m = 1000mm）。

检查 TF：

```bash
./scripts/with_venv.sh ros2 run tf2_tools view_frames
./scripts/with_venv.sh ros2 run tf2_ros tf2_echo map oakd_imu_link
```

在代码中查询变换（示例）：

```python
from tf2_ros import Buffer, TransformListener
import rclpy

node = rclpy.create_node('tf_query')
tf_buffer = Buffer()
tf_listener = TransformListener(tf_buffer, node)

try:
    trans = tf_buffer.lookup_transform('map', 'oakd_imu_link', rclpy.time.Time())
except Exception as e:
  node.get_logger().warn(f"TF lookup failed: {e}")
```

静态安装偏差：使用 `static_transform_publisher` 或在 launch 中设置静态变换进行校正。

---

## 9. 故障排查

- 常见问题：ModuleNotFoundError: depthai → 确认 `.venv` 中安装 depthai（见第 3 节）。
- 设备冲突：优先使用统一节点或确保仅有一个进程访问设备。可用 `pkill` 停止冗余进程。
- RViz 不显示点云：检查话题 `/oakd/points`、Fixed Frame 与 TF 链路。
- 导航栈只会持续发布前向速度：这是当前 `local_planner` 的设计边界，不是故障。

常用排查命令见第 7 节。

---

## 10. 项目文件结构

```
uav_vision_ws/
├── src/oakd_perception/
│   ├── oakd_perception/
│   │   ├── oakd_depth_node.py           # 点云发布节点主文件
│   │   └── oakd_imu_node.py             # IMU 6轴传感器节点
│   ├── config/                          # 预设配置文件
│   │   ├── outdoor_low_power.yaml
│   │   ├── indoor_high_precision.yaml
│   │   ├── balanced_mode.yaml
│   │   └── active_stereo_max.yaml
│   ├── setup.py
│   └── package.xml
├── src/nav_mapping/                      # 点云到局部占用栅格
├── src/nav_planning/                     # 基础局部规划策略
├── src/nav_safety/                       # 安全监控与紧急信号
├── src/nav_px4_bridge/                   # PX4 Offboard 桥接
├── src/nav_local/                        # 向后兼容层
├── src/uav_bringup/                      # 导航栈启动编排
├── scripts/                             # 快速启动脚本与工具
│   ├── with_venv.sh
│   ├── run_complete_system.sh
│   ├── run_imu_fusion_tf.sh
│   ├── run_oakd_outdoor.sh
│   ├── run_oakd_indoor.sh
│   ├── run_oakd_balance.sh
│   ├── run_oakd_active_max.sh
│   └── run_oakd_unified.sh
├── docs/                                # 架构、安装、验证与快速参考
└── README.md
```

---

## 附录：配置文件位置

`src/oakd_perception/config/` 包含预设 YAML，可直接修改或拷贝为自定义配置并在脚本/launch 中引用。

---

