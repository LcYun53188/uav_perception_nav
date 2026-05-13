# 快速参考

## 参数说明

| 参数 | 类型 | 范围 | 默认值 | 说明 |
|-----|------|------|-------|------|
| `enable_passive_stereo` | bool | true/false | true | 启用/禁用被动立体（左右相机纹理匹配） |
| `enable_active_stereo` | bool | true/false | false | 启用/禁用主动立体（IR投影仪） |
| `ir_intensity` | int | 0-1600 | 1600 | IR投影强度（仅当主动立体启用时有效） |

---

## 预置模式

### 1️⃣ **户外飞行** - 低功耗
```bash
./scripts/run_oakd_outdoor.sh
```
- 配置: `passive:ON, active:OFF`
- 特点: 低功耗、低热量、不受室外IR干扰
- 适用: UAV户外巡检、无人机系统

---

### 2️⃣ **室内SLAM** - 平衡精度
```bash
./scripts/run_oakd_balance.sh
```
- 配置: `passive:ON, active:ON, ir=800`
- 特点: 建图精度高、点云稠密、功耗中等
- 适用: 室内导航、建图、避障

---

### 3️⃣ **弱光/黑暗** - 纯主动
```bash
./scripts/run_oakd_active_max.sh
```
- 配置: `passive:OFF, active:ON, ir=1600`
- 特点: 完全依赖IR、不需要可见光纹理、点云最稠密
- 适用: 夜间操作、隧道、地下室

---

### 4️⃣ **室内混合** - 最高精度
```bash
./scripts/run_oakd_indoor.sh
```
- 配置: `passive:ON, active:ON, ir=1000`
- 特点: 主被观点互补、精度最高、点云100%有效
- 适用: 精密测量、高精度SLAM

---

## 命令行快速启动

```bash
# 最小化（仅被动，默认）
./scripts/with_venv.sh ros2 run oakd_perception oakd_depth_node

# 启用主动立体（中强度）
./scripts/with_venv.sh ros2 run oakd_perception oakd_depth_node \
  --ros-args -p enable_active_stereo:=true -p ir_intensity:=1000

# 完整控制
./scripts/with_venv.sh ros2 run oakd_perception oakd_depth_node \
  --ros-args \
  -p enable_passive_stereo:=true \
  -p enable_active_stereo:=true \
  -p ir_intensity:=800
```

---

## 配置文件方法

```bash
# 使用YAML配置文件启动
./scripts/with_venv.sh ros2 run oakd_perception oakd_depth_node \
  --ros-args --params-file src/oakd_perception/config/balanced_mode.yaml
```

可用配置文件:
- `config/outdoor_low_power.yaml` - 户外低功耗
- `config/balanced_mode.yaml` - 平衡模式
- `config/indoor_high_precision.yaml` - 室内高精度
- `config/active_stereo_max.yaml` - 纯主动最强

---

## 运行时查看状态

```bash
# 查看参数值
ros2 param get /oakd_depth_node enable_active_stereo

# 列出所有参数
ros2 param list /oakd_depth_node

# 实时修改参数（不需要重启）
ros2 param set /oakd_depth_node ir_intensity 1200
```

---

## 相关话题

- `/oakd/points` - PointCloud2 格式的三维点云（发布频率 20Hz）
- 分辨率: 约160x100 点（已优化降采样）
- 坐标系: `oakd_link`（相机坐标系）
