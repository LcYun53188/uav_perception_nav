#!/usr/bin/env bash
set -eo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-oakd}"
shift || true

usage() {
  cat <<'EOF'
Usage:
  scripts/run_nav_stack.sh [mode] [extra launch args...]

Modes:
  oakd          Default OAK-D + VINS navigation stack
  gps           OAK-D + VINS + GPS fusion
  mid360        MID360 replaces OAK-D point cloud for obstacle mapping
  both          OAK-D and MID360 point clouds are combined
  mid360_lio    OAK-D VIO + MID360 FAST-LIO2 as peer odometry sources
  mid360_only   Disable OAK-D perception/IMU fusion/VINS, use MID360 + FAST-LIO2

Examples:
  scripts/run_nav_stack.sh oakd
  scripts/run_nav_stack.sh mid360 mid360_x:=0.08 mid360_z:=0.05
  scripts/run_nav_stack.sh mid360_only enable_gps:=true
EOF
}

case "$MODE" in
  -h|--help|help)
    usage
    exit 0
    ;;
  oakd)
    ARGS=()
    ;;
  gps)
    ARGS=(enable_gps:=true)
    ;;
  mid360)
    ARGS=(
      enable_mid360:=true
      obstacle_pointcloud_source:=mid360
    )
    ;;
  both)
    ARGS=(
      enable_mid360:=true
      obstacle_pointcloud_source:=both
    )
    ;;
  mid360_lio)
    ARGS=(
      enable_mid360:=true
      enable_lio:=true
      obstacle_pointcloud_source:=both
    )
    ;;
  mid360_only)
    ARGS=(
      enable_oakd_perception:=false
      enable_imu_fusion:=false
      enable_vins:=false
      enable_mid360:=true
      enable_lio:=true
      obstacle_pointcloud_source:=mid360
    )
    ;;
  *)
    echo "Unknown nav stack mode: $MODE" >&2
    usage >&2
    exit 2
    ;;
esac

exec "$WS_DIR/scripts/with_venv.sh" ros2 launch uav_bringup nav_stack.launch.py "${ARGS[@]}" "$@"
