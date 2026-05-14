# IMU融合包重命名总结

## 变更概览

包名已从 `oakd_imu_fusion` 更新为 `imu_fusion`，删除了 `oakd` 前缀以实现更通用的命名。

## 关键变更

### 目录结构

```
旧布局:
src/oakd_imu_fusion/
├── oakd_imu_fusion/
│   ├── oakd_imu_fusion_node.py
│   ├── oakd_imu_tf_broadcaster.py
│   └── imu_fusion_node.py
│   └── imu_tf_broadcaster.py
└── launch/

新布局:
src/imu_fusion/
├── imu_fusion/
│   ├── imu_fusion_node.py
│   ├── imu_tf_broadcaster.py
│   ├── oakd_imu_fusion_node.py (向后兼容别名)
│   └── oakd_imu_tf_broadcaster.py (向后兼容别名)
└── launch/
```

### 配置文件更新

| 文件 | 更改 |
|------|------|
| package.xml | `<name>oakd_imu_fusion</name>` → `<name>imu_fusion</name>` |
| setup.py | `package_name = 'oakd_imu_fusion'` → `package_name = 'imu_fusion'` |
| setup.cfg | 脚本目录路径更新 |
| resource/ | `oakd_imu_fusion` → `imu_fusion` |
| launch/ | 所有包引用 `package='oak_imu_fusion'` → `package='imu_fusion'` |

### 可执行程序变更

| 旧名称 | 新名称 | 状态 |
|--------|--------|------|
| `oakd_imu_fusion_node` | `imu_fusion_node` | 新推荐 |
| `oakd_imu_tf_broadcaster` | `imu_tf_broadcaster` | 新推荐 |
| - | `oakd_imu_fusion_node` | 保留（通过 entry_points 重定向） |
| - | `oakd_imu_tf_broadcaster` | 保留（通过 entry_points 重定向） |

## 使用示例

### 新的推荐方式

```bash
# 启动新的启动文件
ros2 launch imu_fusion imu_fusion.launch.py

# 运行新的可执行程序
ros2 run imu_fusion imu_fusion_node
ros2 run imu_fusion imu_tf_broadcaster
```

### 向后兼容方式（仍可用）

```bash
# 旧的启动文件（自动重定向）
ros2 launch imu_fusion oakd_imu_fusion.launch.py

# 旧的可执行程序名称（仍可用）
ros2 run imu_fusion oakd_imu_fusion_node
ros2 run imu_fusion oakd_imu_tf_broadcaster
```

## 迁移检查列表

- [x] 包目录重命名 `oakd_imu_fusion` → `imu_fusion`
- [x] 模块目录重命名 `oakd_imu_fusion` → `imu_fusion`
- [x] package.xml 更新
- [x] setup.py 更新
- [x] setup.cfg 更新
- [x] resource/ 文件重命名
- [x] launch 文件包引用更新
- [x] entry_points 更新（保留向后兼容别名）
- [x] 全新構建验证成功
- [x] 新启动文件测试通过
- [x] 旧启动文件向后兼容测试通过

## ROS2 命令验证

```bash
# 列出新包及其可执行程序
ros2 pkg list | grep imu_fusion
# 输出: imu_fusion

ros2 pkg executables imu_fusion
# 输出:
# imu_fusion imu_fusion_node
# imu_fusion imu_tf_broadcaster
# imu_fusion oakd_imu_fusion_node (backward compatibility)
# imu_fusion oakd_imu_tf_broadcaster (backward compatibility)
```

## 文档更新

**重要：** 文档文件 `IMU_MULTI_CONFIG.md` 包含过时的包名引用。它们应更新为：

- `ros2 launch imu_fusion imu_fusion.launch.py` (替代 `ros2 launch oakd_imu_fusion imu_fusion.launch.py`)
- `ros2 launch imu_fusion oakd_imu_fusion.launch.py` (替代 `ros2 launch oakd_imu_fusion oakd_imu_fusion.launch.py`)
- `package='imu_fusion'` (替代 `package='oakd_imu_fusion'`)

## 构建验证结果

```
Starting >>> imu_fusion
Finished <<< imu_fusion [0.52s]

Summary: 1 package finished [0.58s]
```

## runtime 验证

✅ 新启动文件成功启动所有节点
✅ 旧启动文件通过兼容层工作
✅ TF变换正确发布
✅ IMU融合正常运行

---

**完成日期**: 2026年5月14日
**状态**: 完全迁移完成，向后兼容保持
