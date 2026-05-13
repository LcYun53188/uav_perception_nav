#!/bin/bash
# 快速启动脚本：平衡模式 - 被动+主动(中等强度)

echo "============================================="
echo "启动 OAK-D 点云节点 - 平衡模式"
echo "============================================="
echo "配置: 被动立体 + 主动立体(IR=800)"
echo "推荐用于: 通用应用、SLAM建图"
echo ""

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
cd "$WORKSPACE_DIR"

"$WORKSPACE_DIR"/scripts/with_venv.sh "$WORKSPACE_DIR"/.venv/bin/oakd_depth_node \
  --ros-args \
  -p enable_passive_stereo:=true \
  -p enable_active_stereo:=true \
  -p ir_intensity:=800
