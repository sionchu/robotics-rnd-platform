#!/usr/bin/env bash
set -euo pipefail

pi_host="${ROBOTICS_RND_PI_HOST:-pi-rnd}"
remote_output=""
frames=100
camera_mode=""

while (($#)); do
  case "$1" in
    --host) pi_host="$2"; shift 2 ;;
    --output) remote_output="$2"; shift 2 ;;
    --frames) frames="$2"; shift 2 ;;
    --camera-mode) camera_mode="$2"; shift 2 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ ! "$pi_host" =~ ^[A-Za-z0-9._-]+$ ]] || [[ ! "$remote_output" =~ ^[A-Za-z0-9._/-]+$ ]] || [[ "$remote_output" == *..* ]]; then
  printf 'safe --host and --output values are required\n' >&2
  exit 2
fi
if [[ ! "$frames" =~ ^[1-9][0-9]*$ ]] || [[ -z "$camera_mode" ]]; then
  printf 'positive --frames and detected --camera-mode are required\n' >&2
  exit 2
fi

printf -v remote_command '%q ' python3 -m robotics_rnd.edge capture --output "$remote_output" --frames "$frames" --camera-mode "$camera_mode"
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 "$pi_host" "$remote_command"
