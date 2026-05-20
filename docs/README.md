# docs/ 目录说明

欢迎。本目录存放 **uav_vision_ws** 项目的技术文档。

---

## 文档导入点

- **首次来访？** 从 [INDEX.md](./INDEX.md) 开始。
- **需要快速命令？** 参考 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)。
- **想了解安装过程？** 查阅 [INSTALLATION.md](./INSTALLATION.md)。
- **需要深入技术细节？** 阅读 [ARCHITECTURE.md](./ARCHITECTURE.md)。
- **需要规划 PX4 导航与避障？** 阅读 [PX4_NAVIGATION_STRATEGY.md](./PX4_NAVIGATION_STRATEGY.md)。
- **需要逐层验证可行性？** 阅读 [DEBUG_VALIDATION_FLOW.md](./DEBUG_VALIDATION_FLOW.md)。
- **只调试 OAK-D 或 MID360？** 阅读 [SENSOR_DEBUG_GUIDE.md](./SENSOR_DEBUG_GUIDE.md)。
- **需要启动地面全向轮平台？** 阅读 [OMNI_BRINGUP.md](./OMNI_BRINGUP.md)。
- **需要复刻第三方源码依赖？** 阅读 [SUBMODULE_PATCH_REPRODUCTION.md](./SUBMODULE_PATCH_REPRODUCTION.md)。
- **想直接运行系统？** 使用 [../scripts/run_nav_stack.sh](../scripts/run_nav_stack.sh)，单设备调试按 [SENSOR_DEBUG_GUIDE.md](./SENSOR_DEBUG_GUIDE.md)。

---

## 文件列表

| 文件 | 说明 |
|------|------|
| **INDEX.md** | 文档导索与导航，推荐首先阅读 |
| **INSTALLATION.md** | 虚拟环境、依赖管理、项目构建详细步骤 |
| **ARCHITECTURE.md** | 统一节点架构、数据流、坐标系、高级用法 |
| **TF_FRAMES.md** | 坐标系、TF 树、传感器外参、全向轮下位机坐标开关与验收 |
| **PX4_NAVIGATION_STRATEGY.md** | PX4 导航与避障路线、nav 与 3D 方案对比 |
| **DEBUG_VALIDATION_FLOW.md** | 从环境、传感器、里程计、EKF、地图到 PX4 的逐层验证流程 |
| **SENSOR_DEBUG_GUIDE.md** | OAK-D / MID360 独立启动、话题检查、RViz 与 bag 调试 |
| **OMNI_BRINGUP.md** | 地面全向轮独立启动包、启动参数与话题说明 |
| **SUBMODULE_PATCH_REPRODUCTION.md** | 第三方 submodule + patch 复刻与维护流程 |
| **QUICK_REFERENCE.md** | 常用命令、参数示例、故障排查速查表 |
| **archive/** | 历史与参考文档（可选阅读） |
| **README.md** | 本文件 |

---

## 快速开始

1. 阅读 [INDEX.md](./INDEX.md)（5 分钟）
2. 按照 [INSTALLATION.md](./INSTALLATION.md) 配置环境（15 分钟）
3. 查看 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) 启动节点（5 分钟）
4. 优先使用标准脚本入口完成启动

---

## 根目录应该清理的文件

建议将以下文件移出根目录，方法：

1. 已集成到 docs/ 的文件（可删除）：

```bash
rm -f /home/nuc/Program/uav_vision_ws/QUICK_REFERENCE.md
```

2. 应存放在 docs/archive/ 的历史文件：

```bash
mkdir -p docs/archive
mv ARCHITECTURE_ANALYSIS.md docs/archive/
mv ARCHITECTURE_SUMMARY.md docs/archive/
mv ARCHITECTURE_INDEX.md docs/archive/
mv ARCHITECTURE_CHEATSHEET.md docs/archive/
mv IMPLEMENTATION_SUMMARY.md docs/archive/
mv COMPLETION_CHECKLIST.md docs/archive/
mv PACKAGE_RENAME_SUMMARY.md docs/archive/
mv UNIFIED_NODE_ARCHITECTURE.md docs/archive/
```

这样根目录保持清洁，只保留：

```
/
├── README.md                  # 主项目文档
├── docs/                      # 所有技术文档
├── src/                       # 源代码
├── scripts/                   # 启动脚本
└── ...
```

---

## 文档维护

所有新增文档请放在 `docs/` 目录下，并更新 [INDEX.md](./INDEX.md)。

旧版本或不再使用的文档应移至 `docs/archive/` 并在 [archive/README.md](./archive/README.md) 中记录。

---

## 相关链接

- [主 README](../README.md)
- [PX4 导航策略](./PX4_NAVIGATION_STRATEGY.md)
- [调试链路与逐层验证流程](./DEBUG_VALIDATION_FLOW.md)
- [OAK-D / MID360 独立调试指南](./SENSOR_DEBUG_GUIDE.md)
- [地面全向轮启动包说明](./OMNI_BRINGUP.md)
- [Submodule + Patch 复刻流程](./SUBMODULE_PATCH_REPRODUCTION.md)
- [导航栈统一启动脚本](../scripts/run_nav_stack.sh)
- [地面全向轮启动脚本](../scripts/run_omni_nav.sh)
- [OAK-D 包内场景预设脚本](../src/oakd_perception/scripts/README.md)
- [GitHub 上该项目](https://github.com)（如有）
- [DepthAI 官方](https://docs.luxonis.com/)
- [ROS 2 官方](https://docs.ros.org/)

---

最后更新：2026-05-19
