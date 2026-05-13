# uav_vision_ws（统一使用 .venv）

本项目约定所有 Python 相关命令都在项目虚拟环境 `.venv` 中执行。

## 1) 虚拟环境配置

### 1.1 初始化虚拟环境（只需一次）

本项目使用 `uv` 作为包管理工具。确保已安装 `uv`：

```bash
# 安装 uv（如还没安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

创建虚拟环境并安装依赖：

```bash
# 创建虚拟环境
uv venv .venv

# 安装本项目的 oakd_perception 包（可编辑模式）
uv pip install --python .venv/bin/python -e src/oakd_perception

# 安装 OAK-D 深度相机驱动
uv pip install --python .venv/bin/python depthai
```

### 1.2 激活/停用虚拟环境

**激活虚拟环境**（进入该环境后使用 Python 和 pip）：
```bash
source .venv/bin/activate
```

激活后，终端提示符会显示 `(.venv)` 前缀。

**停用虚拟环境**：
```bash
deactivit
```

或直接关闭终端。

### 1.3 虚拟环境中安装额外依赖

激活虚拟环境后，可直接使用 `pip` 安装包（无需指定 `--python` 参数）：

```bash
source .venv/bin/activate
pip install <package_name>
```

或者不激活，直接通过 `uv` 指定 Python 路径安装：

```bash
uv pip install --python .venv/bin/python <package_name>
```

### 1.4 查看虚拟环境中已安装的包

```bash
uv pip list --python .venv/bin/python
```

### 1.5 删除虚拟环境（清理）

如需重新初始化虚拟环境，先删除旧的，再按 1.1 重新创建：

```bash
rm -rf .venv
uv venv .venv
uv pip install --python .venv/bin/python -e src/oakd_perception
uv pip install --python .venv/bin/python depthai
```

### 1.6 在 VS Code 中配置解释器

本工作区已配置默认 Python 解释器为 `.venv/bin/python`。

确认可以在 VS Code 的命令面板（Ctrl+Shift+P）中选择 **Python: Select Interpreter** 并确认指向 `./.venv/bin/python`。

### 1.7 使用 with_venv.sh 包裹脚本

无需手动激活，直接使用 `scripts/with_venv.sh` 可在虚拟环境中执行任何命令：

```bash
# 示例 1：验证 depthai 已安装
./scripts/with_venv.sh python -c "import depthai; print(depthai.__version__)"

# 示例 2：在虚拟环境中运行任意命令
./scripts/with_venv.sh pip list
```

## 2) 构建 oakd_perception

```bash
./scripts/with_venv.sh colcon build --packages-select oakd_perception
```

## 3) 快速启动脚本（深度节点）

项目提供 4 个预配置的启动脚本，位置在 `scripts/` 目录下：

| 脚本 | 被动立体 | 主动立体 | 应用场景 |
|------|--------|--------|--------|
| `run_oakd_outdoor.sh` | ✓ | ✗ | 户外强光（低功耗） |
| `run_oakd_indoor.sh` | ✓ | ✓ | 室内弱光（最精度） |
| `run_oakd_balance.sh` | ✓ | ✓ | 通用平衡模式 |
| `run_oakd_active_max.sh` | ✗ | ✓ | 黑暗环境（最高密度） |

### 使用快速启动脚本

```bash
./scripts/run_oakd_balance.sh          # 平衡模式（推荐）
./scripts/run_oakd_outdoor.sh          # 户外模式
./scripts/run_oakd_indoor.sh           # 室内高精度模式
./scripts/run_oakd_active_max.sh       # 主动立体最大模式
```

每个脚本会自动：
1. 激活虚拟环境
2. 加载 ROS 2 环境
3. 读取对应的 YAML 配置文件
4. 启动点云发布节点

### 运行节点（手动模式）

你也可以手动启动节点，并传递自定义参数：

```bash
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node --ros-args \
  -p enable_passive_stereo:=true \
  -p enable_active_stereo:=true \
  -p ir_intensity:=800 \
  -p sampling_step:=2 \
  -p min_depth:=200 \
  -p max_depth:=5000
