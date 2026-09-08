#!/usr/bin/env python3
"""Generate the Kaleidoscope Coffee logo animation and write kaleidoscope.star.

The mark is two mirrored flamingos flanking a pair of espresso cups. Rather
than hand-plotting the sprites, the birds are composed at the logo's native
resolution (head/neck split off as its own layer, rotated about the neck
base) and only then downscaled + thresholded -- so every pose keeps the real
logo proportions instead of drifting into hand-drawn approximations.

The bottom band (legs, perch line, cups, feet) IS hand-authored: at this size
the downscale turns the thin legs and the two cups into an unreadable smear,
so those rows are cleared and redrawn as explicit pixel geometry.

Two layouts come out of one pass and both land in the .star:
  - "wordmark": 26px birds over a KALEIDOSCOPE wordmark (the default card)
  - "big":      31px birds filling all 32 rows, no wordmark -- the name is
                unreadable past ~6ft on a 3mm-pitch panel anyway, the mark
                carries to ~30ft, so this spends those rows on the birds.
Pick on the device with `pixlet render ... wordmark=off`.

Tune the constants below and re-run:  python3 logo/make_frames.py
"""
import base64
import io

from collections import deque
from dataclasses import dataclass, field
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
SHADOW = (168, 56, 40)     # the shape's lower edge, to give the mass a form
                           # instead of a flat fill. Roughly 2:1 against coral
                           # -- any closer and the panel washes the two together
BEAK = (255, 238, 214)     # the beak gets its own colour, which is what every
                           # small flamingo sprite does and what this one was
                           # missing. A true black tip is unreachable here --
                           # it would border the background on three sides --
                           # so the downward hook is carried by shape alone.
                           # The notch above it then reads as the dark eye,
                           # which is the convention; a bright pupil there
                           # competed with the beak and read as a glint.
UNLIT = (0, 0, 0)          # the wing fold. Black is invisible AGAINST black,
                           # but inside a lit shape it is the strongest mark
                           # available -- the one place black works here
# Wordmark: gray, not white. In relative luminance white (245) sat at ~0.91
# against the birds' ~0.27 -- 3.4x brighter than the thing the card is FOR,
# so the name led and the mark followed. 185 gray is ~0.48: still 10:1 on
# black, no longer the brightest object on the panel.
WORDMARK_COLOR = (185, 185, 185)
WORDMARK_FONT = "CG-pixel-4x5-mono"  # 4px glyphs, 59px wide, 5 rows: K/D/O/C
                                     # stop being ambiguous. tom-thumb's 3px
                                     # glyphs were, and it is 6 rows tall for
                                     # 5 inked.
GOLD = (236, 190, 94)      # the cups; same crema-gold as the shop dashboard
# Steam. Never white: at panel brightness white steam out-shines the birds
# and the card stops being a logo. Capped at 150 gray (~0.30 luminance, level
# with coral) for the same reason -- the old 190 top step was 2x the birds.
# Floor 98 stays >=3.4:1 against black; the last two steps of the very first
# ramp sat at 2.03:1 and 1.55:1 and simply vanished on a lit shop floor.
# One entry per VISIBLE climb step; a puff is born bright and fades as it
# rises, then dissipates for the last step of its cycle. That gap is what
# keeps the top of the climb off the necks at the deepest, dipped lean --
# the steam guard below caught a sixth visible step kissing the neck.
PUFF = [(150, 150, 150), (138, 138, 138), (126, 126, 126),
        (112, 112, 112), (98, 98, 98)]
HEART_COLOR = (128, 128, 128)   # mid-ramp gray: the heart is steam, not a
                                # graphic, so it must never out-shine coral

# ---------------------------------------------------------------- source
PANEL_W, PANEL_H = 64, 32  # the device itself
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

