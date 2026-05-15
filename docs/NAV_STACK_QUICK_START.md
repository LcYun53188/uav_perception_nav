# 导航栈快速启动指南

**更新日期**: 2026-05-15
**系统状态**: ✅ 已验证可用

---

## 快速启动 (30 秒)

### 1. 环境设置
```bash
cd /home/nuc/Program/uav_vision_ws
source install/setup.bash
```

### 2. 启动完整导航栈
```bash
ros2 launch uav_bringup nav_stack.launch.py
```

### 3. 在另一个终端监听速度命令
```bash
source install/setup.bash
ros2 topic echo /nav/cmd_vel
```

### 4. 查看局部地图

#### 方式 1：终端查看地图话题
```bash
source install/setup.bash
ros2 topic echo /local_map/occupancy --no-arr | head -40
```

也可以查看发布频率和消息类型：
```bash
ros2 topic info /local_map/occupancy
ros2 topic hz /local_map/occupancy
```

#### 方式 2：RViz 可视化查看
```bash
source install/setup.bash
./scripts/with_venv.sh rviz2
```

在 RViz 中：

- Fixed Frame 设为 `map`；
- 添加 `Map` 显示；
- Topic 选择 `/local_map/occupancy`；
- 如果同时看点云，可再添加 `/oakd/points_filtered` 的 `PointCloud2`。
- 如需对比原始数据，可另外添加 `/oakd/points`。

**预期输出**:
```yaml
header:
  stamp:
    sec: 1778808817
    nanosec: 488951737
  frame_id: map
twist:
  linear:
    x: 0.5    # 前向速度 (m/s)
    y: 0.0
    z: 0.0
```

---

## 系统内部构成

### 启动的 4 个节点

1. **local_map_builder** (`nav_mapping`)
   - 输入: `/oakd/points_filtered` (点云)
   - 输出: `/local_map/occupancy` (占用栅栏)
   - 职责: 3D 点云 → 2D 地图

2. **local_planner** (`nav_planning`)
   - 输入: `/local_map/occupancy` (占用栅栏)
   - 输出: `/nav/cmd_vel` (速度命令)
   - 职责: 地图 → 运动决策

3. **safety_monitor** (`nav_safety`)
   - 输入: `/oakd/points` (点云)
   - 输出: `/nav/emergency` (紧急标志)
   - 职责: 传感器监视 → 故障检测

4. **px4_offboard_ctrl** (`nav_px4_bridge`)
   - 输入: `/nav/cmd_vel` + `/nav/emergency`
   - 输出: `/fmu/in/*` (PX4 消息, 如可用)
   - 职责: 速度 → 飞控命令

---

## 常用命令

### 查看运行中的节点
```bash
ros2 node list
```

### 查看活跃话题
```bash
ros2 topic list
```

### 监听特定话题

```bash
# 监听占用栅栏
ros2 topic echo /local_map/occupancy --no-arr | head -20

# 监听速度命令
ros2 topic echo /nav/cmd_vel --no-arr

# 监听紧急标志
ros2 topic echo /nav/emergency --no-arr
```

### 查看节点参数

```bash
# local_map_builder 参数
ros2 param list /local_map_builder

# 获取单个参数值
ros2 param get /local_map_builder frame_id
# 输出: String value is: map
```

### 运行时修改参数

```bash
# 改变前向速度
ros2 param set /local_planner forward_speed 1.0

# 改变地图分辨率
ros2 param set /local_map_builder resolution 0.25

# 改变安全阈值
ros2 param set /safety_monitor min_points_threshold 20
```

---

## 参数明细

### local_map_builder (nav_mapping)

| 参数 | 默认 | 范围 | 说明 |
|------|------|------|------|
| `frame_id` | "map" | string | 全局参考帧 |
| `resolution` | 0.5 | 0.1-1.0 | 栅栏分辨率 (m/cell) |
| `width` | 40 | 10-100 | 栅栏宽度 (cells) |
| `height` | 40 | 10-100 | 栅栏高度 (cells) |
| `min_z` | -1.0 | -5.0 to 0.0 | 点云下限 (m) |
| `max_z` | 2.0 | 0.5 to 5.0 | 点云上限 (m) |
| `inflation_radius` | 0.5 | 0.1-2.0 | 障碍膨胀 (m) |
| `publish_rate` | 1.0 | 0.1-10.0 | 发布频率 (Hz) |
| `transform_timeout_sec` | 1.0 | 0.1-5.0 | TF 查询超时 (s) |

**调优建议**:
- 接近障碍物：减少 `inflation_radius`
- 处理移动对象：增加 `publish_rate`
- 噪声太多：调整 `min_z`, `max_z`, `resolution`

### local_planner (nav_planning)

| 参数 | 默认 | 范围 | 说明 |
|------|------|------|------|
| `forward_speed` | 0.5 | 0.1-2.0 | 前向速度 (m/s) |

