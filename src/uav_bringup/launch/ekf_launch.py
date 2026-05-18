"""
Launch file for dual EKF sensor fusion with optional GPS.

Modes:
  enable_gps:=false (default):
    - EKF_odom: odom→base_link (VIO + IMU)
    - Static TF: map→odom (identity, map=odom)

  enable_gps:=true:
    - EKF_odom: odom→base_link (VIO + IMU)
    - EKF_map:  map→odom (VIO + IMU + GPS correction)
    - NavSat Transform: GPS WGS84→ENU

Both modes publish static transforms:
  - base_link → oakd_imu_link (camera mount extrinsic)
  - base_link → gps_link (GPS antenna offset)

Output topics:
  - /odometry/local  (from EKF_odom)
  - /odometry/global (from EKF_map, GPS mode only)

Optional:
  enable_lio:=true adds /lio/odometry as a redundant odometry source.
  enable_mid360:=true publishes base_link→mid360_link static extrinsics.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    enable_gps = LaunchConfiguration('enable_gps').perform(context).lower() == 'true'
    enable_lio = LaunchConfiguration('enable_lio').perform(context).lower() == 'true'
    enable_mid360 = (
        LaunchConfiguration('enable_mid360').perform(context).lower() == 'true'
    )
    lio_odom_topic = LaunchConfiguration('lio_odom_topic').perform(context)

    config_file = PathJoinSubstitution([
        FindPackageShare('uav_bringup'),
        'config',
        'dual_ekf.yaml',
    ])

    nodes = []
    ekf_odom_parameters = [config_file]
    if enable_lio:
        ekf_odom_parameters.append({
            'odom1': lio_odom_topic,
            'odom1_config': [
                True, True, True,
                False, False, False,
                True, True, True,
                False, False, False,
                False, False, False,
            ],
            'odom1_queue_size': 10,
            'odom1_nodelay': True,
            'odom1_differential': False,
            'odom1_relative': False,
        })

    # ── 始终启动：EKF_odom (odom→base_link) ──
    nodes.append(Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node_odom',
        output='screen',
        parameters=ekf_odom_parameters,
        remappings=[
            ('odometry/filtered', 'odometry/local'),
            ('/tf', '/tf'),
            ('/tf_static', '/tf_static'),
        ],
    ))

    if enable_gps:
        ekf_map_parameters = [config_file]
        if enable_lio:
            ekf_map_parameters.append({
                'odom2': lio_odom_topic,
                'odom2_config': [
                    True, True, True,
                    False, False, False,
                    True, True, True,
                    False, False, False,
                    False, False, False,
                ],
                'odom2_queue_size': 10,
                'odom2_nodelay': True,
                'odom2_differential': False,
                'odom2_relative': False,
            })

        # ── GPS 模式：EKF_map (map→odom) ──
        nodes.append(Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_map',
            output='screen',
            parameters=ekf_map_parameters,
            remappings=[
                ('odometry/filtered', 'odometry/global'),
            ],
        ))

        # ── GPS 模式：NavSat Transform ──
        nodes.append(Node(
            package='robot_localization',
            executable='navsat_transform_node',
            name='navsat_transform',
            output='screen',
            parameters=[config_file],
            remappings=[
                ('imu', '/px4/imu'),
                ('gps/fix', '/gps/fix'),
                ('odometry/filtered', 'odometry/global'),
            ],
        ))
    else:
        # ── 无 GPS 模式：静态 map→odom 恒等变换 ──
        nodes.append(Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='map_to_odom_identity',
            arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
        ))

    # ── 静态外参：base_link → oakd_imu_link ──
    # TODO: 替换为实际测量的相机安装偏移量 [x, y, z, yaw, pitch, roll]
    # 坐标约定：ROS ENU (X-前, Y-左, Z-上)
    nodes.append(Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_oakd_imu_link',
        arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'oakd_imu_link'],
    ))

    # ── 静态外参：base_link → gps_link ──
    # GPS 天线与飞控中心偏移（通常较小，可设为全零）
    nodes.append(Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='base_link_to_gps_link',
        arguments=['0', '0', '0', '0', '0', '0', 'base_link', 'gps_link'],
    ))

    if enable_mid360 or enable_lio:
        # 坐标约定：ROS ENU (X-前, Y-左, Z-上)，参数顺序为 x y z yaw pitch roll。
        nodes.append(Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_link_to_mid360_link',
            arguments=[
                LaunchConfiguration('mid360_x'),
                LaunchConfiguration('mid360_y'),
                LaunchConfiguration('mid360_z'),
                LaunchConfiguration('mid360_yaw'),
                LaunchConfiguration('mid360_pitch'),
                LaunchConfiguration('mid360_roll'),
                'base_link',
                'mid360_link',
            ],
        ))

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'enable_gps',
            default_value='false',
            description='Enable GPS fusion (dual EKF + NavSat). Set false for GPS-denied.',
        ),
        DeclareLaunchArgument(
            'enable_mid360',
            default_value='false',
            description='Publish base_link to mid360_link static TF.',
        ),
        DeclareLaunchArgument(
            'enable_lio',
            default_value='false',
            description='Fuse LIO odometry as a redundant EKF input.',
        ),
        DeclareLaunchArgument(
            'lio_odom_topic',
            default_value='/lio/odometry',
            description='LIO odometry topic.',
        ),
        DeclareLaunchArgument('mid360_x', default_value='0.0'),
        DeclareLaunchArgument('mid360_y', default_value='0.0'),
        DeclareLaunchArgument('mid360_z', default_value='0.0'),
        DeclareLaunchArgument('mid360_yaw', default_value='0.0'),
        DeclareLaunchArgument('mid360_pitch', default_value='0.0'),
        DeclareLaunchArgument('mid360_roll', default_value='0.0'),
        OpaqueFunction(function=launch_setup),
    ])
