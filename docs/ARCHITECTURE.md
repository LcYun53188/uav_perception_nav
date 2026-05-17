# 系统架构设计

本文档描述 OAK-D 统一节点的架构设计、解决的问题、核心组件与数据流。

---

## 问题背景

之前的架构使用两个独立进程访问同一 OAK-D 设备：

- `oakd_imu_node`：IMU 数据采集（400Hz）
- `oakd_depth_node`：深度数据采集（20Hz）

**问题**：两个进程无法同时访问 OAK-D 设备，导致设备被占用错误：

```
RuntimeError: Cannot connect to device with name "4.1", it is used by another process.
Error: X_LINK_DEVICE_ALREADY_IN_USE
```

---

## 解决方案：统一节点架构

### 核心思想

创建 `oakd_unified_node`，在单一进程中同时处理 IMU 与深度数据流，确保对 OAK-D 设备的排他性访问。

### 逻辑架构图

```
┌─────────────────────────────────────┐
│     OAK-D 物理设备                   │
│     (单一硬件连接)                   │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │ DAI Pipeline │
        │  (单进程)    │
        └──────┬──────┘
               │
        ┌──────┴──────────┬──────────────┐
        │                 │              │
    ┌───▼────┐      ┌────▼────┐   ┌────▼────┐
    │  IMU   │      │  Depth  │   │  RGB    │
    │ Sensor │      │ Camera  │   │ Camera  │
    │(400Hz) │      │ (30fps) │   │         │
    └───┬────┘      └────┬────┘   └─────────┘
        │                │
        │ /oakd/imu/raw  │ /oakd/points
      ┌──────▼─────────────┐
      │  imu_fusion_node   │ (融合 + TF 广播)
      ├────────────────────┤
           │
        ┌──┴──┐────────────┐
        │     │            │
   /imu │/tf  │ map→oakd_imu_link│
(100Hz) │     │    (动态)   │
        │     │            │
            │ /oakd/imu/raw  │ /oakd/points
            │                │ /oakd/points_filtered
        └─────┴────────────┘
     发布 `/oakd/imu/raw`、`/oakd/points` 与 `/oakd/points_filtered`。

### 架构对比

| 特性 | 旧架构 | 新架构 |
|------|--------|---------|
| 设备连接数 | 2（冲突） | 1（✓ 无冲突） |
| IMU 频率 | 400Hz | 400Hz |
| 点云频率 | 20Hz | 20Hz |
| 进程数 | 2 | 1 |
| 资源占用 | 类似 | 类似 |
| 时钟同步 | 困难 | 统一时钟 |

---

## 核心组件

### 1. oakd_unified_node

**职责**：

- 创建单一 DAI Pipeline 实例；
- 同时管理 IMU 与深度模块；
- 发布 `/oakd/imu/raw`、`/oakd/points` 与 `/oakd/points_filtered`。

**关键特性**：
- 单进程设计，避免设备冲突；
- 可配置的发布频率与参数；
- 集成立体深度模式（被动/主动）。

**发布主题**：

```
/oakd/imu/raw     (sensor_msgs/Imu, 400Hz)
/oakd/points      (sensor_msgs/PointCloud2, 20Hz, raw)
/oakd/points_filtered (sensor_msgs/PointCloud2, 20Hz, filtered)
```

### 2. imu_fusion_node

**职责**：

- 订阅原始 IMU（`/oakd/imu/raw`）；
- 执行姿态融合（EKF）；
- 发布融合后的 IMU（`/imu`）。

**发布主题**：

```
/imu              (sensor_msgs/Imu, 100Hz)
                  含 orientation 四元数
```

### 3. TF 坐标变换

TF 变换由 EKF 节点和静态变换发布器共同负责：

```
map → odom → base_link → oakd_imu_link → oakd_camera_optical_frame
```

详细说明见 [TF_FRAMES.md](./TF_FRAMES.md)。

---

## 数据流

### 启动流程

```
1. 启动 oakd_unified_node
   ├── 初始化 OAK-D SDK
   ├── 配置 IMU 采样（400Hz）
   └── 开始发布数据

2. 启动 imu_fusion
   ├── 订阅 /oakd/imu/raw
   └── 发布融合后 /imu

3. 启动 EKF 节点
   ├── 融合 VIO + IMU
   └── 发布 odom → base_link (TF)

