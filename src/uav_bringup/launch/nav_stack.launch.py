from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('uav_bringup'),
        'config',
        'nav_stack.yaml',
    ])

    return LaunchDescription([
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
            package='nav_px4_bridge',
            executable='px4_offboard_ctrl',
            name='px4_offboard_ctrl',
            output='screen',
            parameters=[config_file],
        ),
    ])