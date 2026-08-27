#!/usr/bin/env python3
"""Generate the Kaleidoscope Coffee logo animation and write kaleidoscope.star.

The mark is two mirrored flamingos flanking a pair of espresso cups. Rather
than hand-plotting 26px sprites, the birds are composed at the logo's native
resolution (head/neck split off as its own layer, rotated about the neck
base) and only then downscaled + thresholded -- so every pose keeps the real
logo proportions instead of drifting into hand-drawn approximations.

The bottom band (legs, perch line, cups, feet) IS hand-authored: at 26px the
downscale turns the thin legs and the two cups into an unreadable smear, so
those rows are cleared and redrawn as explicit 1px geometry.

Tune the constants below and re-run:  python3 logo/make_frames.py
"""
import base64
import io
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
LOGO = Path("/home/adam/Documents/Kaleidoscope/logo.png")
OUT_STAR = HERE / "kaleidoscope.star"

# ---------------------------------------------------------------- palette
CORAL = (242, 90, 60)      # brand #DF513B pushed up ~12% -- LEDs mute it
DARK = (169, 58, 40)       # the perch line only, so the gold cups stay the
                           # brightest thing down there instead of fusing
                           # with it into one horizontal smear
GOLD = (236, 190, 94)      # the cups; same crema-gold as the shop dashboard
# Steam, brightest at the cup rim and fading out as it climbs. Never white:
# at panel brightness white steam out-shines the birds and the card stops
# being a logo.
# Measured against black: the old ramp's last two steps sat at 2.03:1 and
# 1.55:1, so on a lit shop floor the wisp truncated to its bottom 3-4 pixels
# and the sway read as flicker on a stub. Shorter wisp, every step >=3.4:1.
STEAM = [(190, 190, 190), (160, 160, 160), (128, 128, 128), (98, 98, 98)]

# ---------------------------------------------------------------- geometry
# 25 art rows + 1 blank + 6 wordmark = the full 32 rows. The blank row is not
# optional: LED bloom at across-the-room distance closes a 0px gap and the
# feet visually fuse with the text. TOP_MARGIN spends the row that was
# otherwise structurally dead (art ended at FOOT_ROW, leaving a permanently
# black row above the blank one) on giving the heads a pixel of air instead
# of letting them butt against the panel edge.
BIRD_H = 26                # proportion of the downscale (bottom rows redrawn)
CANVAS_W, CANVAS_H = 64, 25
TOP_MARGIN = 1             # art occupies canvas rows 1..24
PANEL_W, PANEL_H = 64, 32  # the device itself
GAP_ROWS = 1               # blank row between art and wordmark
TEXT_ROWS = 6              # tom-thumb inks 5 rows, the widget is 6 tall
EXPECTED_LOGO_SIZE = (1024, 1024)  # the export MARK_BOX was measured against
MARK_BOX = (304, 237, 719, 554)    # flamingo mark inside logo.png
MARK_INK_RANGE = (36000, 44000)    # opaque px the crop must catch (~40031)
# Splitting head+neck off the body needs a SLANTED cut, not a vertical one:
# the head sits left of the neck base, so any straight x cut either leaves a
# sliver of skull welded to the static body or swallows the wing. The cut
# line x > CUT_A + CUT_B*y clears the wing at every row while keeping the
# whole head. The two layers deliberately OVERLAP between BODY_CUT_Y and
# HEAD_CUT_Y so a rotated neck still meets the shoulder instead of tearing.
CUT_A, CUT_B = 60.0, 0.55
CUT_X_MAX = 210            # keeps the left bird's mask off the right bird
BODY_CUT_Y = 106           # body keeps everything below this (the stub)
HEAD_CUT_Y = 125           # head layer runs this far down (past the pivot)
PIVOT_Y = 118              # neck base -- heads rotate about this point
PIVOT_X = 150
LEG_TRIM = 258             # crop the long bare-leg run before downscaling
COMPACT_H = 275            # bird-scale knob, NOT a measured height: it is
                           # neither the 317px crop nor the 258px trim. Chosen
                           # so the torso fills rows 0..17 at BIRD_W == 39.
THRESHOLD = 110

# --- hand-authored bottom band, in bird-local columns (39 wide, mirror @19)
BAND_TOP = 18              # first row the downscale is discarded from, and
                           # the top of every hand-authored element below.
                           # It was previously written out in four separate
                           # places that had to agree by hand.
