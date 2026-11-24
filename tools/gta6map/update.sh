#!/usr/bin/env bash
# Refresh the open data sources and rebuild docs/data/markers.json. Safe to run repeatedly.
#   Open GTA 6 Map (CC BY 4.0)  -> data/openmap_locations.json, data/openmap_removed.json
#   gtadb.org (CC BY 4.0)       -> data/gtadb_landmarks.json (+ new landmark photos)
#   community mirror of the IGN map (dablon/gta-vi-strategic-map) -> new rows in data/ign_snapshot.json
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; DATA="$HERE/data"; TMP="$(mktemp -d)"
fetch() {   # url, destination: replace the file only if the download is valid JSON of a sane size
  if curl -fsSL --retry 3 -m 180 "$1" -o "$TMP/f.json" && python3 - "$TMP/f.json" "$2" <<'PY'
import json, os, sys
new = json.load(open(sys.argv[1], encoding='utf8'))
old = os.path.getsize(sys.argv[2]) if os.path.exists(sys.argv[2]) else 0
assert os.path.getsize(sys.argv[1]) > old * 0.6, 'download is much smaller than the current file'
PY
  then mv "$TMP/f.json" "$2"; echo "updated $(basename "$2")"; else echo "kept old $(basename "$2") (download failed or looked wrong)"; fi
}
RAW=https://raw.githubusercontent.com
fetch "$RAW/fbritoferreira/gta6/HEAD/public/data/locations.json" "$DATA/openmap_locations.json"
fetch "$RAW/fbritoferreira/gta6/HEAD/public/data/removed.json"   "$DATA/openmap_removed.json"
fetch "$RAW/rolux/gtadb.org/HEAD/map/data/6/landmarks.json"      "$DATA/gtadb_landmarks.json"
if curl -fsSL --retry 2 -m 120 "$RAW/dablon/gta-vi-strategic-map/HEAD/public/discovered.json" -o "$TMP/mirror.json"; then
  python3 "$HERE/snapshot_sources.py" --mirror "$TMP/mirror.json" || echo "mirror sync skipped"
fi
python3 "$HERE/fetch_photos.py" || echo "photo sync skipped"
python3 "$HERE/build_data.py"
rm -rf "$TMP"
