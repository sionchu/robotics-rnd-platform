#!/usr/bin/env bash
set -euo pipefail

pi_host="${ROBOTICS_RND_PI_HOST:-pi-rnd}"
remote_session=""
local_root="datasets/local/pi_camera"
execute=false

while (($#)); do
  case "$1" in
    --host) pi_host="$2"; shift 2 ;;
    --remote-session) remote_session="$2"; shift 2 ;;
    --local-root) local_root="$2"; shift 2 ;;
    --execute) execute=true; shift ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ ! "$pi_host" =~ ^[A-Za-z0-9._-]+$ ]] || [[ ! "$remote_session" =~ ^[A-Za-z0-9._/-]+$ ]] || [[ "$remote_session" == *..* ]]; then
  printf 'safe --host and --remote-session values are required\n' >&2
  exit 2
fi
if [[ "$local_root" == /* ]] || [[ "$local_root" == *..* ]]; then
  printf 'local root must be a repository-relative path without ..\n' >&2
  exit 2
fi

mkdir -p "$local_root"
rsync_arguments=(-av --itemize-changes --protect-args)
if [[ "$execute" != true ]]; then
  rsync_arguments+=(--dry-run)
fi
rsync "${rsync_arguments[@]}" "$pi_host:$remote_session/" "$local_root/$(basename "$remote_session")/"
if [[ "$execute" != true ]]; then
  printf 'Dry run only. Re-run with --execute after reviewing the file list.\n'
fi