4. 启动 RViz（可视化）
   ├── 订阅 /oakd/points_filtered
   ├── 订阅 /tf
   └── 显示点云与 TF 树
```

### 消息频率

```
/oakd/imu/raw  ────► imu_fusion_node ────► /imu
 (400Hz)            (融合频率 100Hz)      (100Hz)
                                    ↓
                          imu_tf_broadcaster
                                    ↓
                                   /tf
                                 (动态)

/oakd/points_filtered ───► RViz
  (20Hz)             (订阅与显示)
```

---

## 关键参数

### IMU 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `imu_frequency` | int | 400 | 采样频率（Hz） |
| `imu_topic_name` | str | /oakd/imu/raw | 发布主题 |

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `sampling_step` | int | 2 | 下采样步长 |
| `max_depth` | int | 5000 | 最大深度（mm） |
| `pointcloud_frequency` | int | 20 | 点云频率（Hz） |


### TF 坐标系架构（v2.0）

```
map → odom → base_link → oakd_imu_link → oakd_camera_optical_frame
                 │
                 └→ gps_link
```

- **map**：全局固定参考系（ENU 东北天）
- **odom**：里程计累计参考系
- **base_link**：无人机机身中心（飞控 FCU 质心）
- **oakd_imu_link**：OAK-D 相机 IMU 中心
- **oakd_camera_optical_frame**：相机光学中心，点云参考帧

详见 [TF_FRAMES.md](./TF_FRAMES.md)。

---

## 启动方式

### 方式 1：完整启动脚本

```bash
./scripts/run_complete_system.sh
```

### 方式 2：逐步手动启动

```bash
# 终端 1: OAK-D 统一节点
./scripts/run_oakd_unified.sh

# 终端 2: IMU 融合 + TF 广播
./scripts/run_imu_fusion_tf.sh

# 终端 3: RViz 可视化
./scripts/with_venv.sh rviz2
```

### 方式 3：直接运行节点

```bash
# 仅统一节点（不含融合）
./scripts/run_oakd_unified.sh
```

## 使用方式：提前建图 vs 不提前建图

当前仓库的导航栈以 `nav_mapping` 的实时点云建图为核心，默认工作方式是“在线生成局部占用栅格”，且默认订阅 `/oakd/points_filtered`。

### 1. 提前建图

适用场景：

- 环境相对固定，例如重复巡检、实验室、仿真场景；
- 希望在执行前先把感知、TF、建图链路全部验证完；
- 需要先确认地图稳定性，再进入规划与控制测试。

使用方式：

1. 先在地面或仿真环境中启动完整系统，确认 `/oakd/points_filtered`、`/local_map/occupancy`、`/nav/cmd_vel` 全部正常，同时可对照 `/oakd/points`；
2. 通过 `ros2 topic echo /local_map/occupancy` 和 `ros2 topic hz /local_map/occupancy` 检查地图是否稳定；
3. 确认 TF 树完整，尤其是 `camera_depth_optical_frame → map` 这条链路；
4. 再进入规划和执行验证。

说明：

- 这套流程的重点是“先验证地图生成能力，再投入使用”；
- 目前仓库没有独立的离线地图加载器，所以这里的“提前建图”不是指把地图文件预先导入系统，而是指在任务开始前先把建图链路跑稳。

### 2. 不提前建图

适用场景：

- 环境未知，需要边飞边感知；
- 临时验证硬件链路；
- 更关注系统是否能实时响应当前点云。

使用方式：

1. 直接启动 `ros2 launch uav_bringup nav_stack.launch.py`；
2. 由 OAK-D 实时发布 `/oakd/points` 与 `/oakd/points_filtered`；
3. `nav_mapping` 默认订阅 `/oakd/points_filtered`，在线生成 `/local_map/occupancy`；
4. `nav_planning` 基于当前局部地图输出 `/nav/cmd_vel`；
5. `nav_safety` 持续监视点云异常并在必要时发布 `/nav/emergency`。

说明：

- 这是当前仓库的默认工作模式；
- 优点是启动简单、依赖少；
- 代价是规划质量完全依赖实时点云质量、TF 完整性和地图更新频率。

### 3. 选择建议

- 如果你要做“上线前验收”，优先用“提前建图”流程，先把地图和 TF 链路稳定下来；
- 如果你要做“未知环境验证”，直接用“不提前建图”流程，重点看实时响应和安全降级；
- 如果你要看规划是否真的有效，不要只看 `/nav/cmd_vel` 有没有输出，还要看障碍变化时输出是否发生变化。

### 4. 现场操作清单

#### 提前建图模式

1. 启动感知与融合：确认 `/oakd/imu/raw`、`/oakd/points_filtered` 和 `/tf` 正常，同时保留 `/oakd/points` 供调试使用。
2. 启动导航栈：运行 `ros2 launch uav_bringup nav_stack.launch.py`。
3. 检查地图：确认 `/local_map/occupancy` 持续更新，且 `frame_id` 为 `map`。
4. 检查规划：确认 `/nav/cmd_vel` 有输出，并在障碍靠近时会变化。
5. 检查安全：模拟点云中断或点数异常，确认 `/nav/emergency` 会触发。

#### 不提前建图模式

1. 直接启动整栈，不额外加载地图文件。
2. 保持 OAK-D 在线发布点云，让 `nav_mapping` 基于 `/oakd/points_filtered` 实时生成局部地图。
3. 观察规划输出是否随当前环境变化，而不是固定前向速度。
4. 在环境变化、点云短暂中断或 TF 缺失时，确认系统进入安全降级。
5. 如果需要复现实验，优先记录 `/oakd/points_filtered`、`/oakd/points`、`/local_map/occupancy`、`/nav/cmd_vel` 和 `/nav/emergency` 的数据流。

---

## 高级用法

### 自定义参数启动

```bash
./scripts/with_venv.sh ros2 launch oakd_perception oakd_unified.launch.py \
  enable_active_stereo:=true \
  ir_intensity:=1200 \
  pointcloud_frequency:=30 \
  min_depth:=100 \
  max_depth:=8000