LEG_COL = 9
LEG_W = 2                  # NOT 1. A 1px leg is anatomically right and
                           # unreadable: the panel puts a black gutter between
                           # every diode, so a single-pixel line becomes a
                           # column of separate dots and the bird looks like it
                           # is standing next to its legs rather than on them.
                           # Confirmed on the device, not just in a render.
FOOT_W = 3
FOOT_ROW = 23
LEG_ROWS = range(BAND_TOP, FOOT_ROW)
BAR_ROW = 20
# Perch line: only the stretch between the leg and the cup handle. The logo
# runs it outboard of the legs too, but at this size that turns leg-plus-line
# into a free-floating "+" that reads as a foreign object rather than a bird.
BAR_COLS = range(LEG_COL + LEG_W, 13)
CUP = {                            # left cup; the right one is mirrored
    BAND_TOP + 0: [14, 15, 16, 17],   # rim -- widest row, that is what reads
    BAND_TOP + 1: [14, 15, 16, 17],   # body
    BAND_TOP + 2: [13, 14, 15, 16, 17],  # body + handle, meets the perch line
    BAND_TOP + 3: [15, 16],           # tapered base
}
STEAM_COL = 16                     # wisp column for the left cup
STEAM_BASE_ROW = BAND_TOP - 1      # one row above the cup rim

# ---------------------------------------------------------------- motion
# Positive angle = heads lean INWARD, toward each other over the cups. The
# neck cannot actually reach the cups -- it is near-vertical, so rotating it
# about the shoulder slides the head sideways, not down, and no plausible
# angle puts the beak on a cup. Leaning in is the beat that IS available at
# this size, and past ~20 degrees the two heads collide into one blob.
# Retracting the neck to force a deeper dip was tried and rejected: it eats
# the neck, and the neck is the entire reason the silhouette reads flamingo.
NOD = [0, 7, 14, 20]
# frame -> NOD index. 48 frames @ 66ms = 3.17s; frame 47 flows into frame 0.
# Pose-to-pose with holds, never tweened 1px at a time -- smooth interpolation
# at 26px reads as the sprite melting, not as movement.
BEATS = ([0] * 13 + [1] * 3 + [2] * 3 + [3] * 8 +
         [2] * 3 + [1] * 3 + [0] * 15)
STEAM_LEN = len(STEAM)             # wisp height in rows

# ---------------------------------------------------------------- costumes
# Seasonal dress. Everything is anchored to the HEAD's own downscaled bitmap
# rather than to fixed coordinates, so a costume rides the nod instead of
# floating where the head used to be. Colours are deliberately not coral: at
# this size a costume only reads if it contrasts with the bird wearing it.
SANTA_RED = (198, 40, 34)
SNOW = (238, 236, 232)
LEI_PETALS = [(255, 95, 162), (255, 211, 77)]   # hibiscus pink, frangipani
PLAIN, SANTA, LEI = "plain", "santa", "lei"
SEASONS = (PLAIN, SANTA, LEI)
STEAM_WAVE = [0, 0, 1, 1, 0, 0, -1, -1]   # length 8 divides 48 -> seamless
RIGHT_STEAM_PHASE = 4              # desync the two cups; mirrored steam
                                   # looks mechanical rather than alive
DELAY_MS = 66
TIMEZONE = "America/New_York"   # the shop's clock decides the season


def _layers():
    # MARK_BOX is a crop of THIS logo file at its current 1024x1024 export.
    # A re-exported logo at another size would still crop, still downscale,
    # and still emit 48 valid frames -- of the wrong part of the image. Fail
    # loudly here instead of shipping quietly-wrong art to the shop floor.
    if not LOGO.exists():
        raise SystemExit("source logo not found: %s" % LOGO)
    src = Image.open(LOGO).convert("RGBA")
    if src.size != EXPECTED_LOGO_SIZE:
        raise SystemExit(
            "logo is %dx%d, expected %dx%d -- MARK_BOX and the layer-cut "
            "constants are calibrated to that export. Re-derive them against "
            "the new file before regenerating." % (src.size + EXPECTED_LOGO_SIZE))
    mark = src.crop(MARK_BOX)
    ink = int((np.array(mark.split()[3]) > 128).sum())
    if not MARK_INK_RANGE[0] <= ink <= MARK_INK_RANGE[1]:
        raise SystemExit(
            "MARK_BOX caught %d opaque pixels, expected %d-%d. The logo is the "
            "right size but the mark is not where the crop says it is -- a "
            "re-export that shifted the artwork passes the dimension check and "
            "would otherwise render a quietly-wrong bird." % ((ink,) + MARK_INK_RANGE))
    w, h = mark.size
    a = np.array(mark.split()[3]) > 128
    y, x = np.mgrid[0:h, 0:w]
    cut = CUT_A + CUT_B * y
    mx = w - 1 - x

    def side(col, ymax):
        return a & (y < ymax) & (col > cut) & (col < CUT_X_MAX)

    head_l = side(x, HEAD_CUT_Y)
    head_r = side(mx, HEAD_CUT_Y)
    body = a & ~(side(x, BODY_CUT_Y) | side(mx, BODY_CUT_Y))

    def gray(mask):
        im = Image.new("L", (w, h), 0)
        im.putdata((mask.astype(np.uint8) * 255).ravel().tolist())
        return im

    return gray(body), gray(head_l), gray(head_r), w


