"""
Unified navigation stack launch file (W1-D1-D3: 自包含化)

启动完整的无人机导航栈：
  1. 感知层: OAK-D RGB-D 相机 + IMU (400Hz) 
  2. 定位层: VINS-Fusion VIO + dual EKF (robot_localization)
  3. 规划层: 局部规划器 (当前APF，后续替换为DWB)
  4. 安全层: 多源健康监视
  5. 控制层: PX4 offboard 桥接

用法:
  ros2 launch uav_bringup nav_stack.launch.py enable_gps:=false
"""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('uav_bringup'),
        'config',
        'nav_stack.yaml',
    ])

    px4_comm_bridge_config = PathJoinSubstitution([
        FindPackageShare('px4_comm_bridge'),
        'config',
        'px4_comm_bridge.yaml',
    ])

    enable_gps = LaunchConfiguration('enable_gps')
    launch_dwb = LaunchConfiguration('launch_dwb')

    # ─────────────────────────────────────────────────────
    # ① OAK-D 感知层 (RGB-D + IMU 400Hz + Point Cloud 20Hz)
    # ─────────────────────────────────────────────────────
    oakd_perception_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('oakd_perception'),
                'launch',
                'oakd_unified.launch.py',
            ])
        ),
        launch_arguments={
            'imu_frequency': '400',
            'pointcloud_frequency': '20',
            'enable_passive_stereo': 'true',
        }.items(),
    )

    # ─────────────────────────────────────────────────────
    # ② IMU 融合层 (OAK-D + external IMU)
    # ─────────────────────────────────────────────────────
    imu_fusion_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('imu_fusion'),
                'launch',
                'oakd_imu_fusion.launch.py',
            ])
        ),
        launch_arguments={
            'raw_topic': '/oakd/imu/raw',
            'fused_topic': '/oakd/imu/fused',
            'frame_id': 'oakd_imu_link',
            'imu_frequency': '400',
        }.items(),
    )

    # ─────────────────────────────────────────────────────
    # ③ VINS-Fusion 视觉惯性里程计 (VIO)
    # ─────────────────────────────────────────────────────
    vins_fusion_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('vins_fusion_ros2'),
                'launch',
                'oakd_vins.launch.py',
            ])
        ),
    )

    # ─────────────────────────────────────────────────────
    # ④ 双层EKF融合 (robot_localization)
    # 说明：
    #   - EKF_odom: 融合 VINS + IMU → odom 帧 (局部坐标)
    #   - EKF_map: 融合 VINS + IMU + GPS (可选) → map 帧 (全局坐标)
    # ─────────────────────────────────────────────────────
    ekf_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('uav_bringup'),
                'launch',
                'ekf_launch.py',
            ])
        ),
        launch_arguments={'enable_gps': enable_gps}.items(),
    )

    # ─────────────────────────────────────────────────────
    # ⑤ 规划+安全+控制层
    # ─────────────────────────────────────────────────────
    return LaunchDescription([
        # ─ 参数声明 ─
        DeclareLaunchArgument(
            'enable_gps',
            default_value='false',
            description='Enable GPS fusion (dual EKF + NavSat). Set false for GPS-denied.',
        ),
        DeclareLaunchArgument(
            'launch_dwb',
            default_value='false',
            description='Launch DWB adapter. Requires Nav2 Python modules.',
        ),

        # ─ 启动顺序（感知 → 定位 → 规划/安全/控制） ─
        oakd_perception_launch,
        imu_fusion_launch,
        vins_fusion_launch,
        ekf_launch,

        # ─ 局部地图构建 ─
        Node(
            package='nav_mapping',
            executable='local_map_builder',
            name='local_map_builder',
            output='screen',
            parameters=[config_file],
        ),

        # ─ 局部规划器 (SE(2) DWA: vx/vy/yaw_rate) ─
        Node(
            package='nav_planning',
            executable='se2_dwa_local_planner',
            name='se2_dwa_local_planner',
            output='screen',
            parameters=[config_file],
        ),

        # ─ DWB 局部规划器适配层 (W1-D6) ─
        Node(
            package='nav_planning',
            executable='dwb_bridge',
            name='dwb_bridge',
            output='screen',
            condition=IfCondition(launch_dwb),
            parameters=[
                PathJoinSubstitution([
                    FindPackageShare('nav_planning'),
                    'config',
                    'dwb_local_planner.yaml',
                ]),
            ],
            remappings=[
                ('/oakd/points', '/oakd/points'),
                ('/tf', '/tf'),
                ('/tf_static', '/tf_static'),
                ('/odometry/filtered', '/odometry/filtered'),
                ('/nav/goal_pose', '/nav/goal_pose'),
                ('/nav/cmd_vel', '/nav/cmd_vel'),
            ],
        ),

        # ─ 安全监视器 ─
        Node(
            package='nav_safety',
            executable='safety_monitor',
            name='safety_monitor',
            output='screen',
            parameters=[config_file],
        ),

        # ─ PX4 offboard 桥接 ─
        Node(
            package='px4_comm_bridge',
            executable='px4_bridge_node',
            name='px4_comm_bridge',
            output='screen',
            parameters=[px4_comm_bridge_config],
        ),
    ])
