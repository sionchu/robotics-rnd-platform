#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
pi_host="${ROBOTICS_RND_PI_HOST:-pi-rnd}"
remote_dir="robotics-rnd-edge"
execute=false

while (($#)); do
  case "$1" in
    --host) pi_host="$2"; shift 2 ;;
    --remote-dir) remote_dir="$2"; shift 2 ;;
    --execute) execute=true; shift ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ ! "$pi_host" =~ ^[A-Za-z0-9._-]+$ ]] || [[ ! "$remote_dir" =~ ^[A-Za-z0-9._/-]+$ ]] || [[ "$remote_dir" == *..* ]]; then
  printf 'host/remote directory contains unsupported characters\n' >&2
  exit 2
fi

task_pi_package="$(mktemp -d)"
trap 'rm -rf -- "$task_pi_package"' EXIT
python -m pip wheel --no-deps --wheel-dir "$task_pi_package" "$project_root"
cp "$project_root/hardware/raspberry_pi/pi4_camera_node/deployment-manifest.json" "$task_pi_package/"

rsync_arguments=(-av --itemize-changes --protect-args)
if [[ "$execute" != true ]]; then
  rsync_arguments+=(--dry-run)
fi
printf 'Deployment contents:\n'
find "$task_pi_package" -maxdepth 1 -type f -printf '  %f\n' | sort
rsync "${rsync_arguments[@]}" "$task_pi_package/" "$pi_host:$remote_dir/"
if [[ "$execute" == true ]]; then
  printf 'Files copied. On the Pi, inspect the manifest and install the wheel into an isolated environment.\n'
else
  printf 'Dry run only. Re-run with --execute after reviewing the file list.\n'
fi
