from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    vins_share_dir = get_package_share_directory('vins_fusion_ros2')
    
    config_file = os.path.join(
        vins_share_dir,
        'config',
        'oakd',
        'oakd_stereo_imu_config.yaml'
    )
    
    rviz_config = os.path.join(
        vins_share_dir,
        'config',
        'vins_rviz_config.rviz'
    )

    return LaunchDescription([
        # VINS-Fusion core estimator node
        Node(
            package='vins_fusion_ros2',
            executable='vins_fusion_ros2_node',
            name='vins_fusion_ros2_node',
            output='screen',
            emulate_tty=True,
            parameters=[{'use_sim_time': False},
                        {'config_file': config_file}],
        ),
        
        # RViz2 for visualization
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': False}]
        )
    ])
