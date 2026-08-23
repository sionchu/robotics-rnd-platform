#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

python -m pytest
python -m experiments.vision.run_all all --verify-only
python -m experiments.vision.pi_edge verify-preparation
python -m ruff check .
python -m ruff format --check .
python -m mypy

cmake -S cpp -B cpp/build -G Ninja
cmake --build cpp/build
ctest --test-dir cpp/build --output-on-failure

python scripts/doctor.py >/dev/null
python -m applications.vision_lab.mock_guidance >/dev/null
echo "All generic quality gates passed."
