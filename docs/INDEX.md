# 文档索引

欢迎来到 **uav_vision_ws** 文档库。本目录按主题组织技术文档与指南，支持快速查阅。

---

## 📚 核心文档（快速定位）

| 文档 | 描述 | 目标读者 | 阅读时间 |
|------|------|--------|--------|
| [INSTALLATION.md](./INSTALLATION.md) | 虚拟环境、依赖、构建 | 开发者、新用户 | 15 min |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 系统架构、数据流、节点设计 | 架构师、集成者 | 20 min |
| [PX4_NAVIGATION_STRATEGY.md](./PX4_NAVIGATION_STRATEGY.md) | PX4 导航与避障路线，对比 nav 与 3D 方案 | 导航集成者、算法开发者 | 15 min |
| [OAKD_PRO_W_VINS_CALIBRATION.md](./OAKD_PRO_W_VINS_CALIBRATION.md) | OAK-D Pro W 与 VINS-Fusion 标定、静止漂移排查 | VIO 集成者、调试人员 | 15 min |
| [SENSOR_DEBUG_GUIDE.md](./SENSOR_DEBUG_GUIDE.md) | OAK-D / MID360 单设备启动、话题检查、RViz 与 bag 调试 | 调试人员、集成者 | 10 min |
| [SUBMODULE_PATCH_REPRODUCTION.md](./SUBMODULE_PATCH_REPRODUCTION.md) | 第三方 submodule + patch 复刻与维护流程 | 开发者、集成者 | 10 min |
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | 常用命令、参数、问题排查 | 所有用户 | 10 min |
| [../README.md](../README.md) | 项目主文档、快速开始 | 所有用户 | 10 min |

---

## 🎯 快速导航（按任务）

### 初次使用

1. 阅读 [../README.md](../README.md#快速开始-quick-start) — **快速开始** 节
2. 按 [INSTALLATION.md](./INSTALLATION.md) — 配置虚拟环境
3. 查阅 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) — 启动节点
4. 直接使用标准入口脚本： [scripts/run_nav_stack.sh](../scripts/run_nav_stack.sh)，单设备调试见 [SENSOR_DEBUG_GUIDE.md](./SENSOR_DEBUG_GUIDE.md)

### 深入学习

