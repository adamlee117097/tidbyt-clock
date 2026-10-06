# tidbyt-apps

Custom apps for a Tidbyt (64×32 LED matrix) in a warm-dark espresso
palette, pushed standalone by GitHub Actions — no home machine involved.

| App | Preview | What it shows |
|---|---|---|
| **logo** | ![Logo preview](logo/preview.gif) | Kaleidoscope Coffee: two cartoon flamingos over a pair of steaming espresso cups. While the shop is open they do something new every 15 minutes -- lean in until their necks make a heart, take turns sipping, balance on one leg, dance, preen -- with a wing stretch for the first and last half hour. After closing they sleep on one leg under the moon. |
| **news** | — | Greenpoint headlines (Greenpointers + Brooklyn Paper RSS), vertical scroll, breaking-news state |
| **rocketfuel** | ![Rocket Fuel preview](rocketfuel/preview.gif) | Promo card for Sweetleaf's Rocket Fuel (maple oat-milk cold brew): a pixel-art take on the can — the rider on a gold rocket, flame flickering, splatter stars streaming, the menu price in the corner. Static; pushed daily as a keepalive. |
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

The logo card looks like the easy case and isn't. Its artwork never changes,
but what it *renders* does: it decides whether the birds are awake or asleep
from the shop's opening hours. A pushed WebP is frozen until it is replaced,
so the push cadence is what the card's accuracy depends on — birds still
asleep at 10am would be worse than not having the feature. So `push-logo.yml`
uses the same self-looping trick as the news app, pushing every 15 minutes,
which bounds how stale the card can be at a boundary. Its animation is a 3.2-second seamless loop precisely because the
device only buffers a short chunk of a pushed WebP and replays it — anything
longer would visibly stall (see the clock note below).

The clock is harder: it pre-renders future frames at 1 fps so the display
ticks between pushes, but **stock Tidbyt hardware only buffers a small
chunk of a long animation and loops it**, so the minute can stick. Treat
`clock` as experimental on stock devices; it works properly on Tronbyt,
where the server renders continuously. Pin any clock-style app so
rotation doesn't restart its animation.

## Deploying

```bash
./deploy.sh logo|news|rocketfuel [pixlet render args]
```

A plain `git push` does not reach the panel for up to 5.5 hours: the
self-looping workflows pin both the run in progress and the queued run to
the commit they were created at, and the stale loop overwrites any manual
push every 10–15 minutes until it ends. `deploy.sh` renders and pushes
straight to the device, cancels the stale runs, and dispatches a fresh one
on HEAD. It refuses to run with uncommitted or unpushed changes.

## Local development

```bash
pixlet serve weather/weather.star   # live preview at localhost:8080
pixlet render weather/weather.star --gif --magnify 8 -o preview.gif
```

Pixlet quirk: keep each app in its own directory — two `.star` files in
one folder confuse the loader.

### Opening hours

Outside shop hours the birds sleep: heads folded back over their bodies, eyes
shut, the cups and the counter they sat on cleared away, no steam because the
machines are off, and a pair of "z"s drifting up between them. A closed card with no motion at all would read as a crashed display
rather than a shut shop, so the z's are doing real work.

| | Open |
|---|---|
| Mon–Thu | 8am – 5pm |
| Fri–Sun | 8am – 6pm |

Hours live at the top of `logo/kaleidoscope.star` (`OPEN_HOUR`, `CLOSE_HOUR`). Note that a pixlet
time value has **no weekday attribute** — `now.format("Mon")` is how you get
one.

Force a scene for a look (`heart`, `sip`, `oneleg`, `dance`, `preen`,
`stretch`, `sleep`):

```bash
pixlet render logo/kaleidoscope.star scene=sip --gif --magnify 6 -o /tmp/x.gif
```

### Regenerating the logo card's frames

```bash
python3 logo/make_frames.py     # needs Pillow
```

