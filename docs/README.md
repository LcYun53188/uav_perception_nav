# docs/ 目录说明

欢迎。本目录存放 **uav_vision_ws** 项目的技术文档。

---

## 文档导入点

- **首次来访？** 从 [INDEX.md](./INDEX.md) 开始。
- **需要快速命令？** 参考 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)。
- **想了解安装过程？** 查阅 [INSTALLATION.md](./INSTALLATION.md)。
- **需要深入技术细节？** 阅读 [ARCHITECTURE.md](./ARCHITECTURE.md)。
- **想直接运行系统？** 使用 [../scripts/run_complete_system.sh](../scripts/run_complete_system.sh)、[../scripts/run_oakd_unified.sh](../scripts/run_oakd_unified.sh)、[../scripts/run_imu_fusion_tf.sh](../scripts/run_imu_fusion_tf.sh)。

---

## 文件列表

| 文件 | 说明 |
|------|------|
| **INDEX.md** | 文档导索与导航，推荐首先阅读 |
| **INSTALLATION.md** | 虚拟环境、依赖管理、项目构建详细步骤 |
| **ARCHITECTURE.md** | 统一节点架构、数据流、坐标系、高级用法 |
| **QUICK_REFERENCE.md** | 常用命令、参数示例、故障排查速速表 |
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
- [完整系统启动脚本](../scripts/run_complete_system.sh)
- [OAK-D 统一节点脚本](../scripts/run_oakd_unified.sh)
- [IMU 融合 + TF 广播脚本](../scripts/run_imu_fusion_tf.sh)
- [GitHub 上该项目](https://github.com)（如有）
- [DepthAI 官方](https://docs.luxonis.com/)
- [ROS 2 官方](https://docs.ros.org/)

---

最后更新：2026-05-14
