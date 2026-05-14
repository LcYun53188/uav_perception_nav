# OAK-D 深度模式脚本说明

本目录集中放置深度相机节点的四个启动脚本，用于在不同环境下快速切换立体模式。

## 脚本列表

- run_oakd_outdoor.sh
  - 场景: 户外强光、低功耗
  - 配置: 仅被动立体
  - 参数:
    - enable_passive_stereo=true
    - enable_active_stereo=false

- run_oakd_balance.sh
  - 场景: 通用默认、SLAM建图
  - 配置: 被动 + 主动立体
  - 参数:
    - enable_passive_stereo=true
    - enable_active_stereo=true
    - ir_intensity=800

- run_oakd_indoor.sh
  - 场景: 室内弱光
  - 配置: 被动 + 主动立体
  - 参数:
    - enable_passive_stereo=true
    - enable_active_stereo=true
    - ir_intensity=1000

- run_oakd_active_max.sh
  - 场景: 高精度优先
  - 配置: 仅主动立体
  - 参数:
    - enable_passive_stereo=false
    - enable_active_stereo=true
    - ir_intensity=1600

## 使用方法

方式1：从工作空间根目录直接调用（推荐）

```bash
./scripts/run_oakd_outdoor.sh
./scripts/run_oakd_balance.sh
./scripts/run_oakd_indoor.sh
./scripts/run_oakd_active_max.sh
```

方式2：直接调用包内脚本

```bash
./src/oakd_perception/scripts/run_oakd_outdoor.sh
./src/oakd_perception/scripts/run_oakd_balance.sh
./src/oakd_perception/scripts/run_oakd_indoor.sh
./src/oakd_perception/scripts/run_oakd_active_max.sh
```

说明：
- 根目录 scripts 下同名脚本是兼容入口，会转发到本目录脚本。
- 脚本通过 scripts/with_venv.sh 启动，自动加载 .venv 与 ROS 环境。

## 前置条件

1. 已在工作空间根目录创建虚拟环境

```bash
uv venv .venv
```

2. 已安装依赖并完成构建（至少 oakd_perception）

```bash
./scripts/with_venv.sh colcon build --packages-select oakd_perception
```

3. OAK-D 设备已正确连接

## 快速排障

- 查看节点是否在运行

```bash
ps aux | grep oakd_depth_node
```

- 查看点云话题是否发布

```bash
./scripts/with_venv.sh ros2 topic list | grep /oakd/points
```

- 查看点云频率

```bash
./scripts/with_venv.sh ros2 topic hz /oakd/points
```

- 若设备被占用，先清理旧进程再重试

```bash
pkill -9 -f oakd_ 2>/dev/null || true
sleep 1
```