```

运行后验证节点是否已发布点云话题：

```bash
./scripts/with_venv.sh ros2 topic list
# 应看到 /oakd/points 在列表中
```

停止节点：在前台使用 Ctrl+C，或在后台运行时使用 `ps` 查到 PID 再 `kill`。

## 3.5) IMU 节点（6轴 IMU）

OAK-D 相机内置 6 轴 IMU（加速度计 + 陀螺仪），用于获取实时的运动和姿态数据。

### 启动 IMU 节点

```bash
# 使用虚拟环境启动 IMU 节点
./scripts/with_venv.sh ros2 run oakd_perception oakd_imu_node
```

### IMU 节点发布的话题

| 话题名 | 消息类型 | 发布频率 | 内容 |
|-------|---------|---------|------|
| `/oakd/imu` | `sensor_msgs/Imu` | 400 Hz | 加速度、角速度、协方差 |

### 让点云跟随 IMU 转动

如果你想让 RViz 里的点云跟着 OAK-D 的转动，需要让 IMU 节点发布动态 TF，并让点云和 IMU 使用同一个移动坐标系。

当前实现已经支持：

- IMU 节点发布 `map -> oakd_imu_link` 的动态 TF
- 点云节点使用 `oakd_imu_link` 作为 `frame_id`

RViz 里这样设置：

1. `Fixed Frame` 设为 `map`
2. 添加 `/oakd/points` 的 `PointCloud2`
3. 保持 IMU 节点运行

这样当 OAK-D 旋转时，点云会跟着旋转。

注意：这里的姿态是基于陀螺仪积分并用加速度做简单互补滤波，能够跟随转动，但长期 yaw 方向仍可能漂移。如果需要绝对朝向，后续要接磁力计、视觉里程计或外部姿态估计器。

### IMU 数据格式

IMU 消息包含以下数据：

```
linear_acceleration:    # 线性加速度 (m/s²)
  x: float
  y: float
  z: float

angular_velocity:       # 角速度 (rad/s)
  x: float
  y: float
  z: float

linear_acceleration_covariance: [9次元]
angular_velocity_covariance: [9次元]
```

### IMU 节点参数

| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `publish_tf` | bool | false | 是否发布 TF 变换 |
| `frame_id` | str | "oakd_imu" | IMU 坐标系名称 |

### IMU 节点启动示例

```bash
# 基础启动
./scripts/with_venv.sh ros2 run oakd_perception oakd_imu_node

# 在后台以 bag 形式记录数据
./scripts/with_venv.sh ros2 bag record /oakd/imu -o imu_data.bag

# 查看发布频率
./scripts/with_venv.sh ros2 topic hz /oakd/imu
# 应输出约 400Hz

# 实时查看 IMU 数据（5秒）
timeout 5s ./scripts/with_venv.sh ros2 topic echo /oakd/imu
```

### 同时运行深度和 IMU 节点

可在不同终端分别启动两个节点：

**终端 1 — 启动深度节点**：
```bash
./scripts/run_oakd_balance.sh
```

**终端 2 — 启动 IMU 节点**：
```bash
./scripts/with_venv.sh ros2 run oakd_perception oakd_imu_node
```

**终端 3 — 检查话题发布（可选）**：
```bash
./scripts/with_venv.sh ros2 topic list
# 应看到 /oakd/points 和 /oakd/imu
```

## 4) 可调节参数（深度节点）

oakd_depth_node 支持运行时动态配置，通过 ROS 2 参数系统实现。

### 立体深度模式参数

| 参数名 | 类型 | 默认值 | 范围 | 说明 |
|-------|------|-------|------|------|
| `enable_passive_stereo` | bool | true | - | 启用/禁用被动立体深度（基于纹理匹配） |
| `enable_active_stereo` | bool | false | - | 启用/禁用主动立体深度（红外投影仪） |
| `ir_intensity` | int | 1600 | 0-1600 | 红外照度强度（仅在主动立体启用时生效） |

### 点云过滤参数

| 参数名 | 类型 | 默认值 | 说明 |
|-------|------|-------|------|
| `sampling_step` | int | 2 | 采样间隔（1=无下采样，2=2x2下采样） |
| `min_depth` | int | 200 | 最小深度过滤阈值（毫米） |
| `max_depth` | int | 5000 | 最大深度过滤阈值（毫米） |

### 参数使用示例

```bash
# 高密度点云（室内高精度）
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node --ros-args \
  -p sampling_step:=1 \
  -p min_depth:=100 \
  -p max_depth:=5000

