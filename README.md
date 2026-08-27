# tidbyt-apps

Custom apps for a Tidbyt (64×32 LED matrix) in a warm-dark espresso
palette, pushed standalone by GitHub Actions — no home machine involved.

| App | Preview | What it shows |
|---|---|---|
| **logo** | ![Logo preview](logo/preview.gif) | The Kaleidoscope Coffee mark: two flamingos leaning in over a pair of espresso cups, steam off the crema. They dress for the season. |
| **news** | — | Greenpoint headlines (Greenpointers + Brooklyn Paper RSS), vertical scroll, breaking-news state |
| **weather** | ![Weather preview](weather/preview.gif) | Current temp, animated pixel-art conditions, daily high/low, precip chance (NWS + Open-Meteo blend, no API keys) |
| **clock** | ![Clock preview](clock/preview.gif) | Gold digits, blinking colon, date, seconds bar *(experimental — see note)* |

## Run them on your own Tidbyt

The official Tidbyt community catalog stopped accepting new apps after the
Modal acquisition, so this ships as a self-serve repo instead:

1. **Fork this repo** (keep it public — the free private-repo Actions quota
   won't cover the run frequency).
2. Add repo secrets (Settings → Secrets and variables → Actions):
   - `TIDBYT_DEVICE_ID` — Tidbyt app → device → settings → Get API key
   - `TIDBYT_API_TOKEN` — same screen
3. Enable the workflow(s) you want on the Actions tab (forks start with
   workflows disabled) and trigger each once via *Run workflow*.
4. For the weather app, edit the NWS gridpoint URLs at the top of
   `weather/weather.star` for your location: fetch
   `https://api.weather.gov/points/{lat},{lon}` and copy the `forecast`
   and `forecastHourly` URLs it returns. (US only — NWS.)

If you run a [Tronbyt](https://github.com/tronbyt) (self-hosted firmware)
instead, you don't need the push machinery — drop the `.star` files into
your server's apps folder.

## How the push model works

A Tidbyt shows whatever WebP it was last pushed. The weather app is a
short looping animation re-pushed every 10 minutes — a natural fit.

The news app is the awkward case: GitHub throttles free-tier cron to roughly
every 1–3 hours, so `push-news.yml` keeps a single run alive for ~5.5 hours
pushing every 10 minutes, with the next scheduled run queued behind it. That
is why it carries a `concurrency` block and a 355-minute timeout.

The logo card sits in between. Its art never changes, but it picks a costume
from the date when it renders — so the push, not the app, is what moves the
birds out of Santa hats and into leis. `push-logo.yml` runs once a day for
exactly that reason. Its animation is a 3.2-second seamless loop precisely
because the device only buffers a short chunk of a pushed WebP and replays
it — anything longer would visibly stall (see the clock note below).

The clock is harder: it pre-renders future frames at 1 fps so the display
ticks between pushes, but **stock Tidbyt hardware only buffers a small
chunk of a long animation and loops it**, so the minute can stick. Treat
`clock` as experimental on stock devices; it works properly on Tronbyt,
where the server renders continuously. Pin any clock-style app so
rotation doesn't restart its animation.

## Local development

```bash
pixlet serve weather/weather.star   # live preview at localhost:8080
pixlet render weather/weather.star --gif --magnify 8 -o preview.gif
```

Pixlet quirk: keep each app in its own directory — two `.star` files in
one folder confuse the loader.

### The logo card's seasonal wardrobe

![costumes](logo/costumes.png)

| When | Costume |
|---|---|
| 1 Dec – 6 Jan | Santa hats |
| 1 Jun – 31 Aug | Flower leis, plus a bloom at the ear |
| the rest of the year | undressed |

All three wardrobes ship inside `kaleidoscope.star`; the app picks one from
`time.now()` at render time. Every day of the year maps to exactly one
costume. Preview one out of season without waiting six months:

```bash
pixlet render logo/kaleidoscope.star season=santa --gif --magnify 6 -o /tmp/x.gif
```

`season` accepts `plain`, `santa`, or `lei`.

### Regenerating the logo card's frames

```bash
python3 logo/make_frames.py     # needs Pillow + numpy
```

It recomposes the flamingos from the shop's logo artwork at full resolution —
head and neck are split off as their own layer along a slanted cut and
rotated about the neck base — and only then downscales to 26px, so every pose
keeps the logo's true proportions. The bottom band (legs, perch line, cups,
feet) is hand-authored pixel geometry instead, because at 26px the downscale
smears it. Costumes anchor to the head's own downscaled bitmap so they ride
the nod rather than floating where the head used to be. Edit the constants at
the top and re-run; it rewrites `logo/kaleidoscope.star` in place. Don't
hand-edit the base64 blobs.

This is the one script here that is not fork-friendly: it reads a source logo
by absolute path from outside the repo. You don't need it to *run* the app —
`kaleidoscope.star` is committed and self-contained — only to change the art.

`logo/push.sh` pushes from a laptop, reading the API token from
`~/.config/tidbyt/token` and the device id from `~/.config/tidbyt/device_id`.
Neither is ever written into a tracked file.

### Things the panel taught us

- **1px lines do not read.** The matrix puts a black gutter between every
  diode, so a single-pixel leg becomes a column of separate dots and the bird
  looks like it is standing beside its legs. Legs are 2px. Judge pixel art by
  simulating those gutters, not by magnifying a render.
- Two shades of one hue barely separate at panel brightness — don't rely on
  it to carry a shape.
- Check contrast against black. A gray below about 2:1 simply is not there on
  a lit floor.

Clock config params: `frames` (seconds of animation, default 150),
`offset` (seconds to lead real time by, to cancel push latency), `$tz`
(default America/New_York).
