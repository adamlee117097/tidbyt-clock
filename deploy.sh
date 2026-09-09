#!/bin/bash
# Put the current commit on the device NOW, for one app.
#
#   ./deploy.sh logo|news|rocketfuel [extra pixlet render args]
#
# Why this exists: the self-looping workflows (news, logo) run for ~5.5h and
# BOTH the run in progress AND the queued scheduled run are pinned to the
# commit they were created at. A plain `git push` therefore reaches the panel
# up to 5.5 hours later, and the stale loop overwrites any manual push every
# 10-15 minutes until then. This script does the three things that fix that:
#   1. renders locally and pushes straight to the device (instant),
#   2. cancels every in-progress / queued run of the app's workflow,
#   3. dispatches a fresh run, which checks out HEAD.
# It refuses to run with uncommitted or unpushed changes, because the
# dispatched run would not contain them.
set -euo pipefail
cd "$(dirname "$0")"

APP="${1:-}"; shift || true
case "$APP" in
  logo)       STAR=logo/kaleidoscope.star;    WF=push-logo.yml ;;
  news)       STAR=news/greenpoint_news.star; WF=push-news.yml ;;
  rocketfuel) STAR=rocketfuel/rocketfuel.star; WF=push-rocketfuel.yml ;;
  *) echo "usage: $0 logo|news|rocketfuel [render args]" >&2; exit 2 ;;
esac

if [ -n "$(git status --porcelain)" ]; then
  echo "deploy: uncommitted changes -- commit first, the workflow deploys HEAD" >&2; exit 1
fi
if [ "$(git rev-parse HEAD)" != "$(git rev-parse '@{u}')" ]; then
  echo "deploy: HEAD is not pushed -- git push first" >&2; exit 1
fi

CONF="${XDG_CONFIG_HOME:-$HOME/.config}/tidbyt"
TOKEN="$(cat "$CONF/token")"; DEVICE="$(cat "$CONF/device_id")"
[ -n "$TOKEN" ] && [ -n "$DEVICE" ] || { echo "deploy: missing token or device id" >&2; exit 1; }

OUT="$(mktemp -t tidbyt-XXXXXX.webp)"; trap 'rm -f "$OUT"' EXIT
pixlet render "$STAR" "$@" -o "$OUT"
pixlet push --api-token "$TOKEN" --installation-id "$APP" "$DEVICE" "$OUT"
echo "device: pushed $(wc -c < "$OUT") bytes to installation '$APP'"

for id in $(gh run list --workflow "$WF" --json databaseId,status \
             -q '.[] | select(.status=="in_progress" or .status=="queued" or .status=="pending" or .status=="waiting") | .databaseId'); do
  gh run cancel "$id" >/dev/null && echo "actions: cancelled stale run $id"
done
sleep 8
gh workflow run "$WF" >/dev/null && echo "actions: dispatched $WF on $(git rev-parse --short HEAD)"
sleep 30
gh run list --workflow "$WF" --limit 1 --json status,headSha \
  -q '.[] | "actions: newest run \(.status) on \(.headSha[0:7])"'
