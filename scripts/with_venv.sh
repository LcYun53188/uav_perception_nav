#!/usr/bin/env bash
set -eo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WS_DIR"

if [ ! -f ".venv/bin/activate" ]; then
  echo "Missing .venv. Create it with: uv venv .venv" >&2
  exit 1
fi

# Ensure project virtualenv Python is first on PATH.
source .venv/bin/activate

if [ -f /opt/ros/jazzy/setup.bash ]; then
  source /opt/ros/jazzy/setup.bash
elif [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
elif [ -f /opt/ros/iron/setup.bash ]; then
  source /opt/ros/iron/setup.bash
else
  echo "No supported ROS distro setup found under /opt/ros" >&2
  exit 1
fi

if [ -f install/setup.bash ]; then
  source install/setup.bash
fi

if [ "$#" -eq 0 ]; then
  exec bash
fi

# Force colcon to run under this virtualenv Python.
if [ "$1" = "colcon" ]; then
  shift
  exec "$VIRTUAL_ENV/bin/python" -m colcon "$@"
fi

exec "$@"