BODY, HEAD_L, HEAD_R, SRC_W = _layers()
BIRD_W = round(SRC_W * BIRD_H / COMPACT_H)          # 39
HAND_BAND_WIDTH = 39       # the width every hand-authored column assumes
OX = (CANVAS_W - BIRD_W) // 2                        # 12
MIRROR = BIRD_W - 1                                  # x -> MIRROR - x

# These couplings are what a well-meaning tune breaks silently rather than
# loudly, so state them where an edit trips over them.
assert BIRD_W % 2 == 1, (
    "BIRD_W must stay odd (%d) -- the hand band mirrors about a centre "
    "COLUMN, and an even width puts the axis between pixels" % BIRD_W)
assert BIRD_W == HAND_BAND_WIDTH, (
    "BIRD_W is %d but every hand-authored column (LEG_COL, BAR_COLS, CUP, "
    "STEAM_COL) and BAND_TOP are measured against a %d-wide sprite. Raising "
    "BIRD_H silently slides the legs and cups off the birds and moves the "
    "band wipe up into the torso -- re-tune those columns, then update this."
    % (BIRD_W, HAND_BAND_WIDTH))
assert CANVAS_H + GAP_ROWS + TEXT_ROWS == PANEL_H, (
    "art %d + gap %d + wordmark %d != the panel's %d rows"
    % (CANVAS_H, GAP_ROWS, TEXT_ROWS, PANEL_H))
assert CANVAS_W == PANEL_W, "the frames must be the full panel width"
assert len(BEATS) % len(STEAM_WAVE) == 0, (
    "the steam wave (%d) must divide the frame count (%d) or the wisp jumps "
    "sideways at the loop seam" % (len(STEAM_WAVE), len(BEATS)))
assert max(BEATS) < len(NOD), "BEATS indexes past the end of NOD"
assert FOOT_ROW + TOP_MARGIN < CANVAS_H, "the feet fall off the canvas"
assert max(CUP) + TOP_MARGIN < CANVAS_H, "the cups fall off the canvas"
assert min(CUP) == BAND_TOP, "the cup must start at the hand-authored band top"


def _downscale(gray):
    """Source-resolution layer -> the sprite grid, thresholded."""
    im = gray.crop((0, 0, SRC_W, LEG_TRIM))
    small = im.resize((BIRD_W, round(LEG_TRIM * BIRD_H / COMPACT_H)), Image.LANCZOS)
    grid = np.zeros((BIRD_H, BIRD_W), dtype=bool)
    s = np.array(small) > THRESHOLD
    grid[:s.shape[0], :] = s
    return grid


_HEAD_CACHE = {}


def head_bitmap(angle):
    """The left bird's head+neck alone, so costumes can anchor to it."""
    if angle not in _HEAD_CACHE:
        hl = HEAD_L.rotate(-angle, resample=Image.BICUBIC, center=(PIVOT_X, PIVOT_Y))
        _HEAD_CACHE[angle] = _downscale(hl)
    return _HEAD_CACHE[angle]


