# 可视化软件配置指南 (RViz 2 & Foxglove Studio)

本指南提供了如何配置 RViz 2 和 Foxglove Studio 以监控无人机（UAV）和全向轮机器人（Omni）状态的详细说明。

---

## 1. RViz 2 配置指南

RViz 2 是 ROS 2 的原生 3D 可视化工具，适合本地实时调试。

### 1.1 基本启动
```bash
./scripts/with_venv.sh rviz2
```

### 1.2 核心面板配置
建议手动添加以下 Display 项并保存配置：

| 分类 | 插件类型 | 建议话题 | 说明 |
| :--- | :--- | :--- | :--- |
| **基础** | `TF` | `/tf`, `/tf_static` | 检查坐标树连通性 |
| **感知** | `PointCloud2` | `/oakd/points_filtered` | 避障点云（已过滤高度/噪点） |
| **感知** | `PointCloud2` | `/mid360/points` | 雷达原始转换点云 |
| **映射** | `OccupancyGrid` | `/local_map/occupancy` | 局部代价地图（规划输入） |
| **定位** | `Odometry` | `/odometry/local` | EKF 融合后的里程计 |
| **定位** | `Odometry` | `/vio/odometry` | VINS 原始输出（对比漂移） |
| **规划** | `Path` | `/nav/path` (若有) | 规划的路径线 |

### 1.3 关键设置
*   **Fixed Frame**: 
    *   调试传感器外参：设为 `base_link`。
    *   验证定位/建图：必须设为 `map`。
*   **Global Options**: 将 `Reliability Policy` 设为 `Best Effort` 以处理高带宽点云话题。

---

## 2. Foxglove Studio 配置指南

Foxglove 提供更现代、可定制的 Web/跨平台界面，适合远程监控和数据分析。

### 2.1 启动连接
1.  启动 Foxglove Bridge:
    ```bash
    ./scripts/with_venv.sh ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765
    ```
2.  在 Foxglove 软件中选择 `Open connection` -> `Foxglove WebSocket` -> 输入 `ws://localhost:8765`。

### 2.2 推荐布局 (Layout)
建议按以下逻辑划分面板：

*   **3D Panel**: 
    *   包含所有 TF、点云和里程计。
    *   设置为 `Reference frame: base_link`。
*   **Plot Panel (时间序列)**:
    *   话题：`/nav/safety_status` (数据安全评分)。
    *   话题：`/nav/emergency` (布尔应急标志)。
    *   话题：`/fmu/out/vehicle_status` (PX4 状态：arming/nav_state)。
*   **Raw Messages (原始文本)**:
    *   监控 `/nav/cmd_vel` 和 `/fmu/in/trajectory_setpoint` 的对应关系。

### 2.3 导入/导出
*   你可以将布局保存为 `.json` 文件以便在不同设备间迁移。
*   项目推荐布局详见 `docs/FOXGLOVE_VALIDATION_LAYOUT.md`。

---

## 3. UAV 专有监控建议 (PX4)

当连接真实飞控或 SITL 仿真时，请重点关注以下 PX4 原生主题：

1.  **/fmu/out/vehicle_status**: 确认 `arming_state` (2 为 ARMED) 和 `nav_state` (14 为 OFFBOARD)。
2.  **/fmu/out/vehicle_odometry**: 飞控内部估计的位姿，用于对比上位机 EKF 输出。
3.  **/fmu/in/vehicle_command**: 监控上位机下发的模式切换指令。

---

## 4. Omni 专有监控建议 (全向轮)

针对地面底盘，请重点关注：

1.  **/base/status**: 包含底盘使能状态、错误码。
2.  **/base/diagnostics**: 包含下位机测算的 Yaw 与上位机 TF 计算出的 `yaw_error`。
3.  **坐标轴检查**: 在 RViz 中确认 `base_link` 的旋转方向与实车转向一致（逆时针为正）。

---

## 5. 保存与复用

*   **RViz**: 建议将满意的配置保存为 `src/uav_bringup/rviz/default.rviz`，并在 Launch 文件中通过 `rviz_config` 参数加载。
*   **Foxglove**: 建议点击工作区左侧的 `Export layout to file` 导出。

---

最后更新：2026-05-20
