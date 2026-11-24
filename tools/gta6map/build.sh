#!/usr/bin/env bash
# Rebuild docs/data for the map. Paths point at local checkouts of the source repositories:
#   GTADB = github.com/rolux/gtadb.org (sparse: map/data/6 map/photos/6 maps/tiles/6/day)
#   IGN   = folder with markers.js + taxonomy.js exported from the IGN/MapGenie Leonida map
#   PPX   = github.com/theihtishaam/GTA-6-Interactive-Map-and-Loot-Tracker
#   TR    = folder with out_*.json (Russian location hints)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; DOCS="$HERE/../../docs"
: "${GTADB:?}" "${IGN:?}" "${PPX:?}" "${TR:?}"
B=(--gtadb "$GTADB" --ign "$IGN" --ppx "$PPX" --tr "$TR" --docs "$DOCS")
python3 "$HERE/build_data.py" "${B[@]}" > /dev/null
python3 "$HERE/make_extras.py" --markers "$DOCS/data/markers.json" --ign "$IGN" --out "$HERE/extras.json" > "$HERE/extras_report.txt"
python3 "$HERE/build_data.py" "${B[@]}" --extras "$HERE/extras.json" --unplaced "$HERE/extras_skipped.json"
