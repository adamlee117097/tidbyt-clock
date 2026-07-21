# tidbyt-clock

Custom clock face for a Tidbyt (64×32 LED matrix): gold digits, blinking
colon, amber date line, seconds bar. Runs standalone — no home machine
involved.

## How it works

A Tidbyt shows whatever WebP it was last pushed, so a clock has to keep
itself ticking between pushes. Each render covers the **next 30 minutes at
1 frame/second** (`frames=1800`); a GitHub Actions cron re-renders and
pushes every 10 minutes, so scheduling jitter (or a skipped run or two)
never shows a wrong time. The `clock` installation should be **pinned** in
the Tidbyt mobile app so the animation plays continuously — in normal app
rotation each turn would restart the animation at frame 0.

If pushes stop for more than ~30 minutes, the display loops back to the
start of its last animation (time appears to rewind) until the next push.

## Setup

Repo secrets (Settings → Secrets and variables → Actions):

- `TIDBYT_DEVICE_ID` — Tidbyt app → device → settings → Get API key
- `TIDBYT_API_TOKEN` — same screen

## Local development

```bash
pixlet serve clock.star          # live preview at localhost:8080
pixlet render clock.star frames=6 --gif --magnify 8 -o preview.gif
```

Config params: `frames` (animation length in seconds, default 150 for fast
local renders), `$tz` (default America/New_York).
