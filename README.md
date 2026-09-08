# tidbyt-apps

Custom apps for a Tidbyt (64×32 LED matrix) in a warm-dark espresso
palette, pushed standalone by GitHub Actions — no home machine involved.

| App | Preview | What it shows |
|---|---|---|
| **logo** | ![Logo preview](logo/preview.gif) | Kaleidoscope Coffee: two pixel-art flamingos leaning in over a pair of espresso cups on the counter, steam puffing off the crema. They blink, shift their weight into the lean, flick a tail, and the steam meets as a heart at the deepest lean. They sleep when the shop is shut. |
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

Hours live in `make_frames.py` and are baked into the app. Note that a pixlet
time value has **no weekday attribute** — `now.format("Mon")` is how you get
one.

Force either state for a look:

```bash
pixlet render logo/kaleidoscope.star state=asleep --gif --magnify 6 -o /tmp/x.gif
```

### The wordmark

Gray (185) in `CG-pixel-4x5-mono` rather than white in tom-thumb. White sat
at ~0.91 relative luminance against the birds' ~0.27 -- 3.4x brighter than
the thing the card is for. The 4px glyphs also stop K, D, O and C being
ambiguous at this size. Worth knowing: on a 3mm-pitch panel, 5px text is
legible to about 6 feet and a 24px bird to about 30, so from where anyone
stands in the shop the name is decoration and the mark is the message. A
no-wordmark layout with bigger birds was built once (commit 288420b) and is
parked until the birds themselves are settled.

### Regenerating the logo card's frames

```bash
python3 logo/make_frames.py     # needs Pillow + numpy
```

The birds are hand-authored pose grids (ASCII, one character per pixel) at
the top of the script: neutral, half lean, full lean, and asleep. The right
bird is the left one mirrored. Edit a grid or a constant and re-run; it
rewrites `logo/kaleidoscope.star` in place. Don't hand-edit the base64 blobs.

Why hand-authored: the first four versions downscaled the shop's actual logo
artwork, and however carefully (head split off and rotated at full
resolution, LANCZOS, thresholded, symmetry forced) it never read as a
flamingo -- the neck came out a thick straight column, the bill a sideways
bar, the body a blob with an angular wing. The sprites that do read at this
size all do the same few things: a compact round head, a pale bill hooking
*down* in front of it, a thin vertical neck rising from the *front* of a
horizontal body, a pointed tail, long bare legs. So that is what is drawn.

Things the generator refuses to do quietly: it asserts every grid is the
right shape and uses only known symbols, that each awake pose has exactly one
eye and the sleeping one none, that the puff climb and the z drift divide the
frame count, that the cups, counter and heart are mirror-symmetric, that the
blink and the tail flick actually change a frame, and that the frame after
the last renders byte-identical to the first. Steam has its own guard: no
puff or heart pixel may land on, or even diagonally touch, a bird pixel in
any frame -- LED bloom closes that gap and the steam reads as a growth on
the bird.

### The motion

Four head poses held pose-to-pose (never tweened 1px at a time -- at this
size that reads as the sprite melting). On top of the lean:

- **Steam** is 2x2 puffs, not a 1px wisp -- the wisp was a 1px column, the
  exact thing the gutters turn into a dotted line. Born at the rim, one row
  per 8 frames, fading as they climb, two in flight per cup with the right cup
  half a hold behind the left. Capped at 150 gray so no step out-shines coral.
- **Weight shift**: on the 8-frame deepest lean the body drops one row while
  the feet stay planted.
- **Tail flick**: two frames after the lean lands the tail tip lifts one row
  for three frames. A 2px block, so it survives the gutters.
- **Blink**: the eye notch fills with coral for two frames, each bird on its
  own beat. It removes pixels rather than adding a glint.
- **Steam heart**: during the deepest lean the two cups' steam meets over the
  counter as a 7x5 heart, in steam gray. `HEART = False` in the generator
  drops it.

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