# ---------------------------------------------------------------- motion
# Positive angle = heads lean INWARD, toward each other over the cups. The
# neck cannot actually reach the cups -- it is near-vertical, so rotating it
# about the shoulder slides the head sideways, not down, and no plausible
# angle puts the beak on a cup. Leaning in is the beat that IS available at
# this size, and past ~20 degrees the two heads collide into one blob.
# Retracting the neck to force a deeper dip was tried and rejected: it eats
# the neck, and the neck is the entire reason the silhouette reads flamingo.
NOD = [0, 7, 14, 20]
# Asleep: the head folds back over the body, which is what a roosting
# flamingo actually does. Past about -65 the head is swallowed by the wing
# and the silhouette stops reading as a bird at all; -48 keeps the tucked
# head distinct from the back. The birds already stand on one leg, so the
# head is the whole tell.
SLEEP_ANGLE = -48
# frame -> NOD index. 48 frames @ 66ms = 3.17s; frame 47 flows into frame 0.
# Pose-to-pose with holds, never tweened 1px at a time -- smooth interpolation
# at 26px reads as the sprite melting, not as movement.
BEATS = ([0] * 13 + [1] * 3 + [2] * 3 + [3] * 8 +
         [2] * 3 + [1] * 3 + [0] * 15)
N_FRAMES = len(BEATS)
# Weight shift: on the deeper leans the whole body drops one row while the
# feet stay planted (a knee bend). Heads lean in AND the mass drops toward
# the cups, which is what makes the lean read as intent rather than a wobble.
# Held for the 8-frame pose-3 hold only, so it is a beat, not a tween: on the
# 3-frame transition poses a 1px drop read as jitter, and it also put the
# necks within a diagonal of the rising steam.
DIP_FROM_POSE = 3          # NOD index at which the body sits 1 row lower
# Follow-through: two frames after the lean lands the tail tip lifts one row
# for three frames. A 2px block, so it survives the gutters.
LEAN_LANDS = 19            # first frame of the NOD[3] hold
FLICK_FRAMES = range(LEAN_LANDS + 2, LEAN_LANDS + 5)
# Blink: the eye notch fills with coral for two frames (132ms), each bird on
# its own beat inside the long holds. It REMOVES pixels rather than adding a
# glint -- the bright pupil that was tried read as a glare and was cut.
BLINK_FRAMES = {"left": (6, 7), "right": (36, 37)}
# Steam: 2x2 puffs, not a 1px wisp -- a 1px column is exactly the thing the
# panel's gutters turn into a dotted line. Born at the rim, one row per hold,
# fading with height (PUFF above), two in flight per cup, the right cup
# half a hold behind the left so the pair never moves in lockstep.
PUFF_HOLD = 8              # frames per climb step
PUFF_STEPS = 6             # 6 x 8 = the 48-frame loop; step 5 is the gap
PUFF_OFFSETS = (0, 3)      # two puffs, half a cycle apart
assert len(PUFF) < PUFF_STEPS, "at least one step of the puff cycle must be empty"
RIGHT_PUFF_PHASE = 4       # frames
# During the deepest lean the two cups' steam meets over the counter as a
# heart -- the latte-art motif, in steam gray so it never competes with the
# birds. Occupies the pose-3 hold and nothing else; puffs resume where they
# would have been. Set HEART = False to drop it -- and expect the steam guard
# to ask for a shorter PUFF ramp, because the dipped necks then meet the
# top of the climb that the heart was standing in for.
HEART = True
HEART_FRAMES = range(LEAN_LANDS, LEAN_LANDS + 8)
HEART_SHAPE = [".##.##.",   # 7x5: a 1px point does not read, this one is 3
               "#######",
               "#######",
               ".#####.",
               "..###.."]
# Sleep. Two "z"s drifting up the corridor between the birds -- a card with no
# motion at all reads as a crashed display rather than a closed shop, and this
# is the quietest motion that still says something.
Z_ROWS = 8                 # eight steps of climb
Z_HOLD = 6                 # frames per step; 8 x 6 = the 48-frame loop
Z_OFFSETS = (0, 4)         # two in flight. One reads as a lone mark; three
                           # abut into a blue ladder, since each is 3 rows tall
ZED = [(178, 194, 240), (162, 178, 226), (144, 160, 210), (126, 142, 194),
       (110, 124, 176), (96, 108, 158), (84, 94, 140), (72, 82, 124)]
DELAY_MS = 66
TIMEZONE = "America/New_York"   # the shop's clock decides awake/asleep

# Shop hours, and therefore when the birds turn in. Mon-Thu 8-5, Fri-Sun 8-6.
OPEN_HOUR = 8
CLOSE_HOUR = {"Mon": 17, "Tue": 17, "Wed": 17, "Thu": 17,
              "Fri": 18, "Sat": 18, "Sun": 18}
