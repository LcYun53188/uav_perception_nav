# 综合调试与验证指南 (MASTER_DEBUGGING_GUIDE)

本指南汇总了项目所有功能包的调试逻辑，旨在提供一套从底层硬件到高层规划的标准化排查流程。

---

## 1. 调试体系架构

系统分为 8 个逻辑层级，每一层都依赖其下层的稳定性。**调试原则：禁止跳级调试。**

| 层级 | 涉及模块 | 核心指标 | 验证命令 |
| :--- | :--- | :--- | :--- |
| **L0: 环境** | uv, .venv, colcon | 编译 0 错误, Launch 参数可见 | `colcon build` |
| **L1: 传感器** | `oakd_perception`, `livox_ros_driver2` | 话题频率 (IMU 400Hz, Point 20Hz) | `ros2 topic hz` |
| **L2: 算法里程计** | `vins_fusion_ros2`, `fast_lio` | `/vio/odometry` 或 `/lio/odometry` | `ros2 topic echo` |
| **L3: 状态估计** | `robot_localization` (EKF) | `map -> odom -> base_link` TF 连通 | `ros2 run tf2_ros tf2_echo` |
| **L4: 映射层** | `nav_mapping` | `/local_map/occupancy` 随障碍变化 | `rviz2` (OccupancyGrid) |
| **L5: 规划层** | `nav_planning` | `/nav/cmd_vel` 速度矢量方向正确 | `ros2 topic echo` |
| **L6: 安全层** | `nav_safety` | `/nav/emergency` 状态反馈 | `ros2 topic echo` |
| **L7: 硬件输出** | `px4_comm_bridge`, `ground_serial_bridge` | 串口/FMU 指令下发频率 | `ros2 topic hz /fmu/in/*` |

---

## 2. 分层调试详解

### L1: 传感器层 (Sensors)
*   **OAK-D 统一节点**：
    *   **现象**：`X_LINK_DEVICE_ALREADY_IN_USE`。
    *   **排查**：确保没有多个 `oakd_depth_node` 或 `oakd_unified.launch.py` 同时运行。
    *   **检查**：`ros2 topic hz /oakd/points` (目标 20Hz)。
*   **MID360 雷达**：
    *   **现象**：无 `/livox/lidar` 话题。
    *   **排查**：Host IP 是否设为机载电脑有线网口 IP (通常 `192.168.1.5`)，防火墙是否关闭。

### L2 & L3: 定位与 TF 层 (VIO/LIO/EKF)
*   **VINS-Fusion 漂移**：
    *   **排查**：检查 `docs/OAKD_PRO_W_VINS_CALIBRATION.md`。确认 IMU 加速度计是否已校准，静止时位置跳变不应超过 5cm。
*   **TF 断裂**：
    *   **检查**：`ros2 run tf2_tools view_frames`。
    *   **重点**：`base_link` 到传感器的外参 (Static TF) 必须存在。通过 `scripts/run_nav_stack.sh` 传参修改外参。

### L4: 映射层 (Occupancy Grid)
*   **现象**：局部地图全白或全黑。
*   **排查**：
    1.  检查点云源：`/oakd/points_filtered` 是否有数据。
    2.  检查高度过滤：`min_z` 和 `max_z` 参数是否把地面当成了障碍，或把障碍过滤掉了。
    3.  检查 TF：`camera_frame -> map` 是否可用。

### L5 & L6: 规划与安全 (Control & Safety)
*   **规划器不输出速度**：
    *   **排查**：检查 `/nav/goal_pose` 是否已发布；检查安全层是否触发了 `emergency:=true`。
*   **安全层误触发**：
    *   **排查**：调低 `min_points_threshold` 或检查点云是否被遮挡。

---

## 3. 平台特定调试指南

### UAV (无人机模式)
*   **核心入口**：`./scripts/run_nav_stack.sh`
*   **关键检查**：
    *   `/fmu/in/vehicle_visual_odometry` 是否有数据送往 PX4。
    *   PX4 侧：`EKF2_EV_CTRL` 参数是否开启外部位姿。
    *   Offboard 切换：确认 `px4_comm_bridge` 收到 `cmd_vel` 且 `emergency` 为 `false`。

