#!/usr/bin/env bash
set -eo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

POINTCLOUD_SOURCE="oakd"
ENABLE_BRIDGE="false"
PLANNER="se2_dwa"
DRY_RUN="false"
EXTRA_ARGS=()

usage() {
  cat <<'EOF'
Usage:
  scripts/run_omni_nav.sh [options] [launch_arg:=value ...]

Options:
  --pointcloud-source <oakd|mid360|both>
      Obstacle point cloud source. Default: oakd.

  --bridge / --no-bridge
      Enable or disable ground_serial_bridge output to the base. Default: disabled.

  --planner <se2_dwa|dwb>
      Local planner to launch. Default: se2_dwa.

  --dry-run
      Print the resolved ros2 launch command without executing it.

Examples:
  scripts/run_omni_nav.sh
  scripts/run_omni_nav.sh --bridge
  scripts/run_omni_nav.sh --pointcloud-source mid360
  scripts/run_omni_nav.sh --pointcloud-source both --bridge
  scripts/run_omni_nav.sh --planner dwb --pointcloud-source oakd
EOF
}

require_value() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "$option requires a value" >&2
    exit 2
  fi
}

validate_pointcloud_source() {
  case "$POINTCLOUD_SOURCE" in
    oakd|mid360|both) ;;
    *)
      echo "Invalid pointcloud source: $POINTCLOUD_SOURCE (expected oakd, mid360, or both)" >&2
      exit 2
      ;;
  esac
}

validate_planner() {
  case "$PLANNER" in
    se2_dwa|dwb) ;;
    *)
      echo "Invalid planner: $PLANNER (expected se2_dwa or dwb)" >&2
      exit 2
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|help)
      usage
      exit 0
      ;;
    --pointcloud-source|--cloud-source)
      require_value "$1" "${2:-}"
      POINTCLOUD_SOURCE="$2"
      shift 2
      ;;
    --pointcloud-source=*|--cloud-source=*)
      POINTCLOUD_SOURCE="${1#*=}"
      shift
      ;;
    --bridge)
      ENABLE_BRIDGE="true"
      shift
      ;;
    --no-bridge)
      ENABLE_BRIDGE="false"
      shift
      ;;
    --planner)
      require_value "$1" "${2:-}"
      PLANNER="$2"
      shift 2
      ;;
    --planner=*)
      PLANNER="${1#*=}"
      shift
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    --)
      shift
      EXTRA_ARGS+=("$@")
      break
      ;;
    *)
      if [[ "$1" != *:=* ]]; then
        echo "Unknown option or launch argument: $1" >&2
        echo "Launch arguments must use name:=value syntax." >&2
        echo "Run scripts/run_omni_nav.sh --help for examples." >&2
        exit 2
      fi
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

validate_pointcloud_source
validate_planner

ENABLE_OAKD_PERCEPTION="false"
ENABLE_MID360="false"

case "$POINTCLOUD_SOURCE" in
  oakd)
    ENABLE_OAKD_PERCEPTION="true"
    ;;
  mid360)
    ENABLE_MID360="true"
    ;;
  both)
    ENABLE_OAKD_PERCEPTION="true"
    ENABLE_MID360="true"
    ;;
esac

LAUNCH_SE2_DWA="false"
LAUNCH_DWB="false"
case "$PLANNER" in
  se2_dwa)
    LAUNCH_SE2_DWA="true"
    ;;
  dwb)
    LAUNCH_DWB="true"
    ;;
esac

LAUNCH_ARGS=(
  obstacle_pointcloud_source:="$POINTCLOUD_SOURCE"
  enable_oakd_perception:="$ENABLE_OAKD_PERCEPTION"
  enable_mid360:="$ENABLE_MID360"
  enable_ground_serial_bridge:="$ENABLE_BRIDGE"
  launch_se2_dwa:="$LAUNCH_SE2_DWA"
  launch_dwb:="$LAUNCH_DWB"
)

CMD=(
  "$WS_DIR/scripts/with_venv.sh"
  ros2
  launch
  omni_bringup
  omni_nav.launch.py
  "${LAUNCH_ARGS[@]}"
  "${EXTRA_ARGS[@]}"
)

echo "Omni navigation launch:"
echo "  pointcloud source: $POINTCLOUD_SOURCE"
echo "  OAK-D perception : $ENABLE_OAKD_PERCEPTION"
echo "  MID360           : $ENABLE_MID360"
echo "  planner          : $PLANNER"
echo "  serial bridge    : $ENABLE_BRIDGE"

if [[ "$DRY_RUN" == "true" ]]; then
  printf 'Command:'
  printf ' %q' "${CMD[@]}"
  printf '\n'
  exit 0
fi

exec "${CMD[@]}"
