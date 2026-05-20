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
EXPECTED_FRAME="${OFFLINE_MAP_EXPECTED_FRAME:-map}"

usage() {
  cat <<'EOF'
Usage:
  scripts/check_offline_map.sh [options]

Defaults are read from scripts/nav_launch.env and optional
scripts/nav_launch.local.env. Command-line options override variables.

Options:
  --frame <frame_id>
      Expected map frame. Default: map.

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
    --frame)
      require_value "$1" "${2:-}"
      EXPECTED_FRAME="$2"
      shift 2
      ;;
    --frame=*)
      EXPECTED_FRAME="${1#*=}"
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

print_header "Offline Map Topics"
require_topic /static_map/occupancy
require_topic /local_map/sensor_occupancy
require_topic /local_map/occupancy

print_header "Messages"
check_topic_once /static_map/occupancy static_map transient_local
check_topic_once /local_map/sensor_occupancy sensor_map
check_topic_once /local_map/occupancy fused_map

print_header "Frames"
check_frame_id /static_map/occupancy "$EXPECTED_FRAME" transient_local
check_frame_id /local_map/sensor_occupancy "$EXPECTED_FRAME"
check_frame_id /local_map/occupancy "$EXPECTED_FRAME"

print_header "Rates"
check_topic_hz /local_map/sensor_occupancy sensor_map
check_topic_hz /local_map/occupancy fused_map

finish_report
