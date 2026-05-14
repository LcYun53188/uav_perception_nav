from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

"""
IMU Fusion Launch File

Supports single and multiple IMU configurations.
"""


def generate_launch_description():
    # Primary IMU configuration
    raw_topic_0 = LaunchConfiguration('raw_topic_0')
    fused_topic_0 = LaunchConfiguration('fused_topic_0')
    frame_id_0 = LaunchConfiguration('frame_id_0')
    parent_frame = LaunchConfiguration('parent_frame')
    imu_frequency = LaunchConfiguration('imu_frequency')
    num_imus = LaunchConfiguration('num_imus')

    # Secondary IMU configuration
    raw_topic_1 = LaunchConfiguration('raw_topic_1')
    fused_topic_1 = LaunchConfiguration('fused_topic_1')
    frame_id_1 = LaunchConfiguration('frame_id_1')

    # Additional IMU configurations (extensible for 3+)
    raw_topic_2 = LaunchConfiguration('raw_topic_2')
    fused_topic_2 = LaunchConfiguration('fused_topic_2')
    frame_id_2 = LaunchConfiguration('frame_id_2')

    nodes = [
        # Primary IMU (0) - Always launched
        Node(
            package='oakd_perception',
            executable='oakd_imu_node',
            name='oakd_imu_node_0',
            output='screen',
            parameters=[
                {'topic_name': raw_topic_0},
                {'frame_id': frame_id_0},
                {'imu_frequency': imu_frequency},
            ],
        ),
        Node(
            package='imu_fusion',
            executable='imu_fusion_node',
            name='imu_fusion_node_0',
            output='screen',
            parameters=[
                {'input_topic': raw_topic_0},
                {'output_topic': fused_topic_0},
                {'frame_id': frame_id_0},
            ],
        ),
        Node(
            package='imu_fusion',
            executable='imu_tf_broadcaster',
            name='imu_tf_broadcaster_0',
            output='screen',
            parameters=[
                {'input_topic': fused_topic_0},
                {'parent_frame': parent_frame},
                {'child_frame': frame_id_0},
            ],
        ),
    ]

    return LaunchDescription([
        DeclareLaunchArgument('raw_topic_0', default_value='/imu/raw'),
        DeclareLaunchArgument('fused_topic_0', default_value='/imu'),
        DeclareLaunchArgument('frame_id_0', default_value='oakd_imu_link'),
        DeclareLaunchArgument('parent_frame', default_value='map'),
        DeclareLaunchArgument('imu_frequency', default_value='400'),
        DeclareLaunchArgument('num_imus', default_value='1'),
        
        # Secondary IMU arguments (for convenience)
        DeclareLaunchArgument('raw_topic_1', default_value='/imu_1/raw'),
        DeclareLaunchArgument('fused_topic_1', default_value='/imu_1'),
        DeclareLaunchArgument('frame_id_1', default_value='oakd_imu_link_1'),
        
        # Tertiary IMU arguments (for convenience)
        DeclareLaunchArgument('raw_topic_2', default_value='/imu_2/raw'),
        DeclareLaunchArgument('fused_topic_2', default_value='/imu_2'),
        DeclareLaunchArgument('frame_id_2', default_value='oakd_imu_link_2'),
    ] + nodes)
