#!/usr/bin/env bash
set -eo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WS_DIR"

apply_patch_if_needed() {
  local repo_dir="$1"
  local patch_file="$2"

  if [ ! -d "$repo_dir" ]; then
    echo "Missing $repo_dir. Run: git submodule update --init --recursive" >&2
    exit 1
  fi

  if (cd "$repo_dir" && git apply --check "$WS_DIR/$patch_file" >/dev/null 2>&1); then
    (cd "$repo_dir" && git apply "$WS_DIR/$patch_file")
    echo "Applied $patch_file"
  elif (cd "$repo_dir" && git apply --reverse --check "$WS_DIR/$patch_file" >/dev/null 2>&1); then
    echo "Already applied $patch_file"
  else
    echo "Cannot apply $patch_file cleanly in $repo_dir" >&2
    exit 1
  fi
}

apply_patch_if_needed "src/livox_ros_driver2" "patches/vendor/livox_ros_driver2.patch"
apply_patch_if_needed "src/FAST_LIO_ROS2" "patches/vendor/fast_lio_ros2.patch"
apply_patch_if_needed "third_party/Livox-SDK2" "patches/vendor/livox_sdk2.patch"
