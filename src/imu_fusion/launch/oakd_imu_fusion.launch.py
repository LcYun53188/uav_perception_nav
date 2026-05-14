"""
Backward compatibility launch file.
For new projects, use 'imu_fusion.launch.py' instead.
This file maintains the original oakd_imu_* topic naming conventions.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    raw_topic = LaunchConfiguration('raw_topic')
    fused_topic = LaunchConfiguration('fused_topic')
    frame_id = LaunchConfiguration('frame_id')
    parent_frame = LaunchConfiguration('parent_frame')
    imu_frequency = LaunchConfiguration('imu_frequency')

    imu_fusion_dir = FindPackageShare('imu_fusion')
    imu_fusion_launch = PathJoinSubstitution(
        [imu_fusion_dir, 'launch', 'imu_fusion.launch.py']
    )

    return LaunchDescription([
        DeclareLaunchArgument('raw_topic', default_value='/oakd/imu/raw'),
        DeclareLaunchArgument('fused_topic', default_value='/oakd/imu'),
        DeclareLaunchArgument('frame_id', default_value='oakd_imu_link'),
        DeclareLaunchArgument('parent_frame', default_value='map'),
        DeclareLaunchArgument('imu_frequency', default_value='400'),
        IncludeLaunchDescription(
            imu_fusion_launch,
            launch_arguments={
                'raw_topic_0': raw_topic,
                'fused_topic_0': fused_topic,
                'frame_id_0': frame_id,
                'parent_frame': parent_frame,
                'imu_frequency': imu_frequency,
            }.items(),
        ),
    ])