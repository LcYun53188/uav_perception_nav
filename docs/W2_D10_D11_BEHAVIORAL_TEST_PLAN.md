# W2-D10-D11 行为验证测试计划

**目标**: 在完整导航栈 (nav_stack.launch.py) 上验证 4 种关键行为

**预计工期**: D10-D11 (2 天, 每天 4 小时)  
**验收标准**: 4/4 测试通过

---

## 🎯 测试矩阵

### Test 1: 自动启动与飞行 (20 分钟)

**目的**: 验证 IDLE → ARM → OFFBOARD → FLYING 完整流程

**环境**:
- IPC 安装在无人机上
- PX4 SITL 或实际飞控正常运行
- 导航栈启动: `ros2 launch uav_bringup nav_stack.launch.py`

**操作流程**:
```
1. 系统启动: nav_stack.launch.py 启动所有节点 (13+ 节点)
   验证: ros2 node list (应列出所有节点)

2. RViz 设置目标: 
   - 点击 Nav2 Goal 按钮
   - 在仿真环境（无障碍）中点击某个位置
   
3. 观察状态机转移:
   - 通过 ros2 echo /nav/safety_status 监听安全评分
   - 通过 roslog 输出监听 SM 日志:
     [SM] State transition: IDLE → ARM
     [SM] State transition: ARM → OFFBOARD
     [SM] State transition: OFFBOARD → FLYING
   
4. 验证导航执行:
   - PX4 速度命令应流向无人机 (/fmu/in/trajectory_setpoint)
   - 无人机应开始按规划路径移动

5. 无人机到达目标点后自动停止
   
验收标准:
  ✅ ARM 命令成功 (PX4 armed_state = 1)
  ✅ OFFBOARD 模式激活 (PX4 nav_state = 14)
  ✅ 轨迹跟踪执行 (实际速度 ≈ 规划速度)
  ✅ 到达目标点 (距离误差 < 0.5m)
```

**故障处理**:
- 如果 ARM 超时 (5s): 检查 PX4 是否就绪
- 如果 OFFBOARD 入场失败: 检查是否有硬件故障或 RC 接管
- 如果规划器输出为 0: 检查 DWB 配置和成本地图

---

### Test 2: 多源故障应急 (20 分钟)

**目的**: 验证 FLYING → EMERGENCY 触发和容错处理

**场景 A: PointCloud 丢失**
```
1. 系统启动并进入 FLYING 状态

2. 停止 OAK-D:
   killall rgbd_launch  # 或 ps aux | grep oakd... | kill
   
3. 观察 NavSafety 反应:
   - /nav/safety_status 应升至 CRITICAL (2)
   - 日志: [SafetyMonitor] CRITICAL | PC:2 ...
   
4. 验证状态机应急:
   - [SM] ... FLYING → EMERGENCY
   - 应发送 LAND 命令
   - /nav/cmd_vel 应变为 (0, 0, 0) 或降落速度
   
5. 重启 OAK-D:
   ros2 launch oakd_perception oakd_unified.launch.py
   
6. 等待系统恢复到 IDLE/LANDED
   
验收标准:
  ✅ PC 丢失 → safety_level=CRITICAL
  ✅ CRITICAL → EMERGENCY 转移成功
  ✅ 应急着陆开始 (alt 下降)
  ✅ 系统恢复后可重新任务
```

**场景 B: TF 树失败 (EKF 崩溃)**
```
1. 系统启动并进入 FLYING 状态

2. 停止 EKF:
   kill $(ros2 node info /ekf_node | grep PID | awk '{print $NF}')
   
3. 观察反应:
   - TF 查询应失败 (map → base_link 不可用)
   - /nav/safety_status 应升至 CRITICAL
   - [SM] FLYING → EMERGENCY
   
4. 重启 EKF:
   ros2 launch uav_bringup ekf_launch.py
   
5. 观察恢复
   
验收标准:
  ✅ TF 故障检测 (timeout < 0.5s)
  ✅ 自动应急着陆
  ✅ 恢复后可重新任务
```

