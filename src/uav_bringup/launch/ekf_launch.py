"""
Launch file for robot_localization EKF node.

This launch file starts the EKF node for sensor fusion:
- IMU from imu_fusion_node (/imu)
- Optional VIO odometry (/vio/odometry)
- Optional PX4 vehicle odometry (/px4/vehicle_odometry)

Output: /odometry/filtered (nav_msgs/Odometry)
TF: odom → base_link
"""

from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate launch description for EKF node."""
    config_file = PathJoinSubstitution([
        FindPackageShare('uav_bringup'),
        'config',
        'ekf.yaml',
    ])

    return LaunchDescription([
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[config_file],
            remappings=[
                # Ensure TF is published correctly
                ('/tf', '/tf'),
                ('/tf_static', '/tf_static'),
            ],
        ),
    ])