# These keys are matched against Go's weekday abbreviations, because that is
# what now.format("Mon") returns. A typo does not raise: is_open()'s lookup
# falls back to OPEN_HOUR, which reads as "shut all day", so one misspelled key
# would silently sleep through a whole weekday every week. A day the shop
# really is closed should be written as an explicit OPEN_HOUR value, so a
# genuine closure and a typo stay distinguishable.
assert set(CLOSE_HOUR) == {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}, (
    "CLOSE_HOUR keys must be Go weekday abbreviations: %s" % sorted(CLOSE_HOUR))
assert all(h >= OPEN_HOUR for h in CLOSE_HOUR.values()), "a day closes before it opens"
assert N_FRAMES % (PUFF_HOLD * PUFF_STEPS) == 0, "puff climb must divide the loop"
assert N_FRAMES % (Z_ROWS * Z_HOLD) == 0, "z drift must divide the loop"
assert max(BEATS) < len(NOD), "BEATS indexes past the end of NOD"
assert all(BEATS[f] == 3 for f in HEART_FRAMES), "the heart must sit inside the pose-3 hold"
assert BEATS[LEAN_LANDS] == 3 and BEATS[LEAN_LANDS - 1] != 3, "LEAN_LANDS is not where the lean lands"
for _side, _fr in BLINK_FRAMES.items():
    assert all(BEATS[f] == 0 for f in _fr), "%s blink must sit inside a pose-0 hold" % _side
assert 0 not in FLICK_FRAMES and 0 not in HEART_FRAMES, "frame 0 must be the plain pose (loop seam)"
assert all(len(r) == len(HEART_SHAPE[0]) for r in HEART_SHAPE), "ragged heart"


# ---------------------------------------------------------------- layouts
@dataclass
class Layout:
    """Everything that depends on how big the birds are.

    The hand band is measured in bird-local columns (0..bird_w-1, mirrored
    about the centre column) and bird-local rows (0 = top of the sprite).
    """
    name: str
    bird_h: int
    canvas_h: int
    top_margin: int           # rows of air above the heads
    gap_rows: int             # blank rows between art and wordmark
    text_rows: int            # wordmark widget height (0 = no wordmark)
    hand_band_width: int      # the bird_w every column below was measured at
    band_top: int             # first row the downscale is discarded from
    leg_col: int
    leg_w: int
    foot_w: int
    foot_row: int
    cup: dict                 # row -> cols, left cup; right one is mirrored
    handle_col: int           # the cup handle column, where the perch meets it
    puff_col: int             # left column of the 2px puff over the left cup
    wing_inset: int           # columns in from the wing's leading edge
    wing_rows: range          # where that edge runs straight enough to trace
    z_floor: int              # the z climb ends this far below the top
    heart_top: int            # heart's top row (bird-local); it is centred

    bird_w: int = field(init=False)
    ox: int = field(init=False)
    mirror: int = field(init=False)
    half: int = field(init=False)

    def __post_init__(self):
        self.bird_w = round(SRC_W * self.bird_h / COMPACT_H)
        self.ox = (PANEL_W - self.bird_w) // 2
        self.mirror = self.bird_w - 1          # x -> mirror - x
        self.half = self.bird_w // 2
        self.bar_row = self.band_top + 2       # the row the cup handle sits on
        # Perch line: only the stretch between the leg and the cup handle. The
        # logo runs it outboard of the legs too, but at this size that turns
        # leg-plus-line into a free-floating "+" that reads as a foreign object.
        self.bar_cols = range(self.leg_col + self.leg_w, self.handle_col)
        self.steam_base_row = self.band_top - 1   # one row above the cup rim
        self.leg_rows = range(self.band_top, self.foot_row)

        # These couplings are what a well-meaning tune breaks silently rather
        # than loudly, so state them where an edit trips over them.
        assert self.bird_w % 2 == 1, (
            "%s: BIRD_W must stay odd (%d) -- the hand band mirrors about a "
            "centre COLUMN, and an even width puts the axis between pixels"
            % (self.name, self.bird_w))
        assert self.bird_w == self.hand_band_width, (
            "%s: bird_w is %d but every hand-authored column (leg_col, cup, "
            "puff_col) and band_top are measured against a %d-wide sprite. "
            "Changing bird_h silently slides the legs and cups off the birds "
            "and moves the band wipe up into the torso -- re-tune those "
            "columns, then update hand_band_width."
            % (self.name, self.bird_w, self.hand_band_width))
        assert self.canvas_h + self.gap_rows + self.text_rows == PANEL_H, (
            "%s: art %d + gap %d + wordmark %d != the panel's %d rows"
            % (self.name, self.canvas_h, self.gap_rows, self.text_rows, PANEL_H))
        assert self.foot_row + self.top_margin < self.canvas_h, "the feet fall off the canvas"
        assert max(self.cup) + self.top_margin < self.canvas_h, "the cups fall off the canvas"
        assert min(self.cup) == self.band_top, "the cup must start at the hand-authored band top"
        assert self.handle_col in self.cup[self.bar_row], (
            "%s: the perch line must meet the cup handle: bar_row %d does not "
            "carry column %d" % (self.name, self.bar_row, self.handle_col))
        assert self.heart_top + len(HEART_SHAPE) <= self.band_top, (
            "the heart must float above the cup rims")


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