**场景 C: 命令超时 (规划器掉线)**
```
1. 系统启动并进入 FLYING 状态

2. 停止 DWB 规划器:
   kill $(ros2 node info /dwb_bridge | grep PID | awk '{print $NF}')
   
3. 观察:
   - /nav/cmd_vel 停止发送 (旧消息在 10s 后过期)
   - 等待 10s...
   - [SM] Command timeout (>10.0s), triggering EMERGENCY
   - /fmu/in/trajectory_setpoint 应变为停止速度
   
4. 重启规划器:
   ros2 launch nav_planning dwb_local_planner ...
   
验收标准:
  ✅ 检测到超时 (≤ 10.5s)
  ✅ 自动转为应急着陆
  ✅ 恢复后可重新任务
```

---

### Test 3: 安全生命周期 (15 分钟)

**目的**: 验证 LANDED 恢复和多次起飞

**操作流程**:
```
1. Test 1 的目标点到达后, 系统自动转为 LANDED

2. 重新输入 RViz 目标:
   - 确认转移: LANDED → IDLE → ARM → OFFBOARD → FLYING
   - 应顺利开始第二次任务
   
3. 重复 3 次起飞/着陆周期
   - 验证状态机不会卡顿或内存泄漏
   
4. 观察 PX4 状态反馈:
   - 每个周期的 armed_state、nav_state 应正确
   
验收标准:
  ✅ 3 个完整周期无异常
  ✅ 每次转移日志正确
  ✅ 内存/CPU 负载稳定
```

---

### Test 4: 人工紧急停驻 (15 分钟)

**目的**: 验证硬件 E-STOP 和应急信号处理

**场景 A: 软件紧急信号**
```
1. 系统飞行中

2. 发送应急信号:
   ros2 topic pub /nav/emergency std_msgs/Bool 'data: true'
   
3. 验证反应:
   - 立即进入 EMERGENCY
   - 发送 LAND 命令
   - 无延迟

验收标准:
  ✅ 应急响应 < 100ms
  ✅ 着陆动作立即执行
```

**场景 B: 安全监视器 CRITICAL 信号**
```
1. 通过参数修改降低安全阈值:
   ros2 param set /safety_monitor pc_timeout_sec 0.5  # 极低容限
   
2. 等待 PointCloud 超时 (< 0.5s)
   - /nav/safety_status 自动升至 CRITICAL
   - [SM] FLYING → EMERGENCY
   
3. 恢复参数:
   ros2 param set /safety_monitor pc_timeout_sec 2.0

验收标准:
  ✅ CRITICAL 触发应急 < 100ms
  ✅ 不依赖用户干预
```

---

## 📊 验收标准汇总

| 测试 | 关键指标 | 通过标准 |
|-----|--------|--------|
| Test 1 | 自动启动到飞行 | 4 个转移 + 目标到达 |
| Test 2A | PointCloud 故障恢复 | 检测 < 2.5s + 应急 + 恢复 |
| Test 2B | TF 故障恢复 | 检测 < 0.7s + 应急 + 恢复 |
| Test 2C | 命令超时恢复 | 检测 ≤ 10.5s + 应急 + 恢复 |
| Test 3 | 生命周期健壮性 | 3 周期无异常 + 日志正确 |
| Test 4A | 软件应急 | 响应 < 100ms |
| Test 4B | 安全应急 | 响应 < 100ms + 自动恢复 |

**总体通过标准**: 7/7 子测试通过 = ✅ W2 PASS

---

## 🛠️ 测试工具和脚本

### 脚本 1: 完整导航栈启动

```bash
#!/bin/bash
# launch_full_stack.sh

echo "[*] Sourcing ROS2 environment..."
source /home/nuc/Program/uav_vision_ws/install/setup.bash

echo "[*] Killing any existing nodes..."
killall -9 ros2 2>/dev/null || true
sleep 1

echo "[*] Launching full navigation stack..."
ros2 launch uav_bringup nav_stack.launch.py &
LAUNCH_PID=$!

sleep 3

echo "[*] Monitoring nodes..."
ros2 node list

echo "[*] Monitoring topics..."
ros2 topic list | grep -E "(cmd_vel|safety_status|emergency|vehicle_status)"

echo "[*] Stack launched. Press Ctrl+C to stop."
wait
```

### 脚本 2: 故障注入和恢复