def santa_hat(head):
    """A red cone with a white brim and a pom lolling back off the skull.

    It replaces the top of the head rather than sitting above it -- which is
    where a hat goes anyway, and there is no room above: the skull already
    reaches the first row of the canvas.
    """
    rows = np.where(head.any(axis=1))[0]
    top = int(rows.min())
    cols = np.where(head[top])[0]
    c0, c1 = int(cols.min()), int(cols.max())
    out = [(c0 - 1, top - 1, SNOW)]                        # pom, lolling back
    out += [(c, top - 1, SANTA_RED) for c in (c0, c0 + 1)]  # tip
    out += [(c, top, SANTA_RED) for c in range(c0, c1 + 1)]
    out += [(c, top + 1, SNOW) for c in range(c0 - 1, c1 + 2)]  # brim
    return out


def lei(head):
    """A flower garland round the neck, plus one bloom at the ear.

    The neck is only three pixels wide, so a single row of three different
    colours just reads as noise -- it needs two rows to register as an object
    at all. The ear flower is what actually says "tropical" at a glance; the
    garland alone is ambiguous.
    """
    rows = np.where(head.any(axis=1))[0]
    top, base = int(rows.min()), int(rows.max())
    out = []
    for i, row in enumerate((base - 1, base)):
        cols = np.where(head[row])[0]
        for j, c in enumerate(range(int(cols.min()), int(cols.max()) + 1)):
            out.append((c, row, LEI_PETALS[(i + j) % 2]))
    ear = np.where(head[top + 2])[0]
    out += [(int(ear.min()), top + 2, LEI_PETALS[0]),
            (int(ear.min()) + 1, top + 2, LEI_PETALS[1])]
    return out


COSTUMES = {PLAIN: lambda head: [], SANTA: santa_hat, LEI: lei}


def bird_bitmap(angle):
    """Full-res compose at this head angle, then downscale to the sprite grid."""
    hl = HEAD_L.rotate(-angle, resample=Image.BICUBIC, center=(PIVOT_X, PIVOT_Y))
    hr = HEAD_R.rotate(angle, resample=Image.BICUBIC,
                       center=(SRC_W - 1 - PIVOT_X, PIVOT_Y))
    merged = np.maximum(np.maximum(np.array(BODY), np.array(hl)), np.array(hr))
    grid = _downscale(Image.fromarray(merged))
    grid[BAND_TOP:, :] = False  # the downscale's leg/cup mush -- redrawn below

    # Mirror the left half onto the right rather than trusting the downscale
    # to come out symmetric. It does not: LANCZOS lands either side of
    # THRESHOLD by a hair and every frame carried a stray pixel on one bird
    # that its twin lacked. The mark is a mirrored pair, so make that true by
    # construction. The axis column is never lit (asserted at import).
    half = BIRD_W // 2
    grid[:, BIRD_W - half:] = np.fliplr(grid[:, :half])
    return grid


def draw_frame(angle, tick, season=PLAIN):
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), (0, 0, 0))
    px = img.load()

    def put(col, row, color):
        y = row + TOP_MARGIN
        if 0 <= y < CANVAS_H and 0 <= col < BIRD_W:
            px[OX + col, y] = color

    for y, row in enumerate(bird_bitmap(angle)):
        for x, on in enumerate(row):
            if on:
                put(x, y, CORAL)

    # Perch line first, legs over it: drawn the other way round its dark
    # pixel lands on top of the leg at any crossing and severs it.
    for col in BAR_COLS:                                # perch line
        put(col, BAR_ROW, DARK)
        put(MIRROR - col, BAR_ROW, DARK)

    for i in range(LEG_W):                              # legs
        for row in LEG_ROWS:
            put(LEG_COL + i, row, CORAL)
            put(MIRROR - LEG_COL - i, row, CORAL)
    for i in range(FOOT_W):                             # feet
        put(LEG_COL + i, FOOT_ROW, CORAL)
        put(MIRROR - LEG_COL - i, FOOT_ROW, CORAL)

    for row, cols in CUP.items():                       # the two espresso cups
        for col in cols:
            put(col, row, GOLD)
            put(MIRROR - col, row, GOLD)

    for col, row, color in COSTUMES[season](head_bitmap(angle)):
        put(col, row, color)                    # left bird
        put(MIRROR - col, row, color)           # and its mirror

    n = len(STEAM_WAVE)
    for k in range(STEAM_LEN):                          # steam off the crema
        wave = STEAM_WAVE[(k + tick) % n]
        put(STEAM_COL + wave, STEAM_BASE_ROW - k, STEAM[k])
        wave_r = STEAM_WAVE[(k + tick + RIGHT_STEAM_PHASE) % n]
        put(MIRROR - (STEAM_COL + wave_r), STEAM_BASE_ROW - k, STEAM[k])
    return img


