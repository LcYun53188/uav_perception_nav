#!/bin/bash
# 统一节点入口脚本 - 转发到特定的包内配置脚本

set -e

# 可选模式: balance, indoor, outdoor, active_max
TARGET_MODE="balance"

WORKSPACE_DIR="/home/nuc/Program/uav_vision_ws"
PACKAGE_SCRIPTS_DIR="${WORKSPACE_DIR}/src/oakd_perception/scripts"
TARGET_SCRIPT="${PACKAGE_SCRIPTS_DIR}/run_oakd_${TARGET_MODE}.sh"

# 检查脚本是否存在
if [ ! -f "$TARGET_SCRIPT" ]; then
    echo "错误：无法找到目标脚本 $TARGET_SCRIPT"
    echo "可用模式: balance, indoor, outdoor, active_max"
    exit 1
fi

echo "=========================================================="
echo "  转发到模式: $TARGET_MODE"
echo "  执行脚本: $TARGET_SCRIPT"
echo "=========================================================="

# 清理旧进程 - 改进模式匹配，避免杀死脚本自身
echo "清理之前的OAK-D和ROS进程..."
pkill -9 -f "oakd_.*node" || true
pkill -9 -f "imu_fusion" || true
pkill -9 -f "ros2" || true
sleep 1

# 执行目标脚本
exec "$TARGET_SCRIPT"