### Omni (地面全向轮模式)
*   **核心入口**：`./scripts/with_venv.sh ros2 launch omni_bringup omni_nav.launch.py`
*   **坐标补偿调试**：
    *   如果车辆平移时方向偏转，参考 `docs/TF_FRAMES.md` 中的“下位机坐标调试”。
    *   对比 `/base/status` 回传的 `yaw_mcu` 与上位机 `yaw_base`。
    *   **串口检查**：使用 `screen /dev/ttyUSB0 115200` 观察原始回传数据是否符合 10+2 字节协议。

---

## 4. 必备调试工具箱

### 脚本工具 (Scripts)
*   `./scripts/test_unified_system.sh`: 自动化链路完整性扫描。
*   `./scripts/apply_vendor_patches.sh`: 修复第三方 submodule 编译问题。
*   `./scripts/run_nav_stack.sh --dry-run`: 检查实际生成的 ROS 2 指令。

### 可视化 (RViz)
*   **Fixed Frame**: 必须设为 `map` 以观察全局一致性。
*   **TF**: 开启所有坐标系，检查 `base_link` 是否在地图中心。
*   **PointCloud2**: 样式改为 `Points`，Size 设为 `0.03` 方便观察细节。

### 数据记录 (Rosbag)
*   **推荐记录话题**：
    ```bash
    /tf /tf_static /odometry/local /oakd/points_filtered /local_map/occupancy /nav/cmd_vel /nav/emergency
    ```
*   **录制命令**：`./scripts/record_nav_debug_bag.sh` (如果存在) 或使用 `ros2 bag record`。

---

## 5. 常见故障自查表 (Cheat Sheet)

| 症状 | 可能原因 | 解决方法 |
| :--- | :--- | :--- |
| `colcon build` 找不到包 | 没 source `.venv` | `source .venv/bin/activate` |
| 节点启动后立即崩溃 | 配置文件路径错 | 检查 launch 中的 `FindPackageShare` |
| VIO 初始化失败 | IMU 噪声过大 | 保持机器人完全静止 3 秒 |
| 局部地图漂移 | TF 树不完整 | 检查是否漏起 EKF 或静态 TF 发布器 |
| 速度输出为 0 | 目标点已到达或被阻挡 | 检查 `/nav/goal_pose` 和规划器参数 |
| 无法连接底盘串口 | 权限不足 | `sudo chmod 666 /dev/ttyUSB*` |

---

## 6. TF 树与物理位置校验 (TF Visualization)

验证各硬件的物理位置是否与 TF 配置相符，是确保定位和避障算法有效的前提。

### 6.1 使用 RViz 2 校验物理对齐 (最直观)
RViz 可以将抽象的 TF 轴与真实的传感器数据重叠，检查“虚实是否一致”。
*   **启动命令**：`./scripts/with_venv.sh rviz2`
*   **配置步骤**：
    1.  **Fixed Frame**：设为 `map` 或 `odom`。
    2.  **添加 TF**：点击 `Add` -> `TF`。检查 `base_link` 到传感器（如 `oakd_imu_link`）的相对位置。
    3.  **叠加点云**：点击 `Add` -> `PointCloud2`，选择 `/oakd/points`。
*   **判定标准**：
    *   **高度对齐**：若机体离地 15cm，点云中的地面应刚好位于 `base_link` 下方 15cm 处。
    *   **转动一致性**：原地旋转机器人。若点云（如墙壁）在 RViz 中保持不动而坐标轴在转，说明外参正确；若点云随坐标轴一起转，说明**旋转外参 (Yaw/Pitch/Roll)** 设反了。

### 6.2 使用 view_frames 校验逻辑结构 (查断裂)
若话题有数据但 RViz 不显示，通常是 TF 树断裂。
*   **生成结构图**：`./scripts/with_venv.sh ros2 run tf2_tools view_frames`
*   **检查重点**：确保 `map -> odom -> base_link -> 传感器` 是一条完整的单向链，无断开的孤岛。

### 6.3 使用 tf2_echo 校验数值精度 (对参数)
用于验证修改后的 `.sh` 启动参数或 `yaml` 配置文件是否真实生效。
*   **查询命令**：`./scripts/with_venv.sh ros2 run tf2_ros tf2_echo base_link oakd_imu_link`
*   **对比标准**：将输出的 `Translation [x, y, z]` 与物理测量值进行比对，误差应在毫米级。

---

最后更新：2026-05-20
