#!/bin/bash
# OAK-D 统一节点入口脚本 - 转发到包内配置脚本

set -e

# 可选模式: balance, indoor, outdoor, active_max
TARGET_MODE="balance"

WORKSPACE_DIR="/home/nuc/Program/uav_vision_ws"
PACKAGE_SCRIPTS_DIR="${WORKSPACE_DIR}/src/oakd_perception/scripts"
TARGET_SCRIPT="${PACKAGE_SCRIPTS_DIR}/run_oakd_${TARGET_MODE}.sh"

print_banner() {
    echo ""
    echo "=========================================================="
    echo "$1"
    echo "=========================================================="
    echo ""
}

# 检查脚本是否存在
if [ ! -f "$TARGET_SCRIPT" ]; then
    echo "错误：无法找到目标脚本 $TARGET_SCRIPT"
    echo "可用模式: balance, indoor, outdoor, active_max"
    exit 1
fi

print_banner "OAK-D 统一节点转发"
echo "  模式: $TARGET_MODE"
echo "  脚本: $TARGET_SCRIPT"

# 执行目标脚本
exec "$TARGET_SCRIPT"
