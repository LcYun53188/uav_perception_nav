from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

"""
IMU Fusion Launch File

Supports single and multiple IMU configurations.
"""


def launch_setup(context, *args, **kwargs):
    # Primary IMU configuration
    raw_topic_0 = LaunchConfiguration('raw_topic_0').perform(context)
    fused_topic_0 = LaunchConfiguration('fused_topic_0').perform(context)
    frame_id_0 = LaunchConfiguration('frame_id_0').perform(context)
    parent_frame = LaunchConfiguration('parent_frame').perform(context)
    imu_frequency = LaunchConfiguration('imu_frequency').perform(context)
    launch_imu_node = LaunchConfiguration('launch_imu_node').perform(context) == 'true'

    nodes = []
    
    # Conditionally launch IMU node (disable if using unified node)
    if launch_imu_node:
        nodes.append(
            Node(
                package='oakd_perception',
                executable='oakd_imu_node',
                name='oakd_imu_node_0',
                output='screen',
                parameters=[
                    {'topic_name': raw_topic_0},
                    {'frame_id': frame_id_0},
                    {'imu_frequency': int(imu_frequency)},
                ],
            )
        )
    
    # Always launch fusion node (filtering only, no TF)
    # TF is now handled by EKF (odom→base_link) + static transforms (base_link→oakd_imu_link)
    nodes.append(
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
    )
    
    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('raw_topic_0', default_value='/oakd/imu/raw'),
        DeclareLaunchArgument('fused_topic_0', default_value='/oakd/imu/fused'),
        DeclareLaunchArgument('frame_id_0', default_value='oakd_imu_link'),
        DeclareLaunchArgument('parent_frame', default_value='map'),
        DeclareLaunchArgument('imu_frequency', default_value='400'),
        DeclareLaunchArgument('num_imus', default_value='1'),
        DeclareLaunchArgument('launch_imu_node', default_value='false', description='Set to true to launch oakd_imu_node (disable when using oakd_unified_node)'),
        
        # Secondary IMU arguments (for convenience)
        DeclareLaunchArgument('raw_topic_1', default_value='/imu_1/raw'),
        DeclareLaunchArgument('fused_topic_1', default_value='/imu_1'),
        DeclareLaunchArgument('frame_id_1', default_value='oakd_imu_link_1'),
        
        # Tertiary IMU arguments (for convenience)
        DeclareLaunchArgument('raw_topic_2', default_value='/imu_2/raw'),
        DeclareLaunchArgument('fused_topic_2', default_value='/imu_2'),
        DeclareLaunchArgument('frame_id_2', default_value='oakd_imu_link_2'),
        
        OpaqueFunction(function=launch_setup),
    ])