# 低功耗户外模式
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node --ros-args \
  -p enable_passive_stereo:=true \
  -p enable_active_stereo:=false \
  -p sampling_step:=2 \
  -p min_depth:=500 \
  -p max_depth:=8000

# 黑暗环境最大范围
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node --ros-args \
  -p enable_passive_stereo:=false \
  -p enable_active_stereo:=true \
  -p ir_intensity:=1600 \
  -p sampling_step:=1 \
  -p min_depth:=50 \
  -p max_depth:=10000
```

### 预设配置文件

项目提供 4 个预配置的 YAML 文件（位置：`src/oakd_perception/config/`），包含针对不同场景的参数组合：

| 配置文件 | 描述 |
|---------|------|
| `outdoor_low_power.yaml` | 户外低功耗：被动立体 ON，主动立体 OFF |
| `indoor_high_precision.yaml` | 室内高精度：混合立体，最密集点云 |
| `balanced_mode.yaml` | 平衡模式：混合立体，适用大多数场景 |
| `active_stereo_max.yaml` | 主动立体最大：黑暗场景，最高密度 |

## 5) 手动进入 venv（可选）

```bash
source .venv/bin/activate
```

说明：
- `scripts/with_venv.sh` 会先激活 `.venv`，再加载 ROS 环境，最后执行你传入的命令。
- VS Code 工作区已配置默认解释器为 `.venv/bin/python`，新开终端会优先使用 `.venv/bin`。

## 6) 在 RViz2 中查看点云

### 启动节点与 RViz

打开两个终端，分别运行：

**终端 1 — 启动点云发布节点**:
```bash
./scripts/with_venv.sh ./install/oakd_perception/bin/oakd_depth_node
```

**终端 2 — 启动 RViz2 可视化工具**:
```bash
./scripts/with_venv.sh rviz2
```

### 在 RViz 中添加点云显示

1. **设置 Fixed Frame**  
   在 RViz 顶部菜单栏左侧或左侧面板 `Global Options` 中，找到 `Fixed Frame` 并将其设置为 `oakd_link`。

2. **添加 PointCloud2 显示**  
   - 点击左下角 `Add` 按钮。
   - 在弹出菜单中选择 `By Topic` 选项卡。
   - 在话题列表中查找 `/oakd/points`，点击选中。
   - 确认数据类型为 `PointCloud2`，点击 `OK`（或双击话题名）。
   - 该显示会被添加到左侧 `Displays` 列表。

3. **调整可视化参数**（可选但推荐）  
   在左侧选中添加的 PointCloud2 显示项，然后在下方调整：
   - **Style**: 选择 `Points` 或 `Spheres`（Points 更轻量）
   - **Size (m)**: 试 0.01–0.05 之间（根据点云密度和观看距离调整）
   - **Color Transformer**: 根据消息内容选择
     - 若仅 XYZ：选 `FlatColor` 并手动选定颜色
     - 若含强度：选 `Intensity`
     - 若含 RGB：选 `RGB8`
   - **Decay Time**: 可设为 0.1–1.0s，使连续帧略微拖尾效果

### 显示效果验证

当节点正常发布、RViz 正确配置后，应在 3D 视图区看到点云点群。

若不显示点云，排查步骤：
- 在新终端验证 `/oakd/points` 话题存在：
  ```bash
  ./scripts/with_venv.sh ros2 topic list | grep /oakd/points
  ```
- 查看一条消息内容（应输出 PointCloud2 结构）：
  ```bash
  timeout 5s ./scripts/with_venv.sh ros2 topic echo /oakd/points
  ```
- 如果话题缺失，检查节点是否在运行：
  ```bash
  ps -ef | grep oakd_depth_node | grep -v grep
  ```
- 若无进程，重新启动节点：
  ```bash
  ./scripts/with_venv.sh ./install/oakd_perception/bin/oakd_depth_node
  ```

## 7) 故障排除

### 常见问题

**问题：节点启动失败，提示"找不到模块"**
```
ModuleNotFoundError: No module named 'depthai'
```
**解决**：确保虚拟环境已正确初始化：
```bash
./scripts/with_venv.sh python -c "import depthai; print(depthai.__version__)"
```
若输出版本号，则 depthai 已正确安装。

**问题：运行快速启动脚本提示"权限被拒绝"**
```
Permission denied
```
**解决**：给脚本添加执行权限：
```bash
chmod +x scripts/run_oakd_*.sh
```

**问题：点云参数不生效**
```bash
# 正确用法
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node --ros-args -p key:=value

