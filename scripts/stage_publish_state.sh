#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

candidates=(
  data/state.json
  data/approved_market_feed.json
  output/telegram_state.json
  output/approval_queue.json
  output/content_*.json
  output/draft_*.json
  output/media/*.publish.json
)
paths=()
for path in "${candidates[@]}"; do
  if [[ -e "$path" ]]; then
    paths+=("$path")
  fi
done

if (("${#paths[@]}" == 0)); then
  echo "No publish-state files found to stage."
  exit 0
fi

git add -A -- "${paths[@]}"
printf 'Staged %s publish-state file(s).\n' "${#paths[@]}"