```bash
#!/bin/bash
# test_fault_injection.sh

# 故障 1: 停止 OAK-D
echo "[TEST 1] Stopping OAK-D..."
pkill -f "oakd_unified" &
sleep 5
echo "[TEST 1] Restarting OAK-D..."
ros2 launch oakd_perception oakd_unified.launch.py &
sleep 3

# 故障 2: 停止 EKF
echo "[TEST 2] Stopping EKF..."
pkill -f "ekf_node" &
sleep 5
echo "[TEST 2] Restarting EKF..."
ros2 launch uav_bringup ekf_launch.py &
sleep 3

# 故障 3: 停止 DWB
echo "[TEST 3] Stopping DWB..."
pkill -f "dwb_bridge" &
sleep 12  # 等待超时
echo "[TEST 3] Restarting DWB..."
ros2 run nav_planning dwb_bridge &
sleep 3
```

### 脚本 3: 状态监控仪表板

```bash
#!/bin/bash
# monitor_dashboard.sh

echo "State Machine Dashboard (Ctrl+C to exit)"
echo ""

while true; do
  clear
  echo "=== Navigation Stack Health === $(date +%H:%M:%S)"
  echo ""
  
  echo "Nodes:"
  ros2 node list 2>/dev/null | wc -l
  echo ""
  
  echo "Safety Status:"
  ros2 topic echo -n 1 /nav/safety_status 2>/dev/null | grep data || echo "N/A"
  echo ""
  
  echo "Recent SM Logs:"
  ros2 topic echo -n 1 /rosout 2>/dev/null | grep "\[SM\]" | tail -3 || echo "No logs"
  echo ""
  
  sleep 1
done
```

---

## 📋 执行检查清单 (D10-D11)

### D10 (第一天)

- [ ] 09:00 - 环境准备
  - [ ] IPC 配置和网络连接
  - [ ] PX4 SITL / 实飞控就绪
  - [ ] RViz 安装并配置
  
- [ ] 10:00 - Test 1 执行
  - [ ] 启动完整导航栈
  - [ ] 验证 13+ 节点启动
  - [ ] 自动启动 → 飞行
  - [ ] 记录日志

- [ ] 11:30 - Test 2 执行 (多源故障)
  - [ ] PointCloud 丢失恢复
  - [ ] TF 树故障恢复
  - [ ] 命令超时恢复
  - [ ] 记录所有故障场景

- [ ] 13:00 午休

- [ ] 14:00 - Test 3 执行 (生命周期)
  - [ ] 3 个完整起飞/着陆周期
  - [ ] 监控内存/CPU
  - [ ] 验证日志正确性

### D11 (第二天)

- [ ] 09:00 - Test 4 执行 (应急处理)
  - [ ] 软件应急信号
  - [ ] 安全监视器 CRITICAL
  - [ ] 响应时间测量

- [ ] 10:30 - 数据收集和分析
  - [ ] 汇总所有日志
  - [ ] 计算统计指标 (响应时间、恢复时间等)
  - [ ] 生成验收报告

- [ ] 12:00 - 最终验收
  - [ ] 7/7 子测试确认
  - [ ] 文档完成
  - [ ] 归档所有测试数据

---

## 📊 验收报告模板

```
# W2-D10-D11 行为验证测试报告

## 执行日期
[D10-D11 实际日期]

## 测试环境
- IPC: [型号和规格]
- PX4: [SITL/实飞, 版本]
- ROS2: [版本]
- 导航栈版本: W2-D8-D9 完成版

## 测试结果

### Test 1: 自动启动与飞行
- 结果: [PASS/FAIL]
- ARM 延迟: [时间]
- OFFBOARD 延迟: [时间]
- 目标到达误差: [距离]

### Test 2: 多源故障应急
- PointCloud 故障抗性: [PASS/FAIL], 检测时间: [时间]
- TF 故障抗性: [PASS/FAIL], 检测时间: [时间]
- 命令超时恢复: [PASS/FAIL], 检测时间: [时间]

### Test 3: 生命周期
- 3 周期完成: [PASS/FAIL]
- 内存泄漏: [无/有], 增长量: [MB]
- CPU 峰值: [%]

### Test 4: 应急处理
- 软件应急响应: [时间] (目标: < 100ms)
- 安全应急响应: [时间] (目标: < 100ms)

## 总体验收
[✅ PASS / ❌ FAIL]

## 备注
[任何特殊情况或发现]
```

---

## 🎓 验收后交付件

- [ ] W2-D10-D11 测试报告 (markdown)
- [ ] 所有测试日志 (rosbag 或文本)
- [ ] 状态机行为视频 (可选)
- [ ] 最终系统集成验收清单

---

*W2-D10-D11 行为验证测试框架完成*  
*下一步: D10 上午 09:00 开始执行*
