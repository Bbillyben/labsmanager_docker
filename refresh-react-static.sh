#!/bin/bash
# Refresh only the React files in the persistent static volume before collectstatic.
set -euo pipefail

source_dir="$LAB_MNG_DIR/data/static/frontend"
target_dir="$LAB_STATIC_ROOT/frontend"

if [[ ! -f "$source_dir/index.html" || ! -d "$source_dir/assets" ]]; then
    echo "React build is missing from $source_dir" >&2
    exit 1
fi
if [[ "$(realpath "$source_dir")" == "$(realpath -m "$target_dir")" ]]; then
    echo "React source and collected destination must be separate" >&2
    exit 1
fi

echo "Refreshing React static assets in $target_dir"
rm -rf -- "$target_dir"
python3 "$LAB_MNG_DIR/manage.py" collectstatic --noinput

index="$target_dir/index.html"
if [[ ! -f "$index" ]]; then
    echo "React index was not collected: $index" >&2
    exit 1
fi
for extension in css js; do
    asset="$(grep -oE "assets/index-[^\" ]+\.${extension}" "$index" | head -n 1 || true)"
    if [[ -z "$asset" || ! -f "$target_dir/$asset" ]]; then
        echo "React ${extension} asset referenced by index is missing: $asset" >&2
        exit 1
    fi
    echo "React asset: $asset"
done