# 25 art rows + 2 blank + 5 wordmark = the full 32 rows. The blank rows are
# not optional: LED bloom at across-the-room distance closes a 0px gap and the
# feet visually fuse with the text. TOP_MARGIN spends the row that was
# otherwise structurally dead (art ended at FOOT_ROW, leaving a permanently
# black row above the blank one) on giving the heads a pixel of air instead of
# letting them butt against the panel edge.
WORDMARK = Layout(
    name="wordmark", bird_h=26, canvas_h=25, top_margin=1, gap_rows=2, text_rows=5,
    hand_band_width=39,
    band_top=18,           # the torso's bottom stub is row 17
    leg_col=9, leg_w=2,    # NOT 1. A 1px leg is anatomically right and
                           # unreadable: the panel puts a black gutter between
                           # every diode, so a single-pixel line becomes a
                           # column of separate dots and the bird looks like it
                           # is standing next to its legs rather than on them.
                           # Confirmed on the device, not just in a render.
    foot_w=3, foot_row=23,
    cup={18: [14, 15, 16, 17],       # rim -- widest row, that is what reads
         19: [14, 15, 16, 17],       # body
         20: [13, 14, 15, 16, 17],   # body + handle, meets the perch line
         21: [15, 16]},              # tapered base
    handle_col=13,
    puff_col=16,           # cols 16-17: one column of air off the chest (14)
    wing_inset=3, wing_rows=range(10, 16),
    z_floor=3,             # keeps the climb clear of the birds' heads
    heart_top=13,          # rows 13-17: the point sits in the gap between
                           # the cups, so the heart rises from the counter
)

# The whole panel is birds: 31px tall, 47 wide, corridor 11. Feet on the
# bottom edge, two rows of air over the heads.
BIG = Layout(
    name="big", bird_h=31, canvas_h=32, top_margin=2, gap_rows=0, text_rows=0,
    hand_band_width=47,
    band_top=22,           # the torso's bottom stub is row 21
    leg_col=11, leg_w=2, foot_w=3, foot_row=29,
    cup={22: [17, 18, 19, 20, 21],
         23: [17, 18, 19, 20, 21],
         24: [16, 17, 18, 19, 20, 21],
         25: [17, 18, 19, 20, 21],
         26: [18, 19, 20]},
    handle_col=16,
    puff_col=19,           # cols 19-20: air at 18, chest ends at 17
    wing_inset=4, wing_rows=range(12, 19),
    z_floor=5,
    heart_top=17,          # rows 17-21, point between the cups
)
LAYOUTS = [WORDMARK, BIG]


def _holes(grid):
    """Unlit pixels the border cannot reach -- i.e. the logo's beak notch.

    Found by flood fill rather than by fixed coordinates, so the eye lands
    correctly at every head angle, including the tucked sleeping one, without
    anything to keep in sync.
    """
    h, w = grid.shape
    seen = np.zeros_like(grid)
    queue = deque()
    for r in range(h):
        for c in (0, w - 1):
            if not grid[r, c] and not seen[r, c]:
                seen[r, c] = True
                queue.append((r, c))
    for c in range(w):
        for r in (0, h - 1):
            if not grid[r, c] and not seen[r, c]:
                seen[r, c] = True
                queue.append((r, c))
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            y, x = r + dr, c + dc
            if 0 <= y < h and 0 <= x < w and not grid[y, x] and not seen[y, x]:
                seen[y, x] = True
                queue.append((y, x))
    return (~grid) & (~seen)


