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
        │ (400Hz)        │ (20Hz)
        └────┬───────────┘
             │
      ┌──────▼─────────────┐
      │  imu_fusion_node   │ (融合 + TF 广播)
      ├────────────────────┤
      │ - 计算融合姿态     │
      │ - 广播 TF         │
      └────┬───────────────┘
           │
        ┌──┴──┐────────────┐
        │     │            │
   /imu │/tf  │ map→imu_link│
(100Hz) │     │    (动态)   │
        │     │            │
        └─────┴────────────┘
```

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
- 发布 `/oakd/imu/raw` 与 `/oakd/points`。

**关键特性**：

- 单进程设计，避免设备冲突；
- 可配置的发布频率与参数；
- 集成立体深度模式（被动/主动）。

**发布主题**：

```
/oakd/imu/raw     (sensor_msgs/Imu, 400Hz)
/oakd/points      (sensor_msgs/PointCloud2, 20Hz)
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

### 3. imu_tf_broadcaster

**职责**：

- 订阅融合后的 IMU（`/imu`）；
- 广播 TF 变换 `map → imu_link`；
- 使点云能随 IMU 姿态旋转（RViz 中）。

**广播变换**：

```
map (全局坐标系)
  └── imu_link (IMU 坐标系)
       ├── oakd_link (相机坐标系)
       └── ...
```

---

## 数据流

### 启动流程

```
1. 启动 oakd_unified_node
   ├── 初始化 OAK-D SDK
   ├── 配置 IMU 采样（400Hz）
   ├── 配置深度处理（20Hz）
   └── 开始发布数据

2. 启动 imu_fusion
   ├── 订阅 /oakd/imu/raw
   └── 发布融合后 /imu

3. 启动 imu_tf_broadcaster
   ├── 订阅 /imu
   └── 广播 map → imu_link

4. 启动 RViz（可视化）
   ├── 订阅 /oakd/points
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

/oakd/points ───► RViz
  (20Hz)      (订阅与显示)
```

---

## 关键参数

### IMU 配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `imu_frequency` | int | 400 | 采样频率（Hz） |
| `imu_topic_name` | str | /oakd/imu/raw | 发布主题 |
| `imu_frame_id` | str | oakd_imu_link | 坐标系 |

### 深度配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enable_passive_stereo` | bool | true | 被动立体 |
| `enable_active_stereo` | bool | false | 主动立体 |
| `ir_intensity` | int | 1600 | 红外强度 |
| `sampling_step` | int | 2 | 下采样步长 |
| `min_depth` | int | 200 | 最小深度（mm） |
| `max_depth` | int | 5000 | 最大深度（mm） |
| `pointcloud_frequency` | int | 20 | 点云频率（Hz） |

---

## 坐标系定义

### 坐标系树

```
map
  └── imu_link (融合 IMU 确定的姿态)
       ├── oakd_imu_link (IMU 物理位置)
       └── oakd_link (相机光学中心)
```

### 坐标系说明

- **map**：全局世界坐标系（由 `imu_fusion` 定义为参考）；
- **imu_link**：IMU 经融合后的坐标系，包含 orientation；
- **oakd_link**：OAK-D 相机的机体坐标系（深度点云的参考帧）。

---

## 启动方式

### 方式 1：完整启动脚本

```bash
./scripts/run_complete_system.sh
# 选择 1: 完整系统
```

### 方式 2：逐步手动启动

```bash
# 终端 1: 统一节点
./scripts/with_venv.sh ros2 launch oakd_perception oakd_unified.launch.py

# 终端 2: IMU 融合
./scripts/with_venv.sh ros2 launch imu_fusion imu_fusion.launch.py \
  raw_topic_0:=/oakd/imu/raw \
  fused_topic_0:=/imu \
  frame_id_0:=imu_link \
  parent_frame:=map

# 终端 3: RViz 可视化
./scripts/with_venv.sh rviz2
```

### 方式 3：直接运行节点

```bash
# 仅统一节点（不含融合）
./scripts/with_venv.sh ros2 run oakd_perception oakd_unified_node
```

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

- 检查 `/oakd/points` 话题频率：`ros2 topic hz /oakd/points`
- 调整深度范围：`min_depth`、`max_depth`
- 尝试启用主动立体：`enable_active_stereo:=true`

### IMU 数据异常

- 检查 IMU 原始数据：`ros2 topic echo /oakd/imu/raw`
- 重启 IMU 融合节点
- 查看融合参数配置

---

## 参考资源

- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — 快速命令参考
- [INSTALLATION.md](./INSTALLATION.md) — 安装与构建
- [../README.md](../README.md) — 主文档
- [DepthAI 官方文档](https://docs.luxonis.com/)
- [ROS 2 官方文档](https://docs.ros.org/en/humble/)

---

## 版本历史

- **v1.0** (2026-05)：统一节点架构首次实现，解决设备冲突问题。
