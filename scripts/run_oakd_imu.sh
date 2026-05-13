#!/bin/bash

# OAK-D IMU节点启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../.."
source "$SCRIPT_DIR/scripts/with_venv.sh" ros2 run oakd_perception oakd_imu_node