# 错误用法（不会被识别）
./scripts/with_venv.sh ./.venv/bin/oakd_depth_node -p key:=value
```
**注意**：必须在 `--ros-args` 之后才能使用 `-p` 参数。

**问题：RViz 中看不到点云**

排查顺序：
1. 检查节点是否在运行：`ps aux | grep oakd_depth_node`
2. 检查话题是否存在：`ros2 topic list | grep /oakd/points`
3. 检查 RViz 的 Fixed Frame 是否设为 `oakd_link`
4. 检查点云密度：`timeout 1s ros2 topic hz /oakd/points`（应该显示约 20Hz）

### IMU 节点故障排除

**问题：IMU 节点启动失败，提示"can't find device"**

**排查步骤**：
1. 确保 OAK-D 相机已连接到 USB 端口：
   ```bash
   ./scripts/with_venv.sh python -c "import depthai as dai; print(dai.Device().getCameraSensorNames())"
   ```
2. 若无输出或 USB 连接错误，检查硬件连接或 USB 驱动程序

**问题：IMU 数据不连续或空白**

**解决**：
1. 检查 IMU 话题是否在发布：
   ```bash
   ./scripts/with_venv.sh ros2 topic hz /oakd/imu
   # 应输出约 400 Hz
   ```
2. 若显示 0 Hz 或无输出，重启 IMU 节点：
   ```bash
   pkill oakd_imu_node
   ./scripts/with_venv.sh ros2 run oakd_perception oakd_imu_node
   ```

**问题：IMU 节点与深度节点冲突**

**原因**：两个节点同时访问同一 OAK-D 设备会导致冲突。

**解决**：使用虚拟环境隔离运行，或者创建联合启动文件（待实现）：
```bash
# 确保只有一个节点实例在运行
pkill oakd_imu_node
pkill oakd_depth_node

# 然后分别启动
./scripts/with_venv.sh ros2 run oakd_perception oakd_depth_node
./scripts/with_venv.sh ros2 run oakd_perception oakd_imu_node
```

### 日志输出示例

正常启动时，节点应输出：
```
[INFO] [timestamp] [oakd_pointcloud_node]: Passive Stereo: ON
[INFO] [timestamp] [oakd_pointcloud_node]: Active Stereo:  OFF
[INFO] [timestamp] [oakd_pointcloud_node]: OAK-D 点云驱动节点已启动 [深度模式: 被动立体]，正在发布点云...
```

## 8) 项目文件结构

```
uav_vision_ws/
├── src/oakd_perception/
│   ├── oakd_perception/
│   │   ├── oakd_depth_node.py           # 点云发布节点主文件
│   │   └── oakd_imu_node.py             # IMU 6轴传感器节点
│   ├── config/
│   │   ├── outdoor_low_power.yaml       # 户外低功耗配置
│   │   ├── indoor_high_precision.yaml   # 室内高精度配置
│   │   ├── balanced_mode.yaml           # 平衡模式配置
│   │   └── active_stereo_max.yaml       # 主动立体最大配置
│   ├── setup.py
│   └── package.xml
├── scripts/
│   ├── with_venv.sh                     # 虚拟环境包裹器
│   ├── run_oakd_outdoor.sh              # 户外启动脚本
│   ├── run_oakd_indoor.sh               # 室内启动脚本
│   ├── run_oakd_balance.sh              # 平衡模式启动脚本
│   └── run_oakd_active_max.sh           # 主动立体启动脚本
├── install/                             # colcon 编译输出目录
├── build/                               # colcon 编译中间目录
├── .venv/                               # Python 虚拟环境
└── README.md                            # 本文件
```
