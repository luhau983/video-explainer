#!/usr/bin/env bash
# Tạo character sheet cho từng nhân vật. Dùng: ./scripts/gen_sheets.sh salmon bear
set -e
cd "$(dirname "$0")/.."
for name in "$@"; do
  prompt=$(sed "s/<NAME>/$name/g" prompts/make_sheet.md)
  codex exec -s workspace-write "$prompt"
done
