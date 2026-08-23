#!/usr/bin/env bash
set -euo pipefail

pi_host="${ROBOTICS_RND_PI_HOST:-pi-rnd}"
dataset=""
calibration=""
sensor_model=""
tag_size_m=""
output=""

while (($#)); do
  case "$1" in
    --host) pi_host="$2"; shift 2 ;;
    --dataset) dataset="$2"; shift 2 ;;
    --calibration) calibration="$2"; shift 2 ;;
    --sensor-model) sensor_model="$2"; shift 2 ;;
    --tag-size-m) tag_size_m="$2"; shift 2 ;;
    --output) output="$2"; shift 2 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

if [[ ! "$pi_host" =~ ^[A-Za-z0-9._-]+$ ]] || [[ -z "$dataset" || -z "$calibration" || -z "$sensor_model" || -z "$tag_size_m" || -z "$output" ]]; then
  printf 'host, dataset, calibration, sensor model, measured tag size, and output are required\n' >&2
  exit 2
fi

printf -v remote_command '%q ' python3 -m robotics_rnd.edge benchmark --dataset "$dataset" --calibration "$calibration" --sensor-model "$sensor_model" --tag-size-m "$tag_size_m" --output "$output" --host-label raspberry-pi-edge-anonymized --cpu-label raspberry-pi-4-cpu
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 "$pi_host" "$remote_command"
