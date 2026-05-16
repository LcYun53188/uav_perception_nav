from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.actions import IncludeLaunchDescription
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

    ekf_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('uav_bringup'),
                'launch',
                'ekf_launch.py',
            ])
        )
    )

    return LaunchDescription([
        ekf_launch,
        Node(
            package='nav_mapping',
            executable='local_map_builder',
            name='local_map_builder',
            output='screen',
            parameters=[config_file],
        ),
        Node(
            package='nav_planning',
            executable='local_planner',
            name='local_planner',
            output='screen',
            parameters=[config_file],
        ),
        Node(
            package='nav_safety',
            executable='safety_monitor',
            name='safety_monitor',
            output='screen',
            parameters=[config_file],
        ),
        Node(
            package='px4_comm_bridge',
            executable='px4_bridge_node',
            name='px4_comm_bridge',
            output='screen',
            parameters=[px4_comm_bridge_config],
        ),
    ])
