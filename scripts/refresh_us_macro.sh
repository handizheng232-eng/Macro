#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WIND_SKILL_DIR="${WIND_MCP_SKILL_DIR:-C:/HermesData/skills/wind-mcp-skill}"
END_DATE="${1:-$(date -u +%F)}"
TMP_DIR="$ROOT_DIR/.tmp/wind-us-macro-refresh-$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

call_wind() {
  local category="$1"
  local codes="$2"
  (
    cd "$WIND_SKILL_DIR"
    node scripts/cli.mjs call economic_data query_economic_indicator_data \
      "{\"question\":\"$codes\",\"beginDate\":\"2021-01-01\",\"endDate\":\"$END_DATE\"}"
  ) > "$TMP_DIR/$category.json"
  if [[ ! -s "$TMP_DIR/$category.json" ]]; then
    printf 'Wind returned an empty response for %s\n' "$category" >&2
    exit 1
  fi
}

call_wind growth 'G0000002,G0002323,G1120948,G1109266,G0003883'
call_wind employment 'G1137399,G0000067,G0002446,G0002451,G0002449,G0002463,G0002461,G0002457'
call_wind inflation 'G0000027,G0000029,G1100004,G1100005,P9918147,Z5204395'
call_wind policy 'G1100020,G1100075,G0003351,G1137993'

python "$ROOT_DIR/scripts/refresh_us_macro.py" \
  --input-dir "$TMP_DIR" \
  --wind-skill-dir "$WIND_SKILL_DIR" \
  --end-date "$END_DATE"
