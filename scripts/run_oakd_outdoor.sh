#!/bin/bash
# 快速启动脚本：户外强光 - 纯被动立体（低功耗）

echo "============================================="
echo "启动 OAK-D 点云节点 - 户外低功耗模式"
echo "============================================="
echo "配置: 纯被动立体(IR关闭)"
echo ""

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
cd "$WORKSPACE_DIR"

"$WORKSPACE_DIR"/scripts/with_venv.sh "$WORKSPACE_DIR"/.venv/bin/oakd_depth_node \
  --ros-args \
  -p enable_passive_stereo:=true \
  -p enable_active_stereo:=false
