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
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    enable_gps = LaunchConfiguration('enable_gps').perform(context).lower() == 'true'

    config_file = PathJoinSubstitution([
        FindPackageShare('uav_bringup'),
        'config',
        'dual_ekf.yaml',
    ])

    nodes = []

    # ── 始终启动：EKF_odom (odom→base_link) ──
    nodes.append(Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node_odom',
        output='screen',
        parameters=[config_file],
        remappings=[
            ('odometry/filtered', 'odometry/local'),
            ('/tf', '/tf'),
            ('/tf_static', '/tf_static'),
        ],
    ))

    if enable_gps:
        # ── GPS 模式：EKF_map (map→odom) ──
        nodes.append(Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_map',
            output='screen',
            parameters=[config_file],
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

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'enable_gps',
            default_value='false',
            description='Enable GPS fusion (dual EKF + NavSat). Set false for GPS-denied.',
        ),
        OpaqueFunction(function=launch_setup),
    ])