Redesigned 2026-10-06 as cartoon birds (the earlier hand-drawn and
downscaled-logo versions are in git history before that date). Body, head
and wing are small ASCII grids; the **neck is a cubic Bezier** from the front
of the body to the head, drawn with a 2x2 brush, so a pose is just a head
position. Standing heads get an S-curve; anything reaching forward (the
heart, a sip) gets an arch, because a plain curve flattens into a stick.
The right bird is the left one mirrored. Each scene is 48 frames at 100ms;
all of them are baked into the `.star`, which picks one from the clock.

`logo/push.sh` pushes from a laptop, reading the API token from
`~/.config/tidbyt/token` and the device id from `~/.config/tidbyt/device_id`
(both chmod 600). Neither is ever written into a tracked file. Remove the app
from a device with:

```bash
# Disable push-logo.yml on the Actions tab first -- a run mid-loop will just
# push it straight back, which looks like the delete failing.
pixlet delete --api-token "$(cat ~/.config/tidbyt/token)" \
  "$(cat ~/.config/tidbyt/device_id)" logo
```

### Things the panel taught us

- The device this was designed against is mounted **portrait**, which is
  worth knowing before judging any layout.
- **1px lines do not read.** The matrix puts a black gutter between every
  diode, so a single-pixel leg becomes a column of separate dots and the bird
  looks like it is standing beside its legs. Legs are 2px. Judge pixel art by
  simulating those gutters, not by magnifying a render.
- Two shades of one hue barely separate at panel brightness — don't rely on
  it to carry a *shape*. It is fine for shading a shape you have already
  established: the birds' lower edges are a darker coral at about 2:1 against
  the body, which gives the mass some form without risking the silhouette.
  Anything load-bearing needs a real value gap.
- Black is invisible *against* black, but black *inside* a lit shape is the
  strongest mark available. That is how the eye is drawn: one unlit pixel in
  the head, the genre convention — a bright pupil there competed with the
  bill and read as a glint. A 1px unlit wing fold was tried on the
  hand-drawn body and read as three specks, not a line; the belly shadow does
  the wing's work instead.
- A true black bill tip is unreachable here: at the outer end of the bill it
  would border the background on three sides and vanish. The downward hook is
  carried by shape alone, in the bill's own pale colour.
- Sleeping birds show no bill and no eye: a roosting flamingo lays its head
  along its back with the bill tucked.
- Fidelity to the logo is not the goal; reading as a flamingo is. The
  downscaled logo kept every proportion and read as nothing. Draw the cues,
  not the artwork.
- A counter line that touches a leg reads as a shelf the bird is standing on.
  The cups' counter now stops well short of the legs.
- **Nothing may be black**, since the background is. A witch hat is purple.
  The one exception is unlit pixels *inside* a lit shape — the number strokes
  on the marathon bib work precisely because white surrounds them.
- Small shapes want one hue. Alternating colours inside a 3px-wide band
  dissolve it; save the colour play for something big enough to hold it.
- Check contrast against black. A gray below about 2:1 simply is not there on
  a lit floor.
- Check relative luminance against the *subject*, not just against black. The
  firmware applies CIE luminance correction, so sRGB-space luminance is the
  right model: coral ≈ 0.27, gold ≈ 0.56, white ≈ 0.91. Anything brighter than
  the birds competes with them; that is why the wordmark is gray and the
  steam is capped at 150.
- Legibility distance on a 3mm pitch: roughly 1 inch of cap height per 10
  feet. 5px text reaches ~6 feet; a 26px bird ~30 feet.
- Judge through an LED-gutter simulator (each pixel a square with a gap and a
  faint bloom), never a plain magnified render. pixlet also merges identical
  consecutive frames, so webp frame N is not generator frame N -- expand by
  frame duration before indexing.

Clock config params: `frames` (seconds of animation, default 150),
`offset` (seconds to lead real time by, to cancel push latency), `$tz`
(default America/New_York).
