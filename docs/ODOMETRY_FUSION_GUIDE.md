# 融合里程计中枢集成说明

## 概述

本项目已集成 `robot_localization` 的 EKF（Extended Kalman Filter）节点，用于融合多个传感器数据源（IMU、VIO、PX4 飞控）生成稳定的 `nav_msgs/Odometry` 消息与 `odom → base_link` TF 变换。

## 组件

### 1. IMU 输入（必须）
- **话题**：`/imu` (sensor_msgs/Imu)
- **来源**：`imu_fusion_node`（位于 `oakd_imu_fusion` 包）
- **频率**：100Hz
- **融合的维度**：姿态（roll, pitch, yaw）+ 角速度

### 2. VIO 输入（可选）
- **话题**：`/vio/odometry` (nav_msgs/Odometry)
- **来源**：外部 VIO 模块（例如 VINS-Fusion、ORB-SLAM3）
- **融合的维度**：位置（x, y, z）+ 朝向（yaw）+ 线速度
- **启用方式**：`odom0` 参数已在 `config/ekf.yaml` 中配置

### 3. PX4 飞控输入（可选）
- **话题**：`/px4/vehicle_odometry` (px4_msgs::VehicleOdometry)
- **来源**：PX4 自驾仪（通过 `nav_px4_bridge` 转换）
- **融合的维度**：位置 + 朝向 + 线/角速度
- **启用方式**：在 `config/ekf.yaml` 中注释掉 `odom1` 部分的注释以启用

## 输出

### Odometry 消息
- **话题**：`/odometry/filtered` (nav_msgs/Odometry)
- **频率**：30Hz（可配置）
- **包含**：位置、朝向、线/角速度、协方差

### TF 变换
- **发布**：`odom → base_link`
- **作用**：提供里程计坐标系到基础链接的变换
- **注意**：`map → odom` 在需要全局定位时由后端修正（例如尾部闭合或 GNSS）

## 启用 EKF

### 方式 1：启动完整导航栈（推荐）
```bash
source scripts/with_venv.sh
ros2 launch uav_bringup nav_stack.launch.py
```

此命令将启动：
- OAK-D 传感器节点（IMU + 深度相机）
- IMU 融合模块
- EKF 融合中枢（**自动包含**）
- 局部建图、规划、安全监督

### 方式 2：仅启动 EKF 与 IMU 融合
```bash
source scripts/with_venv.sh

# 终端 1：启动传感器与 IMU 融合
ros2 launch oakd_perception oakd_unified.launch.py
ros2 launch imu_fusion imu_fusion.launch.py

# 终端 2：启动 EKF 节点
ros2 launch uav_bringup ekf_launch.py
```

### 方式 3：启动 EKF 与 VIO（用于测试）
```bash
source scripts/with_venv.sh

# 终端 1：启动 IMU 融合
ros2 launch imu_fusion imu_fusion.launch.py

# 终端 2：启动外部 VIO（例如 VINS-Fusion）
# 假设 /vio/odometry 已发布

# 终端 3：启动 EKF
ros2 launch uav_bringup ekf_launch.py

# 终端 4：监视输出
ros2 topic echo /odometry/filtered
```

## 配置参数

所有 EKF 参数位于 `config/ekf.yaml`，主要参数说明如下：

| 参数 | 值 | 说明 |
|------|-----|------|
| `frequency` | 30.0 | EKF 更新频率（Hz） |
| `sensor_timeout` | 0.1 | 传感器超时时间（秒） |
| `two_d_mode` | false | 2D 模式（仅平面运动） |
| `imu0_config` | 见下表 | IMU 的融合变量 |
| `odom0_config` | 见下表 | VIO 的融合变量 |
| `process_noise_covariance` | 见 yaml | 过程噪声（状态变化速率） |
| `initial_estimate_covariance` | 见 yaml | 初始估计协方差 |

### IMU 融合变量 (`imu0_config`)
```
- false  # x (位置不融合，由 VIO 或 PX4 提供)
- false  # y
- false  # z
- true   # roll (角度融合)
- true   # pitch
- true   # yaw
- false  # vx (线速度不融合)
- false  # vy
- false  # vz
- true   # vroll (角速度融合)
- true   # vpitch
- true   # vyaw
- false  # ax (加速度不融合)
- false  # ay
- false  # az
```

### VIO 融合变量 (`odom0_config`)
```
- true   # x (位置融合)
- true   # y
- true   # z
- false  # roll (角度由 IMU 提供)
- false  # pitch
- true   # yaw (偏航由视觉提供)
- true   # vx (线速度融合)
- true   # vy
- true   # vz
- false  # vroll (角速度由 IMU 提供)
- false  # vpitch
- false  # vyaw
- false  # ax
- false  # ay
- false  # az
```

## 启用/禁用特定输入源

### 启用 PX4 车辆里程计

编辑 `config/ekf.yaml`，找到 `odom1` 部分，取消注释：

```yaml
odom1: /px4/vehicle_odometry
odom1_config:
  - true   # x
  - true   # y
  - true   # z
  - true   # roll
  - true   # pitch
  - true   # yaw
  ...
```