- 需要了解架构设计？ → [ARCHITECTURE.md](./ARCHITECTURE.md)
- 需要规划 PX4 导航路线？ → [PX4_NAVIGATION_STRATEGY.md](./PX4_NAVIGATION_STRATEGY.md)
- 想调整参数与配置？ → [../README.md](../README.md#5-配置与参数) 或 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md#常用启动参数)
- OAK-D Pro W 接入 VINS 静止漂移？ → [OAKD_PRO_W_VINS_CALIBRATION.md](./OAKD_PRO_W_VINS_CALIBRATION.md)
- 只调试 OAK-D 或 MID360？ → [SENSOR_DEBUG_GUIDE.md](./SENSOR_DEBUG_GUIDE.md)
- 需要复刻 MID360/FAST-LIO2 第三方源码？ → [SUBMODULE_PATCH_REPRODUCTION.md](./SUBMODULE_PATCH_REPRODUCTION.md)
- 想确认启动入口？ → [../README.md](../README.md#4-运行与启动) 或 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md#启动命令)
- 遇到问题？ → [QUICK_REFERENCE.md](./QUICK_REFERENCE.md#常见问题与解决) 或 [../README.md](../README.md#10-故障排查)

### 查看历史与参考

- 了解项目完成情况？ → [archive/IMPLEMENTATION_SUMMARY.md](./archive/IMPLEMENTATION_SUMMARY.md)
- 旧架构分析？ → [archive/ARCHITECTURE_ANALYSIS.md](./archive/ARCHITECTURE_ANALYSIS.md)
- 包命名历史？ → [archive/PACKAGE_RENAME_SUMMARY.md](./archive/PACKAGE_RENAME_SUMMARY.md)

---

## 📁 文档结构

```
docs/
├── INDEX.md                      # 本文件
├── INSTALLATION.md               # 环境安装指南
├── ARCHITECTURE.md               # 系统架构设计
├── PX4_NAVIGATION_STRATEGY.md    # PX4 导航与避障路线对比
├── SENSOR_DEBUG_GUIDE.md         # OAK-D / MID360 独立调试
├── SUBMODULE_PATCH_REPRODUCTION.md # 第三方源码复刻与 patch 流程
├── QUICK_REFERENCE.md            # 快速命令参考
└── archive/                      # 历史文档
    ├── README.md                 # 归档说明
    ├── IMPLEMENTATION_SUMMARY.md # 实现完成总结
    ├── COMPLETION_CHECKLIST.md   # 完成清单
    └── ...（其他历史文档）
```

---

## 📖 文档说明

### INSTALLATION.md

**用途**：手把手配置虚拟环境、安装依赖、构建项目。

**内容**：
- uv 工具安装
- 虚拟环境创建与激活
- 包与驱动安装
- VS Code 配置
- `with_venv.sh` 使用
- colcon 构建
- 故障排查

### ARCHITECTURE.md

**用途**：深入理解统一节点架构、数据流与坐标系。

**内容**：
- 旧架构问题与新方案
- 逻辑架构图与对比
- 核心组件职责
- 数据流与消息频率
- 坐标系定义
- 参数表
- 启动方式与高级用法

### QUICK_REFERENCE.md

**用途**：快速查阅常用命令、参数与常见问题解决方案。

**内容**：
- 启动命令（完整/硬件/验证）
- 发布主题表
- 常用参数示例
- 验证步骤
- 常见问题与解决方案
- RViz 配置
- 系统架构简图
- 性能指标

### SUBMODULE_PATCH_REPRODUCTION.md

**用途**：复刻当前项目的第三方源码依赖，并维护本项目对 submodule 的 patch。

**内容**：
- 新环境拉取 submodule 和应用 patch
- 新增、更新第三方 submodule 的流程
- 检查第三方源码没有误提交到父仓库
- patch 冲突与恢复方法

### SENSOR_DEBUG_GUIDE.md

**用途**：单独调试 OAK-D 相机和 Livox MID360，避免主 README 变成命令清单。

**内容**：
- OAK-D 场景预设脚本、手动传参、话题检查
- OAK-D IMU 预融合和 RViz 检查
- MID360 网络配置、点云链路、FAST-LIO2 检查
- 传感器专项 ros2 bag 录制与常见问题

### 标准启动脚本

- [scripts/run_nav_stack.sh](../scripts/run_nav_stack.sh) — 导航栈模式化启动入口
- [scripts/run_complete_system.sh](../scripts/run_complete_system.sh) — 完整系统一键编排
- [scripts/run_oakd_unified.sh](../scripts/run_oakd_unified.sh) — OAK-D 统一节点入口
- [scripts/run_imu_fusion_tf.sh](../scripts/run_imu_fusion_tf.sh) — IMU 融合 + TF 广播入口

### 归档文档（archive/）

**用途**：保存历史文档以供参考或审计。

**包含**：
- 实现完成总结
- 项目清单
- 包重命名历史
- 旧的多层架构分析

---

## 🔗 相关链接

- [主 README](../README.md) — 项目概览与快速开始
- [OAK-D / MID360 独立调试指南](./SENSOR_DEBUG_GUIDE.md)
- [DepthAI 官方文档](https://docs.luxonis.com/)
- [ROS 2 官方文档](https://docs.ros.org/en/humble/)
- [uv 工具文档](https://docs.astral.sh/uv/)

---

## 💡 提示

- **第一次用？** 先读 [../README.md](../README.md)，再读 [INSTALLATION.md](./INSTALLATION.md)。
- **需要快速答案？** 查 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)。
- **想写代码？** 读 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解设计。
- **想直接启动？** 先用 [run_complete_system.sh](../scripts/run_complete_system.sh)。
- **遇到问题？** 先查 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md#常见问题与解决)，再查 [../README.md](../README.md#10-故障排查)。

---

最后更新：2026-05-19
