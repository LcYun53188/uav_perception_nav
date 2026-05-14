#!/bin/bash
# 兼容入口：转发到包内脚本

set -e

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
TARGET_SCRIPT="$WORKSPACE_DIR/src/oakd_perception/scripts/run_oakd_active_max.sh"

if [ ! -f "$TARGET_SCRIPT" ]; then
  echo "错误: 找不到包内脚本: $TARGET_SCRIPT"
  exit 1
fi

exec "$TARGET_SCRIPT"
