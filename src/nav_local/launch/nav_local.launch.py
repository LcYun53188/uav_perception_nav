from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    ld = LaunchDescription()

    ld.add_action(Node(
        package='nav_local',
        executable='local_map_builder',
        name='local_map_builder',
        output='screen',
        parameters=[{'resolution': 0.5, 'width': 40, 'height': 40}]
    ))

    ld.add_action(Node(
        package='nav_local',
        executable='local_planner',
        name='local_planner',
        output='screen',
    ))

    ld.add_action(Node(
        package='nav_local',
        executable='px4_offboard_ctrl',
        name='px4_offboard_ctrl',
        output='screen',
    ))

    ld.add_action(Node(
        package='nav_local',
        executable='safety_monitor',
        name='safety_monitor',
        output='screen',
    ))

    return ld