def _downscale(L, gray):
    """Source-resolution layer -> the sprite grid, thresholded."""
    im = gray.crop((0, 0, SRC_W, LEG_TRIM))
    small = im.resize((L.bird_w, round(LEG_TRIM * L.bird_h / COMPACT_H)), Image.LANCZOS)
    grid = np.zeros((L.bird_h, L.bird_w), dtype=bool)
    s = np.array(small) > THRESHOLD
    grid[:s.shape[0], :] = s
    return grid


def bird_bitmap(L, angle):
    """Full-res compose at this head angle, then downscale to the sprite grid."""
    hl = HEAD_L.rotate(-angle, resample=Image.BICUBIC, center=(PIVOT_X, PIVOT_Y))
    hr = HEAD_R.rotate(angle, resample=Image.BICUBIC,
                       center=(SRC_W - 1 - PIVOT_X, PIVOT_Y))
    merged = np.maximum(np.maximum(np.array(BODY), np.array(hl)), np.array(hr))
    grid = _downscale(L, Image.fromarray(merged))
    grid[L.band_top:, :] = False  # the downscale's leg/cup mush -- redrawn below

    # Mirror the left half onto the right rather than trusting the downscale
    # to come out symmetric. It does not: LANCZOS lands either side of
    # THRESHOLD by a hair and every frame carried a stray pixel on one bird
    # that its twin lacked. The mark is a mirrored pair, so make that true by
    # construction. The axis column is never lit (asserted at import).
    grid[:, L.bird_w - L.half:] = np.fliplr(grid[:, :L.half])
    return grid


def _flick_tail(L, grid):
    """Lift the tail tip one row: the outermost two columns' block moves up."""
    for cols in ((0, 1), (L.mirror - 1, L.mirror)):
        lit = [r for r in range(grid.shape[0]) if grid[r, cols[0]] or grid[r, cols[1]]]
        if not lit:
            continue
        top, bottom = min(lit), max(lit)
        for c in cols:
            grid[bottom, c] = False
            if top - 1 >= 0:
                grid[top - 1, c] = True
    return grid


def frame_state(t):
    """Everything the frame index decides. Pose things wrap at N_FRAMES; the
    puff phase deliberately does not, so the wrap assert below actually tests
    that the climb comes back round to frame 0."""
    f = t % N_FRAMES
    pose = BEATS[f]
    return dict(
        angle=NOD[pose],
        dip=1 if pose >= DIP_FROM_POSE else 0,
        flick=f in FLICK_FRAMES,
        blink_left=f in BLINK_FRAMES["left"],
        blink_right=f in BLINK_FRAMES["right"],
        heart=HEART and f in HEART_FRAMES,
        puff_tick=t,
    )


