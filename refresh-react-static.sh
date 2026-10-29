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
python3 - "$index" "$target_dir" <<'PY'
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class ReactIndex(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.import_map = []
        self.in_import_map = False
        self.stylesheets = 0
        self.module_scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            if attrs.get("type") == "importmap":
                self.in_import_map = True
            elif attrs.get("type") == "module" and attrs.get("src"):
                self.module_scripts += 1
                self.assets.append(attrs["src"])
        elif tag == "link" and attrs.get("href"):
            relations = attrs.get("rel", "").split()
            if "stylesheet" in relations:
                self.stylesheets += 1
                self.assets.append(attrs["href"])
            elif "modulepreload" in relations:
                self.assets.append(attrs["href"])

    def handle_data(self, data):
        if self.in_import_map:
            self.import_map.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_import_map = False


index = Path(sys.argv[1])
root = Path(sys.argv[2]).resolve()
parser = ReactIndex()
parser.feed(index.read_text(encoding="utf-8"))
if not parser.stylesheets or not parser.module_scripts:
    raise SystemExit("React index is missing a stylesheet or module script")
if parser.import_map:
    parser.assets.extend(json.loads("".join(parser.import_map)).get("imports", {}).values())

prefix = "/static/frontend/"
for url in dict.fromkeys(parser.assets):
    path = unquote(urlsplit(url).path)
    if not path.startswith(prefix):
        raise SystemExit(f"Unexpected React asset URL: {url}")
    asset = (root / path.removeprefix(prefix)).resolve()
    if not asset.is_relative_to(root) or not asset.is_file():
        raise SystemExit(f"React asset referenced by index is missing: {url}")
    print(f"React asset: {path}")
PY