**说明**: 当前为原型简单策略。中心自由时以恒定速度前进。

### safety_monitor (nav_safety)

| 参数 | 默认 | 范围 | 说明 |
|------|------|------|------|
| `min_points_threshold` | 10 | 1-1000 | 最小点数 |

**说明**: 点数低于阈值时触发 emergency = true。

### px4_offboard_ctrl (nav_px4_bridge)

参数通常为默认值。运行在降级模式（px4_msgs 不可用）。

---

## 典型工作流

### 场景 1: 调试地图生成

```bash
# 启动只映射节点（独立开发）
ros2 run nav_mapping local_map_builder

# 另一个终端发送虚拟点云
python3 /tmp/test_nav_flow.py

# 第三个终端监听地图
ros2 topic echo /local_map/occupancy --no-arr
```

### 场景 2: 测试完整管道

```bash
# 启动完整系统
ros2 launch uav_bringup nav_stack.launch.py

# 在多个终端监听各话题
Terminal A: ros2 topic echo /local_map/occupancy
Terminal B: ros2 topic echo /nav/cmd_vel
Terminal C: ros2 topic echo /nav/emergency
```

### 场景 3: 参数调优

```bash
# 启动系统
ros2 launch uav_bringup nav_stack.launch.py

# 修改参数（实时生效）
ros2 param set /local_map_builder resolution 0.25
ros2 param set /local_planner forward_speed 1.0

# 观察效果
ros2 topic echo /local_map/occupancy
```

### 场景 4: 性能测试

```bash
# 启动，记录消息频率
ros2 topic hz /local_map/occupancy
ros2 topic hz /nav/cmd_vel
ros2 topic hz /nav/emergency

# 检查延迟
ros2 topic delay /nav/cmd_vel
```

---

## 故障排查

### 问题 1: 启动时找不到 px4_msgs

```
[ERROR] px4_msgs is not available; PX4 bridge will stay inactive
```

**原因**: px4_msgs 包构建失败（已知问题）
**影响**: ⚠️ PX4 消息未发布，其他功能正常
**解决**: 这是预期的降级行为，系统继续工作

### 问题 2: 话题无数据流动

```bash
ros2 topic hz /oakd/points_filtered
# 输出: Topic /oakd/points_filtered does not have any publishers yet
```

**原因**: 需要 OAK-D 硬件或仿真器
**解决**: 启动 OAK-D 节点或使用测试发布器；如果想检查原始点云，可改看 `/oakd/points`
```bash
python3 /tmp/test_nav_flow.py
```

### 问题 3: TF 变换错误

```
[ERROR] [local_map_builder]: Cannot find TF from camera_depth_optical_frame to map
```

**原因**: TF 树不完整，缺少相机 → IMU → map 的变换链
**解决**:
```bash
# 检查 TF 树
ros2 run tf2_tools view_frames

# 启动 IMU TF 广播器
./scripts/run_imu_fusion_tf.sh
```

### 问题 4: 参数未生效

```bash
# 查看实际参数值
ros2 param get /local_map_builder resolution
# String value is: 0.5

# 修改
ros2 param set /local_map_builder resolution 0.25

# 重新查看
ros2 param get /local_map_builder resolution
# String value is: 0.25
```

如果修改后仍未生效，重启节点。

---

## 系统信息

### 版本

- 导航栈版本: 2.0 (拆分)
- ROS2 版本: Jazzy
- Python 版本: 3.12
- 构建系统: colcon + ament_python

### 包列表

```
nav_mapping (local_map_builder)
nav_planning (local_planner)
nav_safety (safety_monitor)
nav_px4_bridge (px4_offboard_ctrl)
nav_local (兼容层)
uav_bringup (启动/配置)
```

### 文档位置

- 完整架构: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 系统集成测试: [SYSTEM_INTEGRATION_TEST.md](./SYSTEM_INTEGRATION_TEST.md)
- 安装指南: [INSTALLATION.md](./INSTALLATION.md)
- 主 README: [../README.md](../README.md)

---

## 常见问题 (FAQ)

**Q: 我能在其他 ROS2 发行版上运行这个吗？**
A: 理论上支持任何 ROS2 发行版（Humble, Iron, Jazzy 等），只要安装了所需的消息包。

**Q: 如何禁用某个节点？**
A: 编辑 `config/nav_stack.yaml`，注释掉对应节点的参数块。

**Q: 能否并行运行多个导航栈实例？**
A: 可以，但需要不同的命名空间或参数。详见高级文档。

**Q: 如何贡献改进？**
A: 各节点独立开发，提交 PR 到对应的功能包。

---

**快速帮助**: `ros2 launch uav_bringup nav_stack.launch.py --help`

**获取更多信息**: 查看 [ARCHITECTURE.md](./ARCHITECTURE.md) 详细设计文档