```

### 修改 ROS 2 参数（运行时）

```bash
./scripts/with_venv.sh ros2 param set /oakd_unified_node enable_passive_stereo true
./scripts/with_venv.sh ros2 param set /oakd_unified_node ir_intensity 800
```

### 查看当前参数

```bash
./scripts/with_venv.sh ros2 param list /oakd_unified_node
```

---

## 故障排查

### 设备冲突

```
Error: X_LINK_DEVICE_ALREADY_IN_USE
```

**解决**：确保仅有一个 `oakd_unified_node` 实例在运行；停止其他占用设备的进程。

### 深度无输出

- 检查 `/oakd/points_filtered` 话题频率：`ros2 topic hz /oakd/points_filtered`
- 调整深度范围：`min_depth`、`max_depth`
- 尝试启用主动立体：`enable_active_stereo:=true`

### IMU 数据异常

- 检查 IMU 原始数据：`ros2 topic echo /oakd/imu/raw`
- 重启 IMU 融合节点
- 查看融合参数配置

---

## 参考资源

- [TF_FRAMES.md](./TF_FRAMES.md) — TF 坐标变换系统说明
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — 快速命令参考
- [INSTALLATION.md](./INSTALLATION.md) — 安装与构建
- [../README.md](../README.md) — 主文档
- [DepthAI 官方文档](https://docs.luxonis.com/)
- [ROS 2 官方文档](https://docs.ros.org/en/humble/)


- **v1.0** (2026-05)：统一节点架构首次实现，解决设备冲突问题。
# 导航栈架构设计（v2.0）


## 概述

导航栈从单个 `nav_local` 功能包拆分为 6 个专职功能包，遵循单一职责原则，提高模块独立性、可测试性和可维护性。

## 函数包体系

```
src/
├── nav_mapping/        # 新: PointCloud2 → OccupancyGrid
│   └── local_map_builder.py (170 行)
│       - 订阅: /oakd/points_filtered, /tf
│       - 发布: /local_map/occupancy
│       - TF 变换启用 (camera_depth_optical_frame → map)
│
├── nav_planning/       # 新: OccupancyGrid → velocity commands
│   └── local_planner.py (80 行)
│       - 订阅: /local_map/occupancy
│       - 发布: /nav/cmd_vel
│       - 规则: 中心自由则前进
│
├── nav_safety/         # 新: PointCloud2 → emergency signal
│   └── safety_monitor.py (90 行)
│       - 订阅: /oakd/points
│       - 发布: /nav/emergency
│       - 监视: 点数阈值故障检测
│
├── px4_comm_bridge/     # 新: velocity + emergency → PX4 msgs
│   └── px4_bridge_node.py (170 行)
│       - 订阅: /nav/cmd_vel, /nav/emergency
│       - 发布: /fmu/in/* (px4_msgs，条件可用)
│       - 转换: ENU → NED 坐标系
│       - 降级: px4_msgs 不可用时安全禁用
│
├── nav_local/          # 改: 兼容层 + 转发
│   ├── local_map_builder.py       (→ nav_mapping)
│   ├── local_planner.py           (→ nav_planning)
│   ├── safety_monitor.py          (→ nav_safety)
│   └── px4_bridge_node.py       (→ px4_comm_bridge)
│
└── uav_bringup/        # 新: 中央 launch + 参数管理
    ├── launch/nav_stack.launch.py
    ├── config/nav_stack.yaml
    └── rviz/nav_stack.rviz
```

## 导航数据流管道

```
┌──────────────────────────────────┐
│ 1. 传感器输入                    │
│ /oakd/points_filtered (PointCloud2) │
└───────────┬──────────────────────┘
            │
    ┌───────┴────────┐
    │                │
    ▼                ▼
┌────────────────┐ ┌──────────────┐
│ local_map_builder │ safety_monitor │
│ (nav_mapping)   │ (nav_safety)   │
└────────┬────────┘ └────────┬──────┘
         │                   │
         │ /local_map/           │ /nav/emergency
         │ /occupancy (OccupancyGrid) (Bool)
         ▼
    ┌────────────────┐
    │ local_planner  │
    │ (nav_planning) │
    └────────┬───────┘
             │
             │ /nav/cmd_vel
             ▼
    ┌────────────────────────┐
    │ px4_bridge_node      │
    │ (px4_comm_bridge)       │
    └────────┬───────────────┘
             │
             ▼ /fmu/in/*
    [PX4 Autopilot]
             │
             ▼
    飞行控制
```

## 参数管理

集中配置文件：`config/nav_stack.yaml`

```yaml
local_map_builder:
  ros__parameters:
    frame_id: map
    resolution: 0.5
    width: 40
    height: 40
    min_z: -1.0
    max_z: 2.0
    inflation_radius: 0.5
    publish_rate: 1.0
    transform_timeout_sec: 1.0

local_planner:
  ros__parameters:
    forward_speed: 0.5

safety_monitor:
  ros__parameters:
    min_points_threshold: 10

px4_bridge_node:
  ros__parameters:
    control_rate_hz: 20
    auto_arm: true
    emergency_action: LAND
```

## 启动命令

### 完整系统

```bash
ros2 launch uav_bringup nav_stack.launch.py
```

### 单个节点（开发/调试）

```bash
# 旧方式（兼容）
ros2 run nav_local local_map_builder

# 新方式（推荐）
ros2 run nav_mapping local_map_builder
```

### 带参数覆盖

```bash
ros2 launch uav_bringup nav_stack.launch.py \
  forward_speed:=1.0 \
  min_points_threshold:=20
```

## 验证状态

✅ **系统集成验证通过** (2026-05-15)

| 项目 | 状态 | 备注 |
|------|------|------|
| 构建验证 | ✅ PASS | 6 个包，0 编译错误 |
| 节点启动 | ✅ PASS | 4/4 节点正常运行 |
| 数据流管道 | ✅ PASS | 5 主话题活跃数据 |
| 消息格式 | ✅ PASS | OccupancyGrid, TwistStamped, Bool |
| 向后兼容 | ✅ PASS | nav_local 转发工作 |
| 参数管理 | ✅ PASS | 中央 YAML 配置加载 |
| 降级模式 | ✅ PASS | px4_msgs 可选，安全禁用 |

详见 [SYSTEM_INTEGRATION_TEST.md](./SYSTEM_INTEGRATION_TEST.md)

## 改进路线图

### 短期 (Week 1)
- [ ] 修复 px4_msgs Rust 生成器，启用真实 PX4 通信
- [ ] 编写综合测试套件 (pytest + ROS2 launch tests)
- [ ] 文档化完整参数表和对接接口

### 中期 (Week 2-3)
- [ ] 升级安全层：超时监控、地图有效性、故障级联
- [ ] 集成本地规划器 (DWA/DWB) 替换原型
- [ ] 与 PX4 SITL 仿真器集成

### 长期 (Week 4+)
- [ ] 硬件验收测试 (PX4 实飞)
- [ ] 性能基准与优化
- [ ] 生产就绪文档