### 禁用 VIO（使用仅 IMU + PX4）

编辑 `config/ekf.yaml`，注释掉 `odom0` 部分：

```yaml
# odom0: /vio/odometry
# odom0_config:
#   ...
```

### 禁用输入源

直接在 YAML 中注释掉相应的 `odom*` 或 `imu*` 部分，或设置其 `config` 全为 `false`。

## 调试与验证

### 1. 检查话题发布

```bash
# 检查 IMU
ros2 topic hz /imu
ros2 topic echo /imu

# 检查 VIO（若启用）
ros2 topic hz /vio/odometry
ros2 topic echo /vio/odometry

# 检查 EKF 输出
ros2 topic hz /odometry/filtered
ros2 topic echo /odometry/filtered
```

### 2. 查看 TF 树

```bash
# 快速查看
ros2 run tf2_tools view_frames

# 或用 RViz 显示 TF 树（Add → TF）
```

### 3. RViz 可视化

在 RViz 中添加：
- **Odometry** 显示：订阅 `/odometry/filtered`，设置颜色和尺寸
- **TF** 显示：查看 `odom → base_link` 变换
- **Axes** 显示：标记 `odom` 与 `base_link` 原点

### 4. 监视诊断信息

```bash
ros2 run diagnostic_aggregator aggregator_node
ros2 run rqt_reconfigure rqt_reconfigure  # 运时调整参数
```

## 常见问题与解决方案

### Q1：EKF 节点无法启动
**症状**：`Could not find executable 'ekf_node'`

**解决**：
1. 确保 `robot_localization` 已在 venv 中编译：
   ```bash
   source scripts/with_venv.sh
   colcon build --packages-select robot_localization
   ```
2. 重新 source 工作区：
   ```bash
   source install/setup.bash
   ```

### Q2：输出话题频率不稳定或缺失
**症状**：`/odometry/filtered` 发布不稳定或话题不存在

**解决**：
1. 检查输入源（IMU/VIO）是否在线：
   ```bash
   ros2 topic list | grep -E "imu|vio|odometry"
   ```
2. 检查 EKF 日志：
   ```bash
   ros2 launch uav_bringup ekf_launch.py  # 查看 stderr 输出
   ```
3. 调整 `sensor_timeout` 与 `frequency` 参数

### Q3：融合结果不稳定或漂移大
**症状**：估计的位置/朝向持续漂移或抖动

**解决**：
1. 检查协方差设置是否合理（较小的协方差意味着更信任该源）
2. 尝试调整 `process_noise_covariance` 与 `initial_estimate_covariance`
3. 逐减输入源排查：先用 IMU+VIO，再加 PX4
4. 确保输入消息的 `frame_id` 一致性

### Q4：TF 变换报告错误或循环
**症状**：`tf2_ros TransformListener` 报告 TF 树错误

**解决**：
1. 检查所有节点发布的 TF 是否冲突（同一父-子帧对）
2. 验证 `config/ekf.yaml` 中 `map_frame`、`odom_frame`、`base_link_frame` 与实际 TF 树一致
3. 查看 TF 静态广播器是否正确发布初始变换

## 高级调优

### 1. 协方差调整策略

- **IMU 协方差过大**（不信任 IMU）：增加 `imu0` 相关维度的噪声；减小 VIO 协方差
- **VIO 协方差过大**（不信任 VIO）：调整 VIO 输入的 `config` 中每个维度的噪声

### 2. 启用 2D 模式

若系统仅在平面内运动（例如水平平台），设置 `two_d_mode: true`，可简化状态维度并加快收敛。

### 3. 实时参数调整

使用 ROS 2 runtime reconfiguration 动态调整参数而无需重启：

```bash
ros2 run rqt_reconfigure rqt_reconfigure

# 或命令行方式
ros2 param set /ekf_filter_node frequency 50.0
```

## 与现有导航栈的集成

### 数据流

```
/imu (imu_fusion_node)
  ↓
[EKF Filter Node]
  ↓
/odometry/filtered  →  nav_mapping (可选：使用融合位置)
                    →  nav_planning  (可选：使用融合速度)
                    →  nav_safety    (可选：监视融合健康度)
                    →  nav_px4_bridge (可选：反馈位置)
```

### 下一步可能的改进

1. **里程计驱动建图**：让 `nav_mapping` 订阅 `/odometry/filtered` 而非纯点云
2. **反馈控制**：在 `nav_px4_bridge` 中利用融合位置进行位置反馈控制
3. **尾部闭合与优化**：集成 loop-closure 检测器修正 `map → odom` 变换

## 参考资源

- [robot_localization 官方文档](http://docs.ros.org/en/rolling/p/robot_localization/)
- [EKF 文档](http://docs.ros.org/en/rolling/p/robot_localization/generated/ekf_localization_node.html)
- [当前项目架构文档](../ARCHITECTURE.md)

---

**最后更新**：2026-05-16  
**维护者**：导航栈团队