def draw_frame(L, angle, tick, awake=True, dip=0, flick=False,
               blink_left=False, blink_right=False, heart=False):
    img = Image.new("RGB", (PANEL_W, L.canvas_h), (0, 0, 0))
    px = img.load()
    bird_px = set()     # canvas coords the birds occupy, for the steam guard

    def put(col, row, color, bird=False):
        y = row + L.top_margin
        if 0 <= y < L.canvas_h and 0 <= col < L.bird_w:
            px[L.ox + col, y] = color
            if bird:
                bird_px.add((L.ox + col, y))

    grid = bird_bitmap(L, angle)
    if dip:
        # The body sits `dip` rows lower; the legs below start that much
        # lower too so the feet stay planted. The torso stub now occupies
        # band_top itself, which the leg columns run straight into.
        grid = np.vstack([np.zeros((dip, L.bird_w), dtype=bool), grid[:-dip]])
    if flick:
        grid = _flick_tail(L, grid)
    rows, cols = grid.shape
    legs = {L.leg_col + i for i in range(L.leg_w)}
    legs |= {L.mirror - c for c in legs}

    # The notch is found BEFORE any blink fills it, so the beak (derived from
    # the notch) stays put with the eye shut.
    holes = _holes(grid)
    blink = np.zeros_like(grid)
    if blink_left:
        blink[:, :L.half] = holes[:, :L.half]
    if blink_right:
        blink[:, L.bird_w - L.half:] = holes[:, L.bird_w - L.half:]

    for y in range(rows):
        for x in range(cols):
            if not grid[y, x] and not blink[y, x]:
                continue
            # Shade the shape's lower edge -- but never in the leg columns.
            # Darkening the belly directly above a leg re-creates the detached
            # look the 2px legs were widened to fix.
            bottom = y + 1 >= rows or not (grid[y + 1, x] or blink[y + 1, x])
            put(x, y, SHADOW if (bottom and x not in legs) else CORAL, bird=True)

    # A 1px fold traced parallel to the wing's leading edge. 2px was tried and
    # reads as a hole punched in the bird rather than as a line.
    for row in L.wing_rows:
        row += dip
        lit = [c for c in range(L.half) if grid[row, c]]
        if not lit:
            continue
        col = min(lit) + L.wing_inset
        if col < L.half and grid[row, col]:
            put(col, row, UNLIT, bird=True)
            put(L.mirror - col, row, UNLIT, bird=True)

    # The beak is the lit run immediately outboard of that notch -- the logo
    # already draws the right shape, it was just the same coral as the bird.
    # Derived from the notch rather than placed, so it tracks the head angle.
    # Not drawn asleep: the folded head turns the notch into a larger enclosed
    # region that reads as a pale blob rather than a bill, and a roosting
    # flamingo has its beak tucked away into its back anyway.
    for row in range(rows) if awake else ():
        notch = [c for c in range(L.half) if holes[row, c]]
        if not notch:
            continue
        col = max(notch) + 1
        while col < L.half and grid[row, col]:
            put(col, row, BEAK, bird=True)
            put(L.mirror - col, row, BEAK, bird=True)
            col += 1

    # Perch line first, legs over it: drawn the other way round its dark
    # pixel lands on top of the leg at any crossing and severs it. It goes
    # with the cups -- on its own it is a stub joining a leg to nothing.
    if awake:
        for col in L.bar_cols:                          # perch line
            put(col, L.bar_row, DARK)
            put(L.mirror - col, L.bar_row, DARK)

    for i in range(L.leg_w):                            # legs
        for row in L.leg_rows:
            if row < L.band_top + dip:
                continue
            put(L.leg_col + i, row, CORAL, bird=True)
            put(L.mirror - L.leg_col - i, row, CORAL, bird=True)
    for i in range(L.foot_w):                           # feet
        put(L.leg_col + i, L.foot_row, CORAL, bird=True)
        put(L.mirror - L.leg_col - i, L.foot_row, CORAL, bird=True)

    if not awake:              # machines off -- no cups, no steam, shop shut
        return img, bird_px

    for row, cs in L.cup.items():                       # the two espresso cups
        for col in cs:
            put(col, row, GOLD)
            put(L.mirror - col, row, GOLD)

    if heart:
        hw = len(HEART_SHAPE[0])
        left = L.half - hw // 2
        for r, line in enumerate(HEART_SHAPE):
            for c, ch in enumerate(line):
                if ch == "#":
                    put(left + c, L.heart_top + r, HEART_COLOR)
        return img, bird_px

    for phase, col0 in ((0, L.puff_col), (RIGHT_PUFF_PHASE, L.mirror - L.puff_col - 1)):
        for offset in PUFF_OFFSETS:
            step = ((tick + phase) // PUFF_HOLD + offset) % PUFF_STEPS
            if step >= len(PUFF):
                continue                                # dissipated
            top = L.steam_base_row - 1 - step
            for r in (top, top + 1):
                for c in (col0, col0 + 1):
                    put(c, r, PUFF[step])
    return img, bird_px


def zed_overlay(L, step):
    """The 'z's, at the heights they have drifted to, fading as they climb."""
    img = Image.new("RGBA", (PANEL_W, L.canvas_h), (0, 0, 0, 0))
    px = img.load()
    m = L.half
    for offset in Z_OFFSETS:
        i = (step + offset) % Z_ROWS
        row = (Z_ROWS - 1) - i + L.top_margin + L.z_floor
        color = ZED[i] + (255,)
        for col in (m - 1, m, m + 1):                   # top and bottom bars
            for r in (row, row + 2):
                if 0 <= r < L.canvas_h:
                    px[L.ox + col, r] = color
        if 0 <= row + 1 < L.canvas_h:                     # the diagonal
            px[L.ox + m, row + 1] = color
    return img


def encode(img):
    buf = io.BytesIO()
    if img.mode == "RGBA":
        img.save(buf, "PNG", optimize=True)      # the z overlays keep alpha
    else:
        img.convert("P", palette=Image.ADAPTIVE, colors=16).save(
            buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def _steam_guard(L, img, bird_px, t):
    """Steam must never touch a bird: a puff or heart pixel on, or even
    diagonally adjacent to, a bird pixel fuses with it under LED bloom and
    reads as a growth on the bird."""
    px = img.load()
    for x in range(PANEL_W):
        for y in range(L.canvas_h):
            if px[x, y] in PUFF or px[x, y] == HEART_COLOR:
                for dx in (-1, 0, 1):
                  for dy in (-1, 0, 1):
                    assert (x + dx, y + dy) not in bird_px, (
                        "%s frame %d: steam at (%d,%d) touches a bird at (%d,%d)"
                        % (L.name, t, x, y, x + dx, y + dy))


def build(L):
    frames = []
    for t in range(N_FRAMES):
        st = frame_state(t)
        img, birds = draw_frame(L, st["angle"], st["puff_tick"], dip=st["dip"],
                                flick=st["flick"], blink_left=st["blink_left"],
                                blink_right=st["blink_right"], heart=st["heart"])
        _steam_guard(L, img, birds, t)
        frames.append(img)

    # The device replays a buffered chunk on repeat, so the wrap has to be a
    # legal step. Render the hypothetical frame after the last one and require
    # it to be frame 0 exactly -- the guarantee every future tune to BEATS,
    # the puff climb or the blink/flick/heart schedule has to keep.
    st = frame_state(N_FRAMES)
    wrap, _ = draw_frame(L, st["angle"], st["puff_tick"], dip=st["dip"],
                         flick=st["flick"], blink_left=st["blink_left"],
                         blink_right=st["blink_right"], heart=st["heart"])
    assert wrap.tobytes() == frames[0].tobytes(), (
        "%s: loop is not seamless: frame %d does not wrap onto frame 0" % (L.name, N_FRAMES - 1))
    # Every awake frame must have found the notch on both birds; the beak and
    # the blink both hang off it.
    for t in range(N_FRAMES):
        st = frame_state(t)
        g = bird_bitmap(L, st["angle"])
        h = _holes(g)
        assert h[:, :L.half].any() and h[:, L.bird_w - L.half:].any(), (
            "%s frame %d: no beak notch found" % (L.name, t))
    # The blink must actually change something, and the flick too.
    assert frames[BLINK_FRAMES["left"][0]].tobytes() != frames[BLINK_FRAMES["left"][0] - 1].tobytes()
    assert frames[FLICK_FRAMES[0]].tobytes() != frames[FLICK_FRAMES[0] - 1].tobytes()

    sleep, _ = draw_frame(L, SLEEP_ANGLE, 0, awake=False)
    zeds = [zed_overlay(L, i) for i in range(Z_ROWS)]
    return frames, sleep, zeds


TEMPLATE = '''"""Kaleidoscope Coffee -- the shop's flamingo mark, animated.

Two mirrored flamingos lean in toward each other over a pair of espresso cups
while steam puffs rise off the crema. A short seamless loop by design: a
Tidbyt only buffers a few seconds of a pushed animation and replays that
chunk, so the whole cycle fits inside the buffer and frame {last} flows back
into 0.

Outside shop hours they sleep: heads folded back over their bodies, the
machines off so no steam, and a pair of "z"s drifting up between them. A
closed card with no motion at all would read as a crashed display rather than
a shut shop.

That choice is made HERE, at render time, so a plain re-push always puts up
the right thing without touching any code. It is also why this app is pushed
every fifteen minutes even though its artwork never changes: a pushed WebP is
frozen until it is replaced, so the cadence is what bounds how stale the card
can be at an 8am open or a 5pm close.

Two layouts are baked in. `wordmark=on` (default): 26px birds over the name.
`wordmark=off`: 31px birds filling the panel, no name -- 5px text is
unreadable past ~6ft on this pitch anyway, the mark carries to ~30ft.

Frames are generated by make_frames.py -- edit the constants there and re-run,
don't hand-edit the blobs below.
"""

load("render.star", "render")
load("encoding/base64.star", "base64")
load("time.star", "time")

WORDMARK = "KALEIDOSCOPE"
WORDMARK_COLOR = "{wordmark_color}"
WORDMARK_FONT = "{wordmark_font}"
DELAY_MS = {delay}
TZ = "{tz}"

OPEN_HOUR = {open_hour}
CLOSE_HOUR = {close_hour}

# ---- wordmark layout: {wm_h}px birds + the name
FRAMES = [
{frames}
]
# Asleep: one still frame, plus a "z" that climbs one step every {z_hold}
# frames. Held as separate images indexed by ZEDS_SEQ rather than as {n}
# near-identical frames.
SLEEP = "{sleep}"
ZEDS = [
{zeds}
]

# ---- big layout: {big_h}px birds, no name
FRAMES_BIG = [
{frames_big}
]
SLEEP_BIG = "{sleep_big}"
ZEDS_BIG = [
{zeds_big}
]
ZEDS_SEQ = {zeds_seq}

def is_open(now):
    # There is no weekday attribute on a pixlet time; format("Mon") is how you
    # get one. An unrecognised key would fall back to OPEN_HOUR and read as
    # "shut all day", so the generator asserts the table's keys.
    close = CLOSE_HOUR.get(now.format("Mon"), OPEN_HOUR)
    return now.hour >= OPEN_HOUR and now.hour < close

def art_for(frames, sleep, zeds, awake):
    if awake:
        return render.Animation(
            children = [render.Image(src = base64.decode(f)) for f in frames],
        )
    return render.Stack(
        children = [
            render.Image(src = base64.decode(sleep)),
            render.Animation(
                children = [render.Image(src = base64.decode(zeds[i])) for i in ZEDS_SEQ],
            ),
        ],
    )

def main(config):
    # `pixlet render ... state=asleep` forces the closed card, for previewing
    # without waiting for closing time. `wordmark=off` picks the big layout.
    now = time.now().in_location(TZ)
    state = config.str("state", "")
    awake = is_open(now) if state not in ("awake", "asleep") else state == "awake"
    big = config.str("wordmark", "on") == "off"

    if big:
        children = [art_for(FRAMES_BIG, SLEEP_BIG, ZEDS_BIG, awake)]
    else:
        children = [
            art_for(FRAMES, SLEEP, ZEDS, awake),
            render.Box(width = {panel_w}, height = {gap_rows}),
            # Box, not Row: a Row shrinks to fit its child, so main_align
            # has no slack to centre within and the wordmark sits flush
            # left. A fixed-width Box centres its child on both axes.
            render.Box(
                width = {panel_w},
                height = {text_rows},
                child = render.Text(
                    content = WORDMARK,
                    font = WORDMARK_FONT,
                    color = WORDMARK_COLOR,
                ),
            ),
        ]

    return render.Root(
        delay = DELAY_MS,
        child = render.Column(children = children),
    )
'''


def main():
    out = {}
    for L in LAYOUTS:
        frames, sleep, zeds = build(L)
        out[L.name] = ([encode(f) for f in frames], encode(sleep), [encode(z) for z in zeds])
        print("%-8s %d frames (%dKB) + sleep"
              % (L.name, len(frames), sum(len(encode(f)) for f in frames) // 1024))

    def blob_list(blobs):
        return ",\n".join('    "%s"' % b for b in blobs)

    wm, big = out["wordmark"], out["big"]
    OUT_STAR.write_text(TEMPLATE.format(
        frames=blob_list(wm[0]), sleep=wm[1], zeds=blob_list(wm[2]),
        frames_big=blob_list(big[0]), sleep_big=big[1], zeds_big=blob_list(big[2]),
        zeds_seq=repr([(i // Z_HOLD) % Z_ROWS for i in range(N_FRAMES)]),
        z_hold=Z_HOLD, n=N_FRAMES,
        open_hour=OPEN_HOUR,
        close_hour=repr(CLOSE_HOUR),
        wordmark_color="#%02X%02X%02X" % WORDMARK_COLOR,
        wordmark_font=WORDMARK_FONT,
        delay=DELAY_MS,
        last=N_FRAMES - 1,
        tz=TIMEZONE,
        panel_w=PANEL_W,
        gap_rows=WORDMARK.gap_rows,
        text_rows=WORDMARK.text_rows,
        wm_h=WORDMARK.bird_h,
        big_h=BIG.bird_h,
    ))
    print("->", OUT_STAR, "(%dKB)" % (OUT_STAR.stat().st_size // 1024))


if __name__ == "__main__":
    main()
