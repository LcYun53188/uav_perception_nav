#!/bin/bash
# IMU融合 + TF广播独立启动脚本
# 独立入口：订阅 OAK-D 原始 IMU，并输出融合结果与 TF

set -e

WORKSPACE="/home/nuc/Program/uav_vision_ws"
SOURCE_SETUP="${WORKSPACE}/install/setup.bash"
IMU_RAW_TOPIC="/oakd/imu/raw"
IMU_FUSED_TOPIC="/imu"
IMU_FRAME_ID="oakd_imu_link"
IMU_PARENT_FRAME="map"

if [ ! -f "$SOURCE_SETUP" ]; then
    echo "❌ 错误：找不到setup.bash"
    exit 1
fi

source "$SOURCE_SETUP"

print_banner() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "$1"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
}

print_banner "🧭 IMU 融合 + TF 广播"
echo "启动配置:"
echo "  • IMU 原始话题 : ${IMU_RAW_TOPIC}"
echo "  • IMU 融合话题 : ${IMU_FUSED_TOPIC}"
echo "  • TF 子坐标系  : ${IMU_FRAME_ID}"
echo "  • TF 父坐标系  : ${IMU_PARENT_FRAME}"
echo ""
echo "处理链路:"
echo "  ${IMU_RAW_TOPIC} → imu_fusion_node → ${IMU_FUSED_TOPIC} → imu_tf_broadcaster"
echo ""
echo "输出统计:"
echo "  • ${IMU_FUSED_TOPIC} : 100Hz"
echo "  • /tf : 动态 (map → ${IMU_FRAME_ID})"
echo ""
echo "准备启动..."
echo ""

ros2 launch imu_fusion imu_fusion.launch.py \
    launch_imu_node:=false \
    raw_topic_0:=${IMU_RAW_TOPIC} \
    fused_topic_0:=${IMU_FUSED_TOPIC} \
    frame_id_0:=${IMU_FRAME_ID} \
    parent_frame:=${IMU_PARENT_FRAME}
