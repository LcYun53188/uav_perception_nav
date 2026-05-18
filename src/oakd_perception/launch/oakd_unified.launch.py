import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    params_file = LaunchConfiguration("params_file").perform(context)

    # 基础参数字典
    base_params = {
        "imu_frequency": int(LaunchConfiguration("imu_frequency").perform(context)),
        "pointcloud_frequency": int(
            LaunchConfiguration("pointcloud_frequency").perform(context)
        ),
        "enable_passive_stereo": LaunchConfiguration("enable_passive_stereo").perform(
            context
        )
        == "true",
        "enable_active_stereo": LaunchConfiguration("enable_active_stereo").perform(
            context
        )
        == "true",
        "ir_intensity": int(LaunchConfiguration("ir_intensity").perform(context)),
        "sampling_step": int(LaunchConfiguration("sampling_step").perform(context)),
        "min_depth": int(LaunchConfiguration("min_depth").perform(context)),
        "max_depth": int(LaunchConfiguration("max_depth").perform(context)),
        "depth_border_crop_px": int(
            LaunchConfiguration("depth_border_crop_px").perform(context)
        ),
        "max_depth_jump_mm": int(
            LaunchConfiguration("max_depth_jump_mm").perform(context)
        ),
        "enable_fov_boundary_filter": LaunchConfiguration(
            "enable_fov_boundary_filter"
        ).perform(context)
        == "true",
        "auto_estimate_fov": LaunchConfiguration("auto_estimate_fov").perform(
            context
        )
        == "true",
        "fov_h_deg": float(LaunchConfiguration("fov_h_deg").perform(context)),
        "fov_v_deg": float(LaunchConfiguration("fov_v_deg").perform(context)),
        "fov_boundary_margin_m": float(
            LaunchConfiguration("fov_boundary_margin_m").perform(context)
        ),
        "imu_topic_name": LaunchConfiguration("imu_topic").perform(context),
        "pointcloud_topic": LaunchConfiguration("pointcloud_topic").perform(context),
        "filtered_pointcloud_topic": LaunchConfiguration(
            "filtered_pointcloud_topic"
        ).perform(context),
        "imu_frame_id": LaunchConfiguration("imu_frame_id").perform(context),
        "pointcloud_frame_id": LaunchConfiguration("pointcloud_frame_id").perform(
            context
        ),
    }

    node_params = [base_params]

    # 如果指定了 YAML 文件，则将其加入参数列表（它将覆盖之前的参数）
    if params_file and os.path.exists(params_file):
        node_params.append(params_file)

    oakd_unified_node = Node(
        package="oakd_perception",
        executable="oakd_unified_node",
        name="oakd_unified",
        output="screen",
        parameters=node_params,
    )

    # 静态变换：oakd_imu_link (重力中心) -> oakd_camera_optical_frame (镜头中心)
    # 修正：
    # 1. 绕 Z 轴翻转 180 度 (由上一步完成)
    # 2. 再绕相机的 X 轴逆时针旋转 90 度 (+1.57 rad)
    # 最终参数：yaw=1.57, pitch=0, roll=3.14
    static_tf_node = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="imu_to_camera_tf",
        arguments=[
            "0",
            "0",
            "0",
            "1.57",
            "0",
            "3.14",
            "oakd_imu_link",
            "oakd_camera_optical_frame",
        ],
    )

    return [oakd_unified_node, static_tf_node]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file", default_value="", description="YAML参数文件的路径"
            ),
            DeclareLaunchArgument("imu_frequency", default_value="400"),
            DeclareLaunchArgument("pointcloud_frequency", default_value="20"),
            DeclareLaunchArgument("enable_passive_stereo", default_value="true"),
            DeclareLaunchArgument("enable_active_stereo", default_value="false"),
            DeclareLaunchArgument("ir_intensity", default_value="1600"),
            DeclareLaunchArgument("sampling_step", default_value="2"),
            DeclareLaunchArgument("min_depth", default_value="200"),
            DeclareLaunchArgument("max_depth", default_value="5000"),
            DeclareLaunchArgument("depth_border_crop_px", default_value="8"),
            DeclareLaunchArgument("max_depth_jump_mm", default_value="350"),
            DeclareLaunchArgument(
                "enable_fov_boundary_filter", default_value="true"
            ),
            DeclareLaunchArgument("auto_estimate_fov", default_value="true"),
            DeclareLaunchArgument("fov_h_deg", default_value="72.0"),
            DeclareLaunchArgument("fov_v_deg", default_value="53.0"),
            DeclareLaunchArgument(
                "fov_boundary_margin_m", default_value="0.15"
            ),
            DeclareLaunchArgument("imu_topic", default_value="/oakd/imu/raw"),
            DeclareLaunchArgument("pointcloud_topic", default_value="/oakd/points"),
            DeclareLaunchArgument(
                "filtered_pointcloud_topic", default_value="/oakd/points_filtered"
            ),
            DeclareLaunchArgument("imu_frame_id", default_value="oakd_imu_link"),
            DeclareLaunchArgument(
                "pointcloud_frame_id", default_value="oakd_camera_optical_frame"
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )
