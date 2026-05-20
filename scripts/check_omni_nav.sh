#!/usr/bin/env bash
set -eo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$WS_DIR/scripts/nav_launch.env" ]]; then
  source "$WS_DIR/scripts/nav_launch.env"
fi
if [[ -f "$WS_DIR/scripts/nav_launch.local.env" ]]; then
  source "$WS_DIR/scripts/nav_launch.local.env"
fi

TIMEOUT_SEC="${DEBUG_TIMEOUT_SEC:-4}"
CHECK_BRIDGE="${CHECK_OMNI_BRIDGE:-false}"
CHECK_OFFLINE_MAP="${CHECK_OMNI_OFFLINE_MAP:-false}"

usage() {
  cat <<'EOF'
Usage:
  scripts/check_omni_nav.sh [options]

Defaults are read from scripts/nav_launch.env and optional
scripts/nav_launch.local.env. Command-line options override variables.

Options:
  --bridge
      Also check ground_serial_bridge output topics.

  --offline-map
      Also check offline static map fusion topics.

  --timeout <sec>
      Per-check timeout. Default: 4.

  -h, --help
      Show this help.
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bridge)
      CHECK_BRIDGE="true"
      shift
      ;;
    --offline-map)
      CHECK_OFFLINE_MAP="true"
      shift
      ;;
    --timeout)
      require_value "$1" "${2:-}"
      TIMEOUT_SEC="$2"
      shift 2
      ;;
    --timeout=*)
      TIMEOUT_SEC="${1#*=}"
      shift
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

source "$WS_DIR/scripts/nav_debug_lib.sh"

print_header "Omni Navigation Topics"
require_topic /tf
require_topic /tf_static
require_topic /local_map/occupancy
require_topic /nav/cmd_vel
require_topic /nav/emergency
require_topic /nav/safety_status
optional_topic /oakd/points_filtered
optional_topic /mid360/points
optional_topic /perception/obstacle_points

print_header "Rates"
check_topic_hz /local_map/occupancy local_map
check_topic_hz /nav/cmd_vel cmd_vel
check_topic_hz /nav/emergency emergency

print_header "Frames"
check_frame_id /local_map/occupancy map
check_tf map base_link

if [[ "$CHECK_OFFLINE_MAP" == "true" ]]; then
  print_header "Offline Map Fusion"
  require_topic /static_map/occupancy
  require_topic /local_map/sensor_occupancy
  check_frame_id /static_map/occupancy map transient_local
  check_frame_id /local_map/sensor_occupancy map
fi

if [[ "$CHECK_BRIDGE" == "true" ]]; then
  print_header "Ground Serial Bridge"
  require_topic /base/state
  require_topic /base/status
  require_topic /base/diagnostics
  check_topic_hz /base/state base_state
fi

finish_report
