#!/bin/bash
# 包内脚本：平衡模式 - 使用YAML配置

set -e

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../../.. && pwd)"
CONFIG_FILE="${WORKSPACE_DIR}/src/oakd_perception/config/balanced_mode.yaml"

echo "============================================="
echo "启动 OAK-D 统一节点 - 平衡模式"
echo "使用配置: $CONFIG_FILE"
echo "============================================="

# 使用 with_venv.sh 包装器确保环境正确（包含 ROS 2 和虚拟环境依赖）
"${WORKSPACE_DIR}/scripts/with_venv.sh" ros2 launch oakd_perception oakd_unified.launch.py params_file:="$CONFIG_FILE"
