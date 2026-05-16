# Copyright 2026 UAV Vision WS
# Licensed under the Apache License, Version 2.0

"""
UAV GPS 融合 Launch 文件

启动三个节点:
  1. ekf_filter_node_odom  — 局部 EKF (odom→base_link)
  2. ekf_filter_node_map   — 全局 EKF (map→odom)
  3. navsat_transform       — GPS WGS84→ENU 转换

数据流:
  VINS /odometry ──┬──→ ekf_odom → /odometry/local
                   └──→ ekf_map  → /odometry/global
  px4  /imu ───────┬──→ ekf_odom
                   └──→ ekf_map
  px4  /gps/fix ──→ navsat_transform → /odometry/gps → ekf_map
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
import launch_ros.actions
import os
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    robot_localization_dir = get_package_share_directory('robot_localization')
    parameters_file_path = os.path.join(
        robot_localization_dir, 'params', 'uav_gps_fusion.yaml'
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'output_final_position',
            default_value='false',
        ),

        # ── EKF 1: 局部里程计 (odom 坐标系) ──
        launch_ros.actions.Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_odom',
            output='screen',
            parameters=[parameters_file_path],
            remappings=[
                ('odometry/filtered', 'odometry/local'),
            ],
        ),

        # ── EKF 2: 全局定位 (map 坐标系) ──
        launch_ros.actions.Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node_map',
            output='screen',
            parameters=[parameters_file_path],
            remappings=[
                ('odometry/filtered', 'odometry/global'),
            ],
        ),

        # ── NavSat Transform: GPS→ENU ──
        launch_ros.actions.Node(
            package='robot_localization',
            executable='navsat_transform_node',
            name='navsat_transform',
            output='screen',
            parameters=[parameters_file_path],
            remappings=[
                ('imu',              'imu'),
                ('gps/fix',          'gps/fix'),
                ('gps/filtered',     'gps/filtered'),
                ('odometry/gps',     'odometry/gps'),
                ('odometry/filtered', 'odometry/global'),
            ],
        ),
    ])
