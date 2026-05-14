# oakd_perception

本包负责 OAK-D 设备侧感知能力（IMU 原始数据 + 深度点云）。

重要说明：
- 实际使用（生产/日常运行）只使用统一节点 `oakd_unified_node`。
- 独立节点 `oakd_imu_node` 和 `oakd_depth_node` 仅用于测试、对比和问题定位。

## 1. 包内节点说明

### 1.1 oakd_unified_node（主节点，推荐）

文件位置：
- `oakd_perception/oakd_unified_node.py`

作用：
- 单进程连接 OAK-D，统一采集 IMU 与深度。
- 避免独立节点并发启动时的设备冲突（常见为 `X_LINK_DEVICE_ALREADY_IN_USE`）。

默认输出：
- `/oakd/imu/raw`（`sensor_msgs/Imu`）
- `/oakd/points`（`sensor_msgs/PointCloud2`）

常用参数（见 `launch/oakd_unified.launch.py`）：
- `imu_frequency`（默认 400）
- `pointcloud_frequency`（默认 20）
- `enable_passive_stereo`（默认 true）
- `enable_active_stereo`（默认 false）
- `ir_intensity`（默认 1600）
- `sampling_step`（默认 2）
- `min_depth`（默认 200）
- `max_depth`（默认 5000）

### 1.2 oakd_imu_node（仅测试）

文件位置：
- `oakd_perception/oakd_imu_node.py`

作用：
- 单独验证 IMU 采集链路。

默认输出：
- `/oakd/imu/raw`

备注：
- 不建议与 `oakd_depth_node` 同时运行在同一设备上。

### 1.3 oakd_depth_node（仅测试）

文件位置：
- `oakd_perception/oakd_depth_node.py`

作用：
- 单独验证深度点云链路和立体参数。

默认输出：
- `/oakd/points`

备注：
- 不建议与 `oakd_imu_node` 同时运行在同一设备上。

### 1.4 fov_boundary_filter（工具模块）

文件位置：
- `oakd_perception/fov_boundary_filter.py`

作用：
- 点云 FOV 边界过滤与几何约束工具。
- 非独立 ROS 节点。

## 2. 完整启动操作（推荐流程）

以下为从工作空间根目录执行。

### 2.1 构建

```bash
./scripts/with_venv.sh colcon build --packages-select oakd_perception imu_fusion
```

### 2.2 启动统一节点（生产方式）

```bash
./scripts/with_venv.sh ros2 launch oakd_perception oakd_unified.launch.py
```

### 2.3 启动 IMU 融合与 TF（可选但常用）

```bash
./scripts/with_venv.sh ros2 launch imu_fusion imu_fusion.launch.py
```

### 2.4 启动可视化（可选）

```bash
./scripts/with_venv.sh rviz2
```

## 3. 一键/脚本化启动

### 3.1 深度模式快速脚本（位于包内）

- `scripts/run_oakd_outdoor.sh`
- `scripts/run_oakd_balance.sh`
- `scripts/run_oakd_indoor.sh`
- `scripts/run_oakd_active_max.sh`

说明：
- 包内脚本位于 `src/oakd_perception/scripts/`。
- 工作空间根目录 `scripts/` 下同名脚本是兼容入口，会转发到包内脚本。

### 3.2 完整系统脚本（工作空间根目录）

```bash
./scripts/run_complete_system.sh
```

## 4. 测试场景启动（仅调试时使用）

### 4.1 仅测试 IMU 节点

```bash
./scripts/with_venv.sh ros2 run oakd_perception oakd_imu_node
```

### 4.2 仅测试深度节点

```bash
./scripts/with_venv.sh ros2 run oakd_perception oakd_depth_node
```

注意：
- 这两个独立节点不要同时跑在同一个 OAK-D 上。
- 若遇设备占用错误，先清理相关进程再重启。

## 5. 运行检查

### 5.1 节点

```bash
./scripts/with_venv.sh ros2 node list
```

### 5.2 话题

```bash
./scripts/with_venv.sh ros2 topic list
```

### 5.3 频率

```bash
./scripts/with_venv.sh ros2 topic hz /oakd/imu/raw
./scripts/with_venv.sh ros2 topic hz /oakd/points
```

## 6. 常见问题

### 6.1 设备占用（X_LINK_DEVICE_ALREADY_IN_USE）

处理方式：

```bash
pkill -9 -f oakd_ 2>/dev/null || true
sleep 1
```

然后仅启动 `oakd_unified_node`。

### 6.2 启动后无点云

建议检查：
- OAK-D 是否正常连接。
- `/oakd/points` 是否存在。
- `min_depth/max_depth` 是否过严。
- 立体模式是否适合当前环境（户外优先被动，弱光可开主动）。

## 7. 相关文件

- `launch/oakd_unified.launch.py`
- `QUICK_START.md`
- `DEPTH_MODE_CONFIG.md`
- `scripts/README.md`
