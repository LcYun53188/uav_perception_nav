# 2D过渡方案 — 完整实现路线

**目标**: 将APF原型规划器替换为Nav2 DWB 2D控制器，保留VINS-Fusion+robot_localization定位层
**周期**: 3周 | **风险**: 中等 | **自包含启动**: 必需

---

## ① 整改清单（优先级 + 影响面）

### P0 级 — 启动层割裂（阻塞）
| 项目 | 文件 | 改动内容 | 影响 | 原因 |
|------|------|---------|------|------|
| **启动自包含** | uav_bringup/launch/nav_stack.launch.py | 纳入OAK-D+VINS+EKF节点 | 🔴 高（硬件+仿真） | 当前需多窗口启动，自动化测试阻塞 |
| **节点启动超时** | uav_bringup/launch/*.py | 添加expect_process节点健康检查 | 🟡 中 | 无TF/topic就绪校验 |

### P1 级 — 规划+安全+桥接（生效）
| 项目 | 文件 | 改动内容 | 影响 | 原因 |
|------|------|---------|------|------|
| **局部规划器替换** | nav_planning/local_planner.py | 从APF→Nav2 DWB适配层 | 🔴 高（3D→2D） | APF无成熟避障+无目标规划 |
| **安全监视器扩展** | nav_safety/safety_monitor.py | +TF延迟检查+EKF健康检查+PX4状态 | 🟠 高（安全） | 仅点云阈值不足 |
| **PX4桥接状态机** | px4_comm_bridge/control_bridge.py | 实现armed/offboard/hold转移+自启动 | 🟠 高（关键路径） | pose_cb空腹+无状态封装 |

### P2 级 — 测试+精细化（验证）
| 项目 | 文件 | 改动内容 | 影响 | 原因 |
|------|------|---------|------|------|
| **行为验证测试** | uav_bringup/test/test_nav_stack_integration.py | 添加避障验证+目标到达+紧急停止 | 🟡 高（验收） | 仅检查topic存在性 |
| **DWB配置调优** | nav_planning/config/dwb_params.yaml（新) | 载权重/前向模型/采样参数 | 🟡 中 | 需与OAK-D帧率+PX4延迟适配 |

---

## ② 文件级实现路线图

### 阶段1: 启动自包含（Week 1, 前3天）
**目标**: nav_stack.launch.py 一键拉起全栈

```
src/uav_bringup/launch/nav_stack.launch.py
  ├─ [新增] IncludeLaunchDescription → oakd_perception/launch/oakd_rgb_imu.launch.py
  ├─ [新增] IncludeLaunchDescription → oakd_imu_fusion/launch/imu_fusion.launch.py
  ├─ [新增] IncludeLaunchDescription → vins_fusion_ros2/launch/oakd_vins.launch.py
  ├─ [改]  IncludeLaunchDescription → ekf_launch.py (enable_gps:=True参数)
  ├─ [保持] local_map_builder node
  ├─ [保持] local_planner node (临时用APF) 
  ├─ [保持] safety_monitor node
  └─ [保持] px4_bridge_node (control_bridge)
```

**实现行动**:
1. 复制 `ekf_launch.py` 路径和参数到 `nav_stack.launch.py`
2. 为OAK-D/IMU/VINS添加3个 `IncludeLaunchDescription`
3. 在所有nodes之前添加 `Compose([...wait_for_tf('vins/tf')])` 依赖
4. 测试: `ros2 launch uav_bringup nav_stack.launch.py` 启后30s内所有话题活跃

**验收标准**:
- `ros2 topic list | wc -l` ≥ 15 (perception + localization + planning + control)
- `ros2 node list | wc -l` = 11 (OAK-D + IMU + VINS + EKF + map + planner + safety + bridge + monitor)

---

### 阶段2A: 规划器替换 DWB（Week 1, 后2天 + Week 2）
**目标**: Nav2 DWB > /nav/cmd_vel，测试OAK-D延迟兼容性

**关键路径**:

#### Step 2A-1: 创建 DWB 适配层（Day 4-5）
```
src/nav_planning/dwb_bridge.py [新建]
  ├─ 继承 Node
  ├─ 订阅: /local_map/occupancy (OccupancyGrid)
  ├─ 订阅: /tf (TF树, 获取robot_pose_in_odom)
  ├─ 订阅: /nav/goal_pose (PoseStamped)  [来源: 手动or nav2_simple_commander模拟]
  ├─ 初始化: nav2_core.dwb_local_planner + controller_server内部对象
  ├─ 处理: occupancy_grid → Costmap2D → local_planner.computeVelocityCommands()
  └─ 发布: /nav/cmd_vel (TwistStamped)
```

**代码骨架**:
```python
from nav2_core.dwb_local_planner import DWBLocalPlanner
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import TwistStamped, PoseStamped
from tf2_ros import Buffer, TransformListener

class DWBBridge(Node):
    def __init__(self):
        super().__init__('dwb_bridge')
        self.planner = DWBLocalPlanner()
        self.costmap = Costmap2D(...)  # 从OccupancyGrid初始化
        
    def grid_callback(self, msg: OccupancyGrid):
        self.costmap.updateFromOG(msg)
        
    def goal_callback(self, msg: PoseStamped):
        vel = self.planner.computeVelocityCommands(
            pose=self.robot_pose, 
            vel=self.robot_vel, 
            goal=msg.pose
        )
        self.cmd_pub.publish(vel)
```

**DWB配置** (nav_planning/config/dwb_local_planner.yaml 新建):
```yaml
DWBLocalPlanner:
  min_vel_x: -0.1  # 支持后退
  max_vel_x: 2.0   # OAK-D + PX4 can handle up to 2m/s
  min_vel_y: -1.0
  max_vel_y: 1.0
  min_vel_theta: -1.57  # π/2 rad/s
  max_vel_theta: 1.57
  
  acc_lim_x: 0.5    # 与PX4加速度限制对齐
  acc_lim_y: 0.5
  acc_lim_theta: 1.0
  
  vx_samples: 20
  vy_samples: 5
  vtheta_samples: 20
  
  sim_granularity: 0.05  # m
  sim_time: 1.0          # s
  
  path_distance_bias: 32.0
  goal_distance_bias: 24.0
  occdist_scale: 0.02
  forward_point_distance: 0.325
```

#### Step 2A-2: 集成 DWB 到 nav_stack（Day 6）
```
src/uav_bringup/launch/nav_stack.launch.py
  [替换] local_planner node
      from: nav_planning.local_planner (APF)
      ├─ 参数: occupied_thresh, free_thresh
      to: nav_planning.dwb_bridge (DWB)
      ├─ 参数: dwb_local_planner.yaml
      ├─ 话题: /local_map/occupancy → Costmap2D
      └─ 话题: /nav/goal_pose [需通过external_nav2_simple_commander或手动pose_pub模拟]
```

#### Step 2A-3: 验证与延迟检查（Day 7）
- 测试: 仿真环境下 OccupancyGrid (20Hz) → DWB规划 (<10ms) → cmd_vel (20Hz)
- 检查: TF查询延迟 (should be < 5ms since on same machine)
- 验证: 无静态障碍时是否能到达目标
- 验收: 与APF对比，DWB避障成功率 ≥ 95%

**代码变更位置**:
- `src/nav_planning/dwb_bridge.py` ← 新建
- `src/nav_planning/config/dwb_local_planner.yaml` ← 新建
- `src/uav_bringup/launch/nav_stack.launch.py` ← 改 (第45-50行: Node替换)
- `src/uav_bringup/config/nav_params.yaml` ← 改 (新增参数引入)

---

### 阶段2B: 安全监视器扩展（Week 1末 并行，Day 5-7）
**目标**: 从单传感器阈值 → 多源健康评分

**实现行动**:

```python
# src/nav_safety/safety_monitor.py [改造]

class SafetyMonitor:
    def __init__(self):
        # 现有: 点云超时+密度
        self.pc_timeout_sec = 2.0
        self.min_point_density = 100
        
        # 新增: TF + EKF + PX4 健康检查
        self.tf_timeout_sec = 0.5
        self.odometry_timeout_sec = 1.0
        self.px4_state_timeout_sec = 1.0
        
    def monitor_loop(self):
        # 现有
        pc_level = self.check_pointcloud_health()
        
        # 新增
        tf_level = self.check_tf_tree_health()      # 检查 base_link→map 转换延迟
        ekf_level = self.check_odometry_health()    # 检查 /odometry/filtered 鲜度
        px4_level = self.check_px4_state()          # 检查 /vehicle_status armed+offboard
        
        # 综合评分 (highest criticality winner)
        overall_level = max(pc_level, tf_level, ekf_level, px4_level)
        
        if overall_level == LEVEL_CRITICAL:
            self.trigger_emergency_land()
```

**新增检查逻辑**:
```python
def check_tf_tree_health(self):
    try:
        start = self.get_clock().now()
        trans = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
        elapsed = (self.get_clock().now() - start).nanoseconds / 1e9
        if elapsed > self.tf_timeout_sec:
            return LEVEL_WARN  # TF lookup太慢，可能VINS/EKF滞后
        return LEVEL_OK
    except Exception as e:
        return LEVEL_CRITICAL  # TF断裂，完全无定位

def check_odometry_health(self):
    if not hasattr(self, 'odometry_time'):
        return LEVEL_WARN
    since = (self.get_clock().now() - self.odometry_time).nanoseconds / 1e9
    if since > self.odometry_timeout_sec:
        return LEVEL_CRITICAL
    # 可选: 检查EKF协方差是否异常增长 (表示丧失VIO)
    return LEVEL_OK

def check_px4_state(self):
    if not hasattr(self, 'vehicle_status'):
        return LEVEL_WARN
    since = (self.get_clock().now() - self.vehicle_status.timestamp / 1e6).seconds
    if since > self.px4_state_timeout_sec:
        return LEVEL_CRITICAL
    if not self.vehicle_status.arming_state == ARMED:
        return LEVEL_WARN
    if not self.vehicle_status.nav_state == OFFBOARD:
        return LEVEL_WARN
    return LEVEL_OK
```

**验收标准**:
- ✓ 点云丢失 → 5s内 CRITICAL + emergency_land 发布
- ✓ TF延迟>0.5s → WARN (不中止，记日志)
- ✓ Odometry停止 → 3s内 CRITICAL + RTL
- ✓ PX4未armed → 启动时 WARN (允许等待)

**代码变更位置**:
- `src/nav_safety/safety_monitor.py` ← 改 (新增4个check方法, 第62-90行)

---

### 阶段3: PX4桥接状态机（Week 2）
**目标**: 完整的armed/offboard/hold转移 + 自动武装逻辑

**现状分析**:
```python
# src/px4_comm_bridge/control_bridge.py [现状 lines 67, 102-103]

def nav_to_px4_bridge():
    # 问题1: pose_cb 完全空 (reserved for future)
    def pose_cb(msg):  # lines 102-103
        # Reserved for future pose-based command mapping. return
        pass
    
    # 问题2: auto_arm 参数声明但未实现 (line 98)
    auto_arm = param_client.get_parameter('px4_bridge.auto_arm').value  # 读了没用
    
    # 问题3: 无state_machine, 仅 if received_cmd -> offboard_cmd
```

**改造方案**:

```python
# src/px4_comm_bridge/control_bridge.py [新版本]

from enum import Enum
from px4_msgs.msg import VehicleCommand, VehicleStatus

class AutopilotState(Enum):
    IDLE = 0
    ARMED = 1
    OFFBOARD = 2
    HOLDING = 3
    RTL = 4
    LAND = 5

class ControlBridge(Node):
    def __init__(self):
        super().__init__('px4_comm_bridge')
        self.state = AutopilotState.IDLE
        self.auto_arm = self.declare_parameter('auto_arm', False).value
        self.cmd_velocity_received_time = None
        self.cmd_timeout = 1.0  # s
        
    def vehicle_status_cb(self, msg: VehicleStatus):
        old_state = self.state
        
        # State machine logic
        if msg.arming_state != ARMED:
            self.state = AutopilotState.IDLE
        elif msg.nav_state != OFFBOARD:
            self.state = AutopilotState.ARMED
        else:
            self.state = AutopilotState.OFFBOARD
            
        if old_state != self.state:
            self.get_logger().info(f"State transition: {old_state} → {self.state}")
    
    def cmd_velocity_cb(self, msg: TwistStamped):
        current_time = self.get_clock().now()
        
        # Auto-arm logic
        if self.auto_arm and self.state == AutopilotState.IDLE:
            self.arm_vehicle()
            self.state = AutopilotState.ARMED
            
        # Transition to OFFBOARD if needed
        if self.state == AutopilotState.ARMED:
            self.set_offboard_mode()
            self.state = AutopilotState.OFFBOARD
            
        # Publish velocity command
        self.publish_offboard_velocity(msg)
        self.cmd_velocity_received_time = current_time
        
    def watchdog_loop(self):
        # Timeout detection
        if self.cmd_velocity_received_time is not None:
            elapsed = (self.get_clock().now() - self.cmd_velocity_received_time).nanoseconds / 1e9
            if elapsed > self.cmd_timeout:
                self.land()
                self.state = AutopilotState.LAND
    
    def arm_vehicle(self):
        cmd = VehicleCommand()
        cmd.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
        cmd.param1 = 1.0  # arm=1, disarm=0
        self.vehicle_cmd_pub.publish(cmd)
        self.get_logger().info("ARM command issued")
    
    def set_offboard_mode(self):
        cmd = VehicleCommand()
        cmd.command = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
        cmd.param1 = 1.0  # Main mode
        cmd.param2 = 6.0  # OFFBOARD sub-mode
        self.vehicle_cmd_pub.publish(cmd)
        self.get_logger().info("OFFBOARD mode command issued")
    
    def land(self):
        cmd = VehicleCommand()
        cmd.command = VehicleCommand.VEHICLE_CMD_NAV_LAND
        self.vehicle_cmd_pub.publish(cmd)
        self.get_logger().warn("LAND command issued")
```

**验收标准**:
- ✓ 收到cmd_vel + auto_arm=True → 3s内完成 ARM + OFFBOARD 转移
- ✓ cmd_vel 断糖 > 1s → 自动触发 LAND
- ✓ 无pose_cb实现导致的crash或挂起

**代码变更位置**:
- `src/px4_comm_bridge/control_bridge.py` ← 改 (新增AutopilotState,状态机逻辑, lines 40-80)

---

### 阶段4: 行为验证测试（Week 2-3）
**目标**: 从"topic存在" → "行为正确"

**现状问题**:
```python
# src/uav_bringup/test/test_nav_stack_integration.py [现状 lines 142-145]

def test_mapping():
    self.map_received = []
    node.subscribe(msg_type=OccupancyGrid, topic='/local_map/occupancy')
    rclpy.spin_once(node, 10)
    assert len(self.map_received) > 0  # ← 仅检查存在性!
```

**改造方案**:
```python
# src/uav_bringup/test/test_nav_stack_integration.py [新版本]

class TestNavBehavior(unittest.TestCase):
    
    def test_obstacle_avoidance(self):
        """验证DWB能避开OccupancyGrid中的障碍"""
        # Step 1: 发布虚拟OccupancyGrid (右侧有墙)
        og = OccupancyGrid()
        og.header.stamp = self.get_clock().now().to_msg()
        og.info.resolution = 0.1  # m/cell
        og.info.width, og.info.height = 20, 20
        og.data = [0]*400  # 全空闲
        og.data[210:220] = [100]*10  # 右侧墙 (占用)
        self.og_pub.publish(og)
        
        # Step 2: 发布目标 (右上)
        goal = PoseStamped()
        goal.pose.position.x = 2.0
        goal.pose.position.y = 0.5
        goal.pose.orientation.w = 1.0
        self.goal_pub.publish(goal)
        rclpy.spin_once(node, 1)
        
        # Step 3: 收集cmd_vel 10帧，验证y倾向 < -0.1 (避右)
        cmds = self.collect_messages(topic='/nav/cmd_vel', count=10, timeout=1.0)
        vy_list = [msg.twist.linear.y for msg in cmds]
        avg_vy = sum(vy_list) / len(vy_list)
        self.assertLess(avg_vy, -0.05, "DWB should avoid right wall (vy < -0.05)")
    
    def test_goal_reaching(self):
        """验证无障碍时能到达目标"""
        og = OccupancyGrid()
        og.info.width, og.info.height = 20, 20
        og.data = [0]*400  # 全空闲
        self.og_pub.publish(og)
        
        goal_pose = (1.0, 0.0, 0.0)  # 1m前方
        goal = PoseStamped()
        goal.pose.position.x, goal.pose.position.y = goal_pose[0], goal_pose[1]
        goal.pose.orientation.w = 1.0
        self.goal_pub.publish(goal)
        
        # 验证cmd_vel朝向目标 (vx > 0.5, vy ≈ 0)
        cmds = self.collect_messages(topic='/nav/cmd_vel', count=20, timeout=2.0)
        vx_list = [msg.twist.linear.x for msg in cmds]
        vy_list = [msg.twist.linear.y for msg in cmds]
        self.assertGreater(sum(vx_list)/len(vx_list), 0.5, "Should move forward")
        self.assertLess(abs(sum(vy_list)/len(vy_list)), 0.1, "Should not deviate sideways")
    
    def test_emergency_stop_on_point_cloud_loss(self):
        """验证点云丢失 → safety_monitor → emergency_land"""
        # 模拟点云停止 (不发布消息)
        # 等待 safety_monitor 检测超时
        time.sleep(2.5)
        
        # 验证emergency_land published
        em_msgs = self.collect_messages(topic='/safety_monitor/emergency_land', count=1, timeout=1.0)
        self.assertGreater(len(em_msgs), 0, "Emergency land should be triggered")
    
    def test_px4_auto_arm(self):
        """验证auto_arm=True时收到cmd_vel → ARM + OFFBOARD"""
        self.node.set_parameter(rclpy.Parameter('px4_bridge.auto_arm', ParameterValue(bool_value=True)))
        
        # 正常运行: 发布cmd_vel
        cmd = TwistStamped()
        cmd.twist.linear.x = 1.0
        self.cmd_pub.publish(cmd)
        
        # 监听vehicle_command主题, 应该收到ARM + SET_MODE
        cmds = self.collect_messages(topic='/fmu/in/vehicle_command', count=2, timeout=2.0)
        cmd_types = [msg.command for msg in cmds]
        self.assertIn(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, cmd_types)
        self.assertIn(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, cmd_types)
```

**验收标准**:
- ✓ 4个行为测试全部通过 (避障、到达、应急、自启)
- ✓ 测试运行时间 < 5min (可ci/cd集成)

**代码变更位置**:
- `src/uav_bringup/test/test_nav_stack_integration.py` ← 改 (新增4个test方法, ~100行)

---

### 阶段5: 启动脚本完全改造（Week 2末 + Week 3）
**目标**: 创建 `sim_nav_stack.launch.py` 和 `hw_nav_stack.launch.py` 差异化配置

**文件结构**:
```
src/uav_bringup/launch/
  ├─ nav_stack.launch.py              [现有, 保留向后兼容]
  ├─ hardware_nav_stack.launch.py     [新建]
  ├─ sim_nav_stack.launch.py          [新建]
  └─ includes/
      ├─ oakd_perception.launch.py    [新建, 提取OAK-D启动]
      ├─ localization_stack.launch.py [新建, VINS+EKF联合]
      └─ planning_safety_bridge.launch.py [新建, 规划+安全+桥接联合]
```

**改造核心**:

```python
# src/uav_bringup/launch/hardware_nav_stack.launch.py [新建]

def generate_launch_description():
    
    # 参数
    use_gps = LaunchConfiguration('use_gps')
    declare_use_gps = DeclareLaunchArgument('use_gps', default_value='false',
        description='Enable GPS fusion in EKF')
    
    declare_enable_safety = DeclareLaunchArgument('enable_safety', default_value='true')
    declare_dwb_params = DeclareLaunchArgument('dwb_params_file', 
        default_value=PathJoinSubstitution([
            FindPackageShare('nav_planning'),
            'config',
            'dwb_local_planner.yaml'
        ]))
    
    # 启动OAK-D感知
    oakd_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('oakd_perception'), 'launch', 'oakd_rgb_imu.launch.py'
        ])),
        launch_arguments={'enable_color': 'false', 'enable_depth': 'true'}.items()
    )
    
    # 启动定位栈 (VINS-Fusion + EKF)
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('uav_bringup'), 'launch', 'includes', 'localization_stack.launch.py'
        ])),
        launch_arguments={'use_gps': use_gps}.items()
    )
    
    # 启动规划+安全+桥接 (DWB + expanded safety + state machine)
    planning_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('uav_bringup'), 'launch', 'includes', 'planning_safety_bridge.launch.py'
        ])),
        launch_arguments={
            'dwb_params_file': LaunchConfiguration('dwb_params_file'),
            'enable_safety': DeclareLaunchArgument('enable_safety')
        }.items()
    )
    
    return LaunchDescription([
        declare_use_gps,
        declare_enable_safety,
        declare_dwb_params,
        oakd_launch,
        localization_launch,
        planning_launch,
        # 健康检查
        WaitOnCondition(condition=IfCondition(PythonExpression(["'vins' in get_namespaces()"])))
    ])

# 使用示例:
# ros2 launch uav_bringup hardware_nav_stack.launch.py use_gps:=true
```

**仿真版本**:
```python
# src/uav_bringup/launch/sim_nav_stack.launch.py [新建]
# 类似, 但 oakd_launch 替换为 mock_perception_node (发布固定PointCloud2)

def generate_launch_description():
    # 使用仿真OccupancyGrid发布节点
    sim_og_node = Node(
        package='nav_planning',
        executable='sim_occupancy_grid_node',
        name='sim_occupancy_grid',
        parameters=[{
            'grid_size_x': 20.0,
            'grid_size_y': 20.0,
            'resolution': 0.1,
            'publish_rate': 20,
            'enable_test_obstacles': True
        }]
    )
    
    # ... 其余同hardware, 但加载mock_localization而非VINS/EKF
```

**验收标准**:
- ✓ `ros2 launch uav_bringup hardware_nav_stack.launch.py` 30s内所有节点ready
- ✓ `ros2 launch uav_bringup sim_nav_stack.launch.py` 10s内仿真启动完成
- ✓ 参数动态传递生效 (use_gps/enable_safety/dwb_params_file)

**代码变更位置**:
- `src/uav_bringup/launch/hardware_nav_stack.launch.py` ← 新建
- `src/uav_bringup/launch/sim_nav_stack.launch.py` ← 新建
- `src/uav_bringup/launch/includes/localization_stack.launch.py` ← 新建
- `src/uav_bringup/launch/includes/planning_safety_bridge.launch.py` ← 新建

---

## ③ 分阶段实现计划（周度分解）

| 周次 | 天数 | 任务 | 责任人 | 验收 |
|------|------|------|--------|------|
| **W1** | D1-D3 | P0: 启动自包含 | 🟠 核心 | ✓ 单命令启全栈 |
| | D4-D5 | P1: DWB适配层 | 🟠 核心 | ✓ DWB→cmd_vel 发布 |
| | D6-D7 | P1: 安全监视器扩展 + DWB集成 | 🟠 核心 | ✓ 多源健康检查生效 |
| **W2** | D8-D9 | P1: PX4状态机 | 🟠 核心 | ✓ auto_arm → ARM+OFFBOARD |
| | D10-D11 | P2: 行为测试 (避障/到达/应急) | 🔵 测试 | ✓ 4个行为测试通过 |
| | D12-D14 | P2: 启动脚本完全重构 | 🟠 核心 | ✓ hw/sim版本双轨运行 |
| **W3** | D15-D16 | 集成验证 + 端对端测试 | 🔵 测试 | ✓ 仿真-硬件对标 |
| | D17-D21 | 参数调优 + 文档 | 🟢 文档 | ✓ 参数转移指南 ready |

**关键路径** (不可并行):
```
W1-D1-D3 (启动自包含) 
  ↓
W1-D4-D5 (DWB适配) 
  ↓
W2-D8-D9 (状态机) 
  ↓
W2-D10-D11 (行为测试)
  ↓
W3-D15-D16 (端对端验证)
```

**可并行任务**:
- W1-D4-D5 (DWB) ∥ W1-D4-D7 (安全监视器) ∥ W1-D6-D7 (DWB集成)
- W2-D10-D11 (测试) ∥ W2-D12-D14 (启动重构) [不依赖]

---

## ④ Nav2 DWB 集成指南

### 前置条件
1. **ROS2 包依赖** 检查/安装
   ```bash
   rosdep install -i --from-path src --rosdistro humble -y
   # 特别 ensure:
   # - nav2-core (包含DWB)
   # - nav2-costmap-2d
   # - tf2, tf2-geometry-msgs
   ```

2. **编译DWB适配层**
   ```bash
   cd src/nav_planning
   colcon build --packages-select nav_planning --symlink-install
   ```

### 集成步骤

#### I. 配置文件设置 (Day 4)
创建 `src/nav_planning/config/dwb_local_planner.yaml`:
```yaml
# DWB参数调优指南 (基于OAK-D 20Hz、PX4 100Hz offboard)

# ========== 速度限制 ==========
dwb_local_planner:
  # 线速度 [m/s] - OAK-D 400Hz IMU + 20Hz深度 → 稳定性0.5-2.0 m/s, 反应延迟80-100ms
  min_vel_x: -0.2          # 后退有限度
  max_vel_x: 2.0           # 前进上限与PX4加速度对齐
  min_vel_y: -1.0          # 侧移范围
  max_vel_y: 1.0
  
  # 角速度 [rad/s] - π/2 ≈ 1.57
  min_vel_theta: -1.57
  max_vel_theta: 1.57
  
  # ========== 加速度限制 [m/s²] ==========
  # 与PX4 INAV加速度配置对齐 (default: 9.81 m/s²)
  acc_lim_x: 0.5
  acc_lim_y: 0.5
  acc_lim_theta: 1.0
  
  # ========== 采样配置 ==========
  # 沿袭DWA思路: 速度分量 × 时间段充分采样
  vx_samples: 20           # 线速度采样点
  vy_samples: 5            # Y轴采样 (较少, 默认以前向为主)
  vtheta_samples: 20       # 旋转采样
  
  # ========== 模拟参数 ==========
  sim_time: 1.0            # 前向搜索时间 [s]
  sim_granularity: 0.05    # 轨迹采样粒度 [m] (0.1 → 0.05 精度提升)
  
  # ========== 评估函数权重 ==========
  # 总评分 = path×weight + goal×weight + occdist×weight
  
  # 路径保真度 (越大越贴近局部优先目标方向)
  path_distance_bias: 32.0
  
  # 目标指向性 (越大越优先到达goal_pose而非通用规划)
  goal_distance_bias: 24.0
  
  # 障碍距离权重 (越大越保守避碰)
  occdist_scale: 0.02      # OAK-D深度精度有限, 不宜过激进
  
  # 目标方向前视距离, 用于评估朝向
  forward_point_distance: 0.325  #≈ 1/3 m (OAK-D FOV 70°下合理)
  
  # ========== 其他参数 ==========
  # 轨迹评估步长 [s] (越小精度越高但计算量↑)
  publish_cost_grid_pc: true   # 发布costmap用于调试
  prune_plan: true             # 清理已通过的path段
```

#### II. DWB适配层代码 (已在 Step 2A-1 中给出)

#### III. 话题绑定与TF配置

**OccupancyGrid → Costmap转换**:
```python
# 在dwb_bridge.py __init__ 中
from nav2_costmap_2d import Costmap2D

class DWBBridge(Node):
    def __init__(self):
        self.costmap = Costmap2D()
        self.costmap.setSizeInMeters(20.0, 20.0, 0.1)  # width, height, resolution
        
    def grid_callback(self, msg: OccupancyGrid):
        """Convert ROS OccupancyGrid → nav2_costmap_2d::Costmap2D"""
        # 逐cell更新代价
        for y in range(msg.info.height):
            for x in range(msg.info.width):
                idx = y * msg.info.width + x
                if msg.data[idx] > 50:  # occupied threshold
                    self.costmap.setCost(x, y, 254)  # LETHAL_OBSTACLE
                else:
                    self.costmap.setCost(x, y, 0)
```

**TF依赖关系** (确保已建立):
```
map
  ├─ odom          [robot_localization → EKF输出]
  │   └─ base_link [VINS-Fusion或IMU提供]
  └─ vins          [VINS-Fusion隔离TF, 用于调试]
```

验证:
```bash
ros2 run tf2_tools view_frames
# 应输出: map -> odom -> base_link 链路完整
```

#### IV. 参数加载与launch集成

**launch.py 中加载配置**:
```python
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution

dwb_config_file = PathJoinSubstitution([
    FindPackageShare('nav_planning'),
    'config',
    'dwb_local_planner.yaml'
])

dwb_bridge_node = Node(
    package='nav_planning',
    executable='dwb_bridge',
    name='dwb_bridge',
    parameters=[dwb_config_file],
    remappings=[
        ('/local_map/occupancy', '/local_map/occupancy'),  # 输入
        ('/nav/goal_pose', '/nav/goal_pose'),              # 目标
        ('/tf', '/tf'),                                    # TF树
        ('/nav/cmd_vel', '/nav/cmd_vel')                   # 输出
    ],
    output='screen'
)
```

#### V. 参数调优流程

**初期** (Day 5-6):
1. 设置 `path_distance_bias = 32.0` (路径跟踪优先)
2. 设置 `occdist_scale = 0.02` (保守避碰)
3. 运行仿真: `ros2 launch uav_bringup sim_nav_stack.launch.py`
4. 观察 `/cost_cloud` 话题 (如发布), 检查costmap更新频率 ≥ 20Hz

**中期** (Day 6):
- 如转向不足: ↑ `goal_distance_bias` to 32.0
- 如避碰过度: ↓ `occdist_scale` to 0.01
- 如路径抖动: ↓ `vx_samples`/`vtheta_samples` to 15/15

**后期** (W2):
- 实测OAK-D延迟 (<100ms target), 如超: ↓ `sim_time` to 0.5s
- 检查PX4反应延迟 (<50ms target), 否则 ↓ `acceleration_limits`

### 常见问题排查

| 问题 | 症状 | 排查 | 解决 |
|------|------|------|------|
| **Costmap未更新** | cmd_vel 不变 | `rostopic hz /local_map/occupancy` (<5Hz?) | ↑ nav_mapping 发布率 |
| **TF延迟** | DWB查询超时 | `ros2 run tf2_tools view_frames` (任何链路断? | 确保VINS+EKF都launching |
| **转向僵硬** | 绕障碍半径过大 | 调整 `goal_distance_bias` | 尝试 24.0 → 32.0 |
| **局部震荡** | 在目标附近抖动 | `vtheta_samples` 过多 | ↓ to 15 |
| **OccupancyGrid占用阈值** | 不该避的被当障碍 | 检查OG.data encoding (0-100 range) | 调整 grid_callback 中的 `if msg.data[idx] > 50` |

---

## ⑤ 启动脚本重构方案 (自包含化)

### 当前问题
```
❌ ros2 launch uav_bringup nav_stack.launch.py
   → 仅启4个节点 (map/plan/safety/bridge)
   → 缺OAK-D/VINS/EKF → 需手动另开3个终端
   → 测试/CI/CD无法自动化
```

### 目标状态
```
✅ ros2 launch uav_bringup hardware_nav_stack.launch.py use_gps:=true
   → 11个节点全部启动 (perception + localization + planning + control)
   → 30s内TF树完整, 所有话题active
   → 支持参数动态传递 (use_gps, dwb_params_file, etc)
```

### 实现方案

#### Step 1: 提取perception启动 (Day 14)
```python
# src/uav_bringup/launch/includes/oakd_perception.launch.py [新建]

def generate_launch_description():
    return LaunchDescription([
        # OAK-D RGBD node
        Node(
            package='depthai_ros_driver',  # 或你使用的OAK-D包
            executable='rgb_stereo_node',
            name='oak_rgbd',
            parameters=[
                {'enable_rgb': False},
                {'enable_depth': True},
                {'enable_imu': True},
                {'depth_fps': 30},
                {'rgb_fps': 0},  # disabled
                {'imu_rate': 400},
                {'spatial_detection_node': False}
            ],
            remappings=[
                ('/oak/rgb/image_raw', '/oak/rgb/image_raw'),
                ('/oak/stereo/depth_registered', '/oak/stereo/depth_registered'),
                ('/oak/imu', '/oak/imu')
            ]
        ),
        
        # IMU fusion node
        Node(
            package='oakd_imu_fusion',
            executable='imu_fusion_node',
            name='imu_fusion',
            parameters=[{'fusion_rate': 400}],
            remappings=[('/imu/data', '/imu/data')]
        )
    ])
```

#### Step 2: 提取localization启动 (Day 14)
```python
# src/uav_bringup/launch/includes/localization_stack.launch.py [新建]

def generate_launch_description():
    use_gps = LaunchConfiguration('use_gps')
    
    return LaunchDescription([
        DeclareLaunchArgument('use_gps', default_value='true'),
        
        # VINS-Fusion
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('vins_fusion_ros2'),
                'launch',
                'oakd_vins.launch.py'
            ]))
        ),
        
        # EKF dual-tier
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('uav_bringup'),
                'launch',
                'ekf_launch.py'
            ])),
            launch_arguments={'enable_gps': use_gps}.items()
        )
    ])
```

#### Step 3: 提取planning+safety+bridge启动 (Day 14)
```python
# src/uav_bringup/launch/includes/planning_safety_bridge.launch.py [新建]

def generate_launch_description():
    dwb_params = LaunchConfiguration('dwb_params_file')
    enable_safety = LaunchConfiguration('enable_safety')
    
    return LaunchDescription([
        DeclareLaunchArgument('dwb_params_file', default_value=PathJoinSubstitution([
            FindPackageShare('nav_planning'), 'config', 'dwb_local_planner.yaml'
        ])),
        DeclareLaunchArgument('enable_safety', default_value='true'),
        
        # Local mapping
        Node(
            package='nav_mapping',
            executable='local_map_builder_node',
            name='local_map_builder'
        ),
        
        # DWB planning (replaced from APF)
        Node(
            package='nav_planning',
            executable='dwb_bridge',
            name='dwb_bridge',
            parameters=[dwb_params],
            remappings=[
                ('/local_map/occupancy', '/local_map/occupancy'),
                ('/nav/goal_pose', '/nav/goal_pose'),
                ('/nav/cmd_vel', '/nav/cmd_vel')
            ]
        ),
        
        # Safety (conditionally)
        Node(
            package='nav_safety',
            executable='safety_monitor_node',
            name='safety_monitor',
            condition=IfCondition(enable_safety),
            parameters=[{'health_check_expanded': True}]
        ),
        
        # PX4 bridge
        Node(
            package='px4_comm_bridge',
            executable='control_bridge_node',
            name='px4_comm_bridge',
            parameters=[
                {'auto_arm': False},  # 用户可override
                {'cmd_timeout_sec': 1.0}
            ]
        )
    ])
```

#### Step 4: 创建硬件启动入口 (Day 14)
```python
# src/uav_bringup/launch/hardware_nav_stack.launch.py [新建]

def generate_launch_description():
    use_gps = LaunchConfiguration('use_gps')
    
    return LaunchDescription([
        # 参数声明
        DeclareLaunchArgument('use_gps', default_value='false',
            description='Enable GPS in EKF'),
        
        # 感知
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('uav_bringup'),
                'launch', 'includes',
                'oakd_perception.launch.py'
            ]))
        ),
        
        # 定位
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('uav_bringup'),
                'launch', 'includes',
                'localization_stack.launch.py'
            ])),
            launch_arguments={'use_gps': use_gps}.items()
        ),
        
        # 规划+安全+桥接
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('uav_bringup'),
                'launch', 'includes',
                'planning_safety_bridge.launch.py'
            ]))
        )
    ])
```

#### Step 5: 创建仿真启动入口 (Day 14)
```python
# src/uav_bringup/launch/sim_nav_stack.launch.py [新建]

def generate_launch_description():
    """仿真版本: 用mock节点替代OAK-D和VINS"""
    
    return LaunchDescription([
        # Mock感知 (发布固定PointCloud2 + OccupancyGrid)
        Node(
            package='nav_planning',
            executable='mock_perception_node',  # [需新建]
            name='mock_perception',
            parameters=[{'enable_obstacles': True}]
        ),
        
        # Mock定位 (Gazebo /odom 直接用)
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_odom',
            parameters=[PathJoinSubstitution([
                FindPackageShare('robot_localization'),
                'etc', 'ekf.yaml'
            ])],
            remappings=[
                ('/odometry/filtered', '/odometry/filtered')
            ]
        ),
        
        # 规划+安全+桥接 (同上)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([
                FindPackageShare('uav_bringup'),
                'launch', 'includes',
                'planning_safety_bridge.launch.py'
            ]))
        )
    ])
```

### 启动验收

**硬件启动** (Day 14)
```bash
# 终端1: 启动完整栈 (GPS开)
ros2 launch uav_bringup hardware_nav_stack.launch.py use_gps:=true

# 验证 (新终端)
ros2 node list            # 应≥11 nodes
ros2 topic list | wc -l   # 应≥15 topics
ros2 service list | wc -l # 应≥5 services

# 检查TF树
ros2 run tf2_tools view_frames
# 应输出: map → odom → base_link 链路
```

**仿真启动** (Day 14)
```bash
ros2 launch uav_bringup sim_nav_stack.launch.py

# 仿真应在10s内完成启动
# 观察: /local_map/occupancy (20Hz), /odometry/filtered (50Hz), /nav/cmd_vel (20Hz)
```

---

## 总结清单

### 交付物 (Week 1-3末)
- [ ] **P0**: nav_stack.launch.py自包含化 ✅
- [ ] **P1-规划**: DWB适配层+config ✅
- [ ] **P1-安全**: 扩展health_check ✅
- [ ] **P1-桥接**: PX4状态机 ✅
- [ ] **P2-测试**: 行为验证测试套件 ✅
- [ ] **P2-启动**: hw/sim双轨launch ✅

### 验收标准
| 阶段 | 标准 |
|------|------|
| W1末 | 单命令启全栈, DWB发布, 多源健康检查生效 |
| W2末 | auto_arm可用, 4个行为测试通过, hw/sim启动完备 |
| W3末 | 仿真-硬件对标, 参数转移指南完成, 文档更新 |

### 风险与缓解
| 风险 | 概率 | 缓解 |
|------|------|------|
| DWB参数调优耗时 | 中 | 预留W2周末 + 对标APF baseline |
| OAK-D实时性问题 | 中 | 启动时检查rostopic hz, 如<15Hz降计算 |
| TF链路断裂 | 低 | VINS/EKF分离的TF (vins/tf) 及时跳过 |
| PX4状态机复杂 | 低 | 保守从auto_arm=false启, 手动测试arm/offboard |

---

## 后续 (Week 4+)

- 3D规划迁移 (Nav2 MPPI或其他3D capable planner)
- 光流/点云SLAM替代选项 (Ceres-SLAM, TUMVIS等)
- 实机硬件验收 (真实OAK-D + PX4 + Vicon ground truth)