def encode(img):
    buf = io.BytesIO()
    img.convert("P", palette=Image.ADAPTIVE, colors=16).save(
        buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


TEMPLATE = '''"""Kaleidoscope Coffee -- the shop's flamingo mark, animated.

Two mirrored flamingos lean in toward each other over a pair of espresso cups
while steam curls off the crema. A short seamless loop by design: a Tidbyt
only buffers a few seconds of a pushed animation and replays that chunk, so
the whole cycle fits inside the buffer and frame {last} flows back into 0.

The birds dress for the season -- Santa hats through Christmas, flower leis
through the summer. The choice is made HERE, at render time, so a plain
re-push always puts the right costume up without touching any code.

Frames are generated by make_frames.py -- edit the constants there and re-run,
don't hand-edit the blobs below.
"""

load("render.star", "render")
load("encoding/base64.star", "base64")
load("time.star", "time")

WORDMARK = "KALEIDOSCOPE"
CORAL = "{coral}"
DELAY_MS = {delay}
TZ = "{tz}"

FRAMES_PLAIN = [
{frames_plain}
]

FRAMES_SANTA = [
{frames_santa}
]

FRAMES_LEI = [
{frames_lei}
]

WARDROBE = {{"plain": FRAMES_PLAIN, "santa": FRAMES_SANTA, "lei": FRAMES_LEI}}

def dress_for(now):
    """Santa from December through Twelfth Night, leis all summer."""
    if now.month == 12 or (now.month == 1 and now.day <= 6):
        return FRAMES_SANTA
    if now.month >= 6 and now.month <= 8:
        return FRAMES_LEI
    return FRAMES_PLAIN

def main(config):
    # `pixlet render ... season=santa` forces a costume, for previewing one
    # out of season without waiting six months to see if it looks right.
    forced = config.str("season", "")
    if forced in WARDROBE:
        frames = WARDROBE[forced]
    else:
        frames = dress_for(time.now().in_location(TZ))

    return render.Root(
        delay = DELAY_MS,
        child = render.Column(
            children = [
                render.Animation(
                    children = [
                        render.Image(src = base64.decode(f)) for f in frames
                    ],
                ),
                render.Box(width = {canvas_w}, height = {gap_rows}),
                # Box, not Row: a Row shrinks to fit its child, so main_align
                # has no slack to centre within and the wordmark sits flush
                # left. A fixed-width Box centres its child on both axes.
                # Height {text_rows}, not 5 -- tom-thumb inks 5 rows but the
                # widget is 6 tall, and a 5px box clips every glyph's bottom.
                render.Box(
                    width = {canvas_w},
                    height = {text_rows},
                    child = render.Text(
                        content = WORDMARK,
                        font = "tom-thumb",
                        color = CORAL,
                    ),
                ),
            ],
        ),
    )
'''


def main():
    n = len(BEATS)
    sets = {}
    for season in SEASONS:
        frames = [draw_frame(NOD[BEATS[t]], t, season) for t in range(n)]

        # The device replays a buffered chunk on repeat, so the wrap has to be
        # a legal step. Render the hypothetical frame after the last one and
        # require it to be frame 0 exactly -- the guarantee every future tune
        # to BEATS or the steam wave has to keep, checked per costume.
        assert draw_frame(NOD[BEATS[0]], n, season).tobytes() == frames[0].tobytes(), (
            "%s loop is not seamless: frame %d does not wrap onto 0" % (season, n - 1))
        sets[season] = [encode(f) for f in frames]

    OUT_STAR.write_text(TEMPLATE.format(
        frames_plain=",\n".join('    "%s"' % b for b in sets[PLAIN]),
        frames_santa=",\n".join('    "%s"' % b for b in sets[SANTA]),
        frames_lei=",\n".join('    "%s"' % b for b in sets[LEI]),
        coral="#%02X%02X%02X" % CORAL,
        delay=DELAY_MS,
        last=n - 1,
        tz=TIMEZONE,
        canvas_w=CANVAS_W,
        gap_rows=GAP_ROWS,
        text_rows=TEXT_ROWS,
    ))
    print("frames=%d x %d costumes  base64=%dKB  ->  %s"
          % (n, len(SEASONS),
             sum(len(b) for v in sets.values() for b in v) // 1024, OUT_STAR))


if __name__ == "__main__":
    main()
