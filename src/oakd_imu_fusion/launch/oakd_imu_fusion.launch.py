from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    raw_topic = LaunchConfiguration('raw_topic')
    fused_topic = LaunchConfiguration('fused_topic')
    frame_id = LaunchConfiguration('frame_id')
    parent_frame = LaunchConfiguration('parent_frame')
    imu_frequency = LaunchConfiguration('imu_frequency')

    return LaunchDescription([
        DeclareLaunchArgument('raw_topic', default_value='/oakd/imu/raw'),
        DeclareLaunchArgument('fused_topic', default_value='/oakd/imu'),
        DeclareLaunchArgument('frame_id', default_value='oakd_imu_link'),
        DeclareLaunchArgument('parent_frame', default_value='map'),
        DeclareLaunchArgument('imu_frequency', default_value='400'),
        Node(
            package='oakd_perception',
            executable='oakd_imu_node',
            name='oakd_imu_node',
            output='screen',
            parameters=[
                {'topic_name': raw_topic},
                {'frame_id': frame_id},
                {'imu_frequency': imu_frequency},
            ],
        ),
        Node(
            package='oakd_imu_fusion',
            executable='oakd_imu_fusion_node',
            name='oakd_imu_fusion_node',
            output='screen',
            parameters=[
                {'input_topic': raw_topic},
                {'output_topic': fused_topic},
                {'frame_id': frame_id},
            ],
        ),
        Node(
            package='oakd_imu_fusion',
            executable='oakd_imu_tf_broadcaster',
            name='oakd_imu_tf_broadcaster',
            output='screen',
            parameters=[
                {'input_topic': fused_topic},
                {'parent_frame': parent_frame},
                {'child_frame': frame_id},
            ],
        ),
    ])