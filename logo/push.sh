#!/bin/bash
# One-shot push of the logo card to the Tidbyt.
#
# This is NOT the thing that keeps the card current -- push-logo.yml is, and
# it runs every fifteen minutes. The artwork never changes, but the render
# does: the costume comes from the date and awake-vs-asleep from the shop's
# opening hours, both decided at render time. Use this for an out-of-band push
# after regenerating kaleidoscope.star, or if the card drops out of rotation.
#
# The device id is read from disk rather than hardcoded: this repo is public,
# and every workflow here already treats TIDBYT_DEVICE_ID as a secret, so a
# literal in a tracked file would contradict the repo's own posture and tie a
# named shop's display to it.
set -euo pipefail
cd "$(dirname "$0")/.."

CONF="${XDG_CONFIG_HOME:-$HOME/.config}/tidbyt"
TOKEN_FILE="$CONF/token"
DEVICE_FILE="$CONF/device_id"

for f in "$TOKEN_FILE" "$DEVICE_FILE"; do
  [ -r "$f" ] || { echo "push.sh: missing or unreadable: $f" >&2; exit 1; }
done
command -v pixlet >/dev/null || { echo "push.sh: pixlet is not on PATH" >&2; exit 1; }

# Read into variables FIRST. A failing $(cat ...) inlined as a command
# argument does not trip set -e -- it substitutes an empty string and sails
# on, so a missing token would surface as an opaque pixlet auth error rather
# than as the real problem.
TOKEN="$(cat "$TOKEN_FILE")"
DEVICE="$(cat "$DEVICE_FILE")"
[ -n "$TOKEN" ] && [ -n "$DEVICE" ] || { echo "push.sh: token or device id is empty" >&2; exit 1; }

OUT="$(mktemp -t kscope-logo-XXXXXX.webp)"
trap 'rm -f "$OUT"' EXIT
pixlet render logo/kaleidoscope.star -o "$OUT"
pixlet push --api-token "$TOKEN" --installation-id logo "$DEVICE" "$OUT"
echo "pushed $(wc -c < "$OUT") bytes"
