#!/bin/bash
# 快速启动脚本：高精度 - 主动立体优先（最强深度）

echo "============================================="
echo "启动 OAK-D 点云节点 - 高精度主动立体模式"
echo "============================================="
echo "配置: 纯主动立体(IR=1600)"
echo ""

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
cd "$WORKSPACE_DIR"

"$WORKSPACE_DIR"/scripts/with_venv.sh "$WORKSPACE_DIR"/.venv/bin/oakd_depth_node \
  --ros-args \
  -p enable_passive_stereo:=false \
  -p enable_active_stereo:=true \
  -p ir_intensity:=1600
