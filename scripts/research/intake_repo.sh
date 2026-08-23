#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <https-git-url> <slug> [--ref <tag-or-commit>] [--execute]"
  echo "default is a dry run; clones only into ignored .external/intake/<slug>"
}

if [[ $# -lt 2 ]]; then
  usage
  exit 2
fi

repository_url=$1
slug=$2
shift 2
review_ref=HEAD
execute=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      review_ref=$2
      shift 2
      ;;
    --execute)
      execute=true
      shift
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

[[ "$repository_url" =~ ^https://[^[:space:]]+\.git$ ]] || {
  echo "error: use an explicit HTTPS .git URL" >&2
  exit 2
}
[[ "$slug" =~ ^[a-z0-9][a-z0-9._-]*$ ]] || {
  echo "error: slug must contain only lowercase letters, digits, dot, underscore, or dash" >&2
  exit 2
}
[[ "$review_ref" != -* && "$review_ref" != *[[:space:]]* ]] || {
  echo "error: invalid ref" >&2
  exit 2
}

project_root=$(git rev-parse --show-toplevel)
scratch_root="$project_root/.external/intake"
destination="$scratch_root/$slug"

echo "repository=$repository_url"
echo "ref=$review_ref"
echo "destination=.external/intake/$slug"
echo "external_code_execution=false"

if [[ "$execute" != true ]]; then
  echo "status=DRY_RUN"
  exit 0
fi

[[ ! -e "$destination" ]] || {
  echo "error: destination already exists; inspect it or choose another slug" >&2
  exit 2
}

mkdir -p "$scratch_root"
git clone --filter=blob:none --no-checkout "$repository_url" "$destination"
git -C "$destination" checkout --detach "$review_ref"

reviewed_commit=$(git -C "$destination" rev-parse HEAD)
echo "status=CLONED_FOR_INSPECTION"
echo "commit=$reviewed_commit"

license_found=false
for candidate in LICENSE LICENSE.txt LICENSE.md COPYING COPYING.txt; do
  if [[ -f "$destination/$candidate" ]]; then
    echo "license_file=$candidate"
    sed -n '1,12p' "$destination/$candidate"
    license_found=true
    break
  fi
done
if [[ "$license_found" != true ]]; then
  echo "license_file=NOT_FOUND_AT_ROOT"
fi

echo "next=inspect README, package metadata, changelog, examples, tests, CI, source, and issues"
echo "warning=do not execute repository scripts until separately inspected and authorized"
