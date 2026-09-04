#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
version=${1:-0.1.0}
output_dir="$repo_root/dist"
staging_dir=$(mktemp -d)
trap 'rm -rf "$staging_dir"' EXIT

mkdir -p "$output_dir" "$staging_dir/custom_components"
cp -R "$repo_root/custom_components/biofects_butler" "$staging_dir/custom_components/"
cp "$repo_root/hacs.json" "$staging_dir/hacs.json"
find "$staging_dir" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$staging_dir" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

archive="$output_dir/biofects-butler-ha-$version.zip"
rm -f "$archive" "$archive.sha256"
(
    cd "$staging_dir"
    zip -qr "$archive" custom_components hacs.json
)
sha256sum "$archive" > "$archive.sha256"
printf '%s\n' "$archive"