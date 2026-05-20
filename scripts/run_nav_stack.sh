#!/usr/bin/env bash
set -eo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$WS_DIR/scripts/nav_launch.env" ]]; then
  source "$WS_DIR/scripts/nav_launch.env"
fi
if [[ -f "$WS_DIR/scripts/nav_launch.local.env" ]]; then
  source "$WS_DIR/scripts/nav_launch.local.env"
fi

ODOM_SOURCE="${NAV_ODOM_SOURCE:-vio}"
POINTCLOUD_SOURCE="${NAV_POINTCLOUD_SOURCE:-oakd}"
ENABLE_GPS="${NAV_ENABLE_GPS:-false}"
DRY_RUN="false"
EXTRA_ARGS=()
if declare -p NAV_EXTRA_ARGS >/dev/null 2>&1; then
  EXTRA_ARGS=("${NAV_EXTRA_ARGS[@]}")
fi

usage() {
  cat <<'EOF'
Usage:
  scripts/run_nav_stack.sh [options] [launch_arg:=value ...]

Defaults are read from scripts/nav_launch.env and optional
scripts/nav_launch.local.env. Command-line options override variables.

Options:
  --odom-source <vio|lio|both>
      EKF odometry source. Default: vio.

  --pointcloud-source <oakd|mid360|both>
      Obstacle point cloud source. Default: oakd.

  --gps / --no-gps
      Enable or disable GPS fusion. Default: disabled.

  --dry-run
      Print the resolved ros2 launch command without executing it.

Examples:
  scripts/run_nav_stack.sh
  scripts/run_nav_stack.sh --gps
  scripts/run_nav_stack.sh --odom-source vio --pointcloud-source mid360
  scripts/run_nav_stack.sh --odom-source both --pointcloud-source both
  scripts/run_nav_stack.sh --odom-source lio --pointcloud-source mid360 mid360_x:=0.08 mid360_z:=0.05
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

validate_source() {
  local label="$1"
  local value="$2"
  local allowed="$3"

  if [[ "$allowed" == "odom" ]]; then
    case "$value" in
      vio|lio|both) return 0 ;;
    esac
  else
    case "$value" in
      oakd|mid360|both) return 0 ;;
    esac
  fi

  if [[ "$allowed" == "odom" ]]; then
    echo "Invalid $label: $value (expected vio, lio, or both)" >&2
  else
    echo "Invalid $label: $value (expected oakd, mid360, or both)" >&2
  fi
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help|help)
      usage
      exit 0
      ;;
    --odom-source)
      require_value "$1" "${2:-}"
      ODOM_SOURCE="$2"
      shift 2
      ;;
    --odom-source=*)
      ODOM_SOURCE="${1#*=}"
      shift
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
    --gps)
      ENABLE_GPS="true"
      shift
      ;;
    --no-gps)
      ENABLE_GPS="false"
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
        echo "Run scripts/run_nav_stack.sh --help for examples." >&2
        exit 2
      fi
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

validate_source "odometry source" "$ODOM_SOURCE" "odom"
validate_source "pointcloud source" "$POINTCLOUD_SOURCE" "pointcloud"

ENABLE_VINS="false"
ENABLE_LIO="false"
ENABLE_OAKD_PERCEPTION="false"
ENABLE_IMU_FUSION="false"
ENABLE_MID360="false"

case "$ODOM_SOURCE" in
  vio)
    ENABLE_VINS="true"
    ENABLE_OAKD_PERCEPTION="true"
    ENABLE_IMU_FUSION="true"
    ;;
  lio)
    ENABLE_LIO="true"
    ENABLE_MID360="true"
    ;;
  both)
    ENABLE_VINS="true"
    ENABLE_LIO="true"
    ENABLE_OAKD_PERCEPTION="true"
    ENABLE_IMU_FUSION="true"
    ENABLE_MID360="true"
    ;;
esac

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

LAUNCH_ARGS=(
  enable_gps:="$ENABLE_GPS"
  odometry_source:="$ODOM_SOURCE"
  obstacle_pointcloud_source:="$POINTCLOUD_SOURCE"
  enable_oakd_perception:="$ENABLE_OAKD_PERCEPTION"
  enable_imu_fusion:="$ENABLE_IMU_FUSION"
  enable_vins:="$ENABLE_VINS"
  enable_mid360:="$ENABLE_MID360"
  enable_lio:="$ENABLE_LIO"
)

CMD=(
  "$WS_DIR/scripts/with_venv.sh"
  ros2
  launch
  uav_bringup
  nav_stack.launch.py
  "${LAUNCH_ARGS[@]}"
  "${EXTRA_ARGS[@]}"
)

echo "Navigation launch:"
echo "  odometry source  : $ODOM_SOURCE"
echo "  pointcloud source: $POINTCLOUD_SOURCE"
echo "  GPS fusion       : $ENABLE_GPS"
echo "  OAK-D perception : $ENABLE_OAKD_PERCEPTION"
echo "  VINS             : $ENABLE_VINS"
echo "  MID360           : $ENABLE_MID360"
echo "  FAST-LIO         : $ENABLE_LIO"

if [[ "$DRY_RUN" == "true" ]]; then
  printf 'Command:'
  printf ' %q' "${CMD[@]}"
  printf '\n'
  exit 0
fi

exec "${CMD[@]}"
