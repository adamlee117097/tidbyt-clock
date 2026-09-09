#!/usr/bin/env python3
"""Generate the Kaleidoscope Coffee logo animation and write kaleidoscope.star.

Two hand-authored pixel-art flamingos facing each other over a pair of
espresso cups, under the shop's name.

History, so nobody repeats it: the first four rounds of this card downscaled
the shop's actual logo artwork (head/neck split off and rotated, LANCZOS to
26px). It kept the logo's proportions and never read as a flamingo -- the
neck came out as a thick straight column, the bill as a sideways bar, the
body as a blob with an angular wing. Small flamingo sprites that DO read all
do the same few things (see the Mega Voxels 32x32 and perler patterns): a
compact round head, a pale bill hooking DOWN in front of it, a thin vertical
neck rising from the FRONT of a horizontal body, a pointed tail, long bare
legs. So the birds are now drawn by hand as pose grids below, in that idiom.
The old generator is in git history (commit 288420b and before).

Tune the grids and constants below and re-run:  python3 logo/make_frames.py
"""
import base64
import io

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT_STAR = HERE / "kaleidoscope.star"

# ---------------------------------------------------------------- palette
CORAL = (242, 90, 60)      # brand #DF513B pushed up ~12% -- LEDs mute it
DARK = (169, 58, 40)       # the counter line only, so the gold cups stay the
                           # brightest thing down there instead of fusing
                           # with it into one horizontal smear
SHADOW = (168, 56, 40)     # the belly, to give the mass a form instead of a
                           # flat fill. Roughly 2:1 against coral -- any closer
                           # and the panel washes the two together
BEAK = (255, 238, 214)     # the bill in its own colour, hooking down: the cue
                           # every small flamingo sprite leans on. A true
                           # black tip would border the background and vanish,
                           # so the hook is carried by shape alone.
UNLIT = (0, 0, 0)          # the eye. Black is invisible AGAINST black, but
                           # inside a lit shape it is the strongest mark
                           # available
# Wordmark: gray, not white. White (245) sat at ~0.91 relative luminance
# against the birds' ~0.27 -- 3.4x brighter than the thing the card is FOR.
# 185 gray is ~0.48: still 10:1 on black, no longer the brightest object.
WORDMARK_COLOR = (185, 185, 185)
WORDMARK_FONT = "CG-pixel-4x5-mono"  # 4px glyphs, 59px wide, 5 rows: K/D/O/C
                                     # stop being ambiguous, unlike tom-thumb
GOLD = (236, 190, 94)      # the cups; same crema-gold as the shop dashboard
# Steam. Never white and capped at 150 gray (~0.30, level with coral) -- any
# brighter and the steam out-shines the birds. Floor 98 stays >=3.4:1 on
# black; the very first ramp's last steps sat under 2:1 and vanished on a lit
# floor. One entry per VISIBLE climb step; a puff is born bright, fades as it
# rises, then dissipates for the last step of its cycle.
PUFF = [(150, 150, 150), (138, 138, 138), (126, 126, 126),
        (112, 112, 112), (98, 98, 98)]
HEART_COLOR = (128, 128, 128)   # the heart is steam, not a graphic

# ---------------------------------------------------------------- the bird
# Left bird, facing right (the right bird is its mirror). 21 columns x 24
# rows. Legend:  C coral  S shadow  B bill  E eye (unlit, fills on a blink)
#                L leg  F foot  . nothing
# Legs and feet are their own symbols because the weight-shift dip moves
# everything EXCEPT them: the body drops a row onto the planted legs.
#
# The eye is the one 1px feature, and it is inside a lit shape; nothing
# free-standing is thinner than 2px because the panel's inter-diode gutters
# turn a 1px line into dots. Legs are 2px for exactly that reason, confirmed
# on the device. (A 1px unlit wing fold was tried on this body and read as
# three specks, not a line -- the belly shadow does the wing's work.)
NEUTRAL = [
    ".............CCCC....",   # 0  head
    "............CCCCCC...",   # 1
    "............CCECCBB..",   # 2  eye; bill starts in front of the head
    ".............CCCCBB..",   # 3
    ".............CC...B..",   # 4  bill hooks down
    ".............CC......",   # 5  neck: 2px, vertical, from the body's FRONT
    ".............CC......",   # 6
    ".............CC......",   # 7
    ".............CC......",   # 8
    ".............CC......",   # 9
    "......CCCCCCCCCC.....",   # 10 back
    "....CCCCCCCCCCCCC....",   # 11
    "..CCCCCCCCCCCCCCCC...",   # 12
    "CCCCCCCCCCCCCCCCCC...",   # 13 tail point at col 0
    ".CCCSSSSSSSSSSSSS....",   # 14 belly in shadow
    "....SSSSSSSSSSSS.....",   # 15
    "......SSSSSSSSS......",   # 16
    ".........SSSS........",   # 17
    "..........LL.........",   # 18 leg
    "..........LL.........",   # 19
    "..........LL.........",   # 20
    "..........LL.........",   # 21
    "..........LL.........",   # 22
    "..........FFFF.......",   # 23 foot, pointing forward
]
# Half lean: head one column forward, neck starts to tilt.
HALF = [
    "..............CCCC...",
    ".............CCCCCC..",
    ".............CCECCBB.",
    "..............CCCCBB.",
    "..............CC...B.",
    "..............CC.....",
    "..............CC.....",
    ".............CC......",
    ".............CC......",
    ".............CC......",
    "......CCCCCCCCCC.....",
    "....CCCCCCCCCCCCC....",
    "..CCCCCCCCCCCCCCCC...",
    "CCCCCCCCCCCCCCCCCC...",
    ".CCCSSSSSSSSSSSSS....",
    "....SSSSSSSSSSSS.....",
    "......SSSSSSSSS......",
    ".........SSSS........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........FFFF.......",
]
# Full lean: head two columns forward and a row lower, neck a diagonal.
LEAN = [
    ".....................",
    "...............CCCC..",
    "..............CCCCCC.",
    "..............CCECCBB",
    "...............CCCCBB",
    "...............CC...B",
    "...............CC....",
    "..............CC.....",
    "..............CC.....",
    ".............CC......",
    "......CCCCCCCCCC.....",
    "....CCCCCCCCCCCCC....",
    "..CCCCCCCCCCCCCCCC...",
    "CCCCCCCCCCCCCCCCCC...",
    ".CCCSSSSSSSSSSSSS....",
    "....SSSSSSSSSSSS.....",
    "......SSSSSSSSS......",
    ".........SSSS........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........FFFF.......",
]
# Asleep: the neck stays up but the head droops forward and hangs off it, bill
# pointing straight down, eye shut (no eye pixel). A head laid back along the
# body -- what a roosting flamingo really does -- was tried first and at this
# size read as a lump with a loop on it; the drooping hook keeps the neck,
# and the neck is what makes the silhouette a flamingo.
SLEEP = [
    ".....................",
    ".....................",
    ".....................",
    "..............CCC....",
    ".............CCCCCC..",
    ".............CC.CCCC.",
    ".............CC.CCCC.",
    ".............CC..CCBB",
    ".............CC....BB",
    ".............CC.....B",
    "......CCCCCCCCCC.....",
    "....CCCCCCCCCCCCC....",
    "..CCCCCCCCCCCCCCCC...",
    "CCCCCCCCCCCCCCCCCC...",
    ".CCCSSSSSSSSSSSSS....",
    "....SSSSSSSSSSSS.....",
    "......SSSSSSSSS......",
    ".........SSSS........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........LL.........",
    "..........FFFF.......",
]

# ---- the big bird: 23 x 31, for the layout without the wordmark. Taller and
# lankier, not wider -- the corridor for the cups fixes the body width, so
# the extra rows go into the neck and legs, which is where a flamingo keeps
# them anyway. Same legend, same construction.
NEUTRAL_BIG = [
    "...........CCCCC.......",   # 0  head
    "..........CCCCCCC......",   # 1
    "..........CCCECCCBB....",   # 2  eye; bill
    "..........CCCCCCCBB....",   # 3
    "...........CCCCC..BB...",   # 4  bill hooks down
    "............CCC....B...",   # 5  neck: 3px at this size
    "............CCC........",   # 6
    "............CCC........",   # 7
    "............CCC........",   # 8
    "............CCC........",   # 9
    "............CCC........",   # 10
    "............CCC........",   # 11
    "......CCCCCCCCCC.......",   # 12 back
    "....CCCCCCCCCCCCC......",   # 13
    "..CCCCCCCCCCCCCCCC.....",   # 14
    ".CCCCCCCCCCCCCCCCC.....",   # 15
    "CCCCCCCCCCCCCCCCCC.....",   # 16 tail point
    ".CCCSSSSSSSSSSSSSS.....",   # 17 belly
    "...SSSSSSSSSSSSSSS.....",   # 18
    ".....SSSSSSSSSSSS......",   # 19
    ".......SSSSSSSSSS......",   # 20
    ".........SSSSSSS.......",   # 21
    "...........SSSS........",   # 22
    "............LL.........",   # 23 leg
    "............LL.........",   # 24
    "............LL.........",   # 25
    "............LL.........",   # 26
    "............LL.........",   # 27
    "............LL.........",   # 28
    "............LL.........",   # 29
    "............FFFF.......",   # 30 foot
]
# Half lean: the neck tilts, the head does not yet move.
HALF_BIG = [
    "...........CCCCC.......",
    "..........CCCCCCC......",
    "..........CCCECCCBB....",
    "..........CCCCCCCBB....",
    "...........CCCCC..BB...",
    ".............CCC...B...",
    ".............CCC.......",
    ".............CCC.......",
    "............CCC........",
    "............CCC........",
    "............CCC........",
    "............CCC........",
    "......CCCCCCCCCC.......",   # 12 back
    "....CCCCCCCCCCCCC......",   # 13
    "..CCCCCCCCCCCCCCCC.....",   # 14
    ".CCCCCCCCCCCCCCCCC.....",   # 15
    "CCCCCCCCCCCCCCCCCC.....",   # 16 tail point
    ".CCCSSSSSSSSSSSSSS.....",   # 17 belly
    "...SSSSSSSSSSSSSSS.....",   # 18
    ".....SSSSSSSSSSSS......",   # 19
    ".......SSSSSSSSSS......",   # 20
    ".........SSSSSSS.......",   # 21
    "...........SSSS........",   # 22
    "............LL.........",   # 23 leg
    "............LL.........",   # 24
    "............LL.........",   # 25
    "............LL.........",   # 26
    "............LL.........",   # 27
    "............LL.........",   # 28
    "............LL.........",   # 29
    "............FFFF.......",   # 30 foot
]
# Full lean: head one column forward and a row lower. Only one column at
# this size -- two put the two bills in contact at the panel's centre.
LEAN_BIG = [
    ".......................",
    "............CCCCC......",
    "...........CCCCCCC.....",
    "...........CCCECCCBB...",
    "...........CCCCCCCBB...",
    "............CCCCC..BB..",
    ".............CCC....B..",
    ".............CCC.......",
    ".............CCC.......",
    "............CCC........",
    "............CCC........",
    "............CCC........",
    "......CCCCCCCCCC.......",   # 12 back
    "....CCCCCCCCCCCCC......",   # 13
    "..CCCCCCCCCCCCCCCC.....",   # 14
    ".CCCCCCCCCCCCCCCCC.....",   # 15
    "CCCCCCCCCCCCCCCCCC.....",   # 16 tail point
    ".CCCSSSSSSSSSSSSSS.....",   # 17 belly
    "...SSSSSSSSSSSSSSS.....",   # 18
    ".....SSSSSSSSSSSS......",   # 19
    ".......SSSSSSSSSS......",   # 20
    ".........SSSSSSS.......",   # 21
    "...........SSSS........",   # 22
    "............LL.........",   # 23 leg
    "............LL.........",   # 24
    "............LL.........",   # 25
    "............LL.........",   # 26
    "............LL.........",   # 27
    "............LL.........",   # 28
    "............LL.........",   # 29
    "............FFFF.......",   # 30 foot
]
# Asleep: the head has dropped onto the chest -- lower than the small bird's
# droop, so the hanging bill stays clear of the z's climbing the middle.
SLEEP_BIG = [
    ".......................",
    ".......................",
    ".......................",
    ".......................",
    ".......................",
    "............CCCC.......",
    "...........CCCCCCC.....",
    "...........CCC.CCCCC...",
    "...........CCC.CCCCC...",
    "...........CCC.CCCCC...",
    "...........CCC..CCBB...",
    "...........CCC....BB...",
    "......CCCCCCCCCC..B....",
    "....CCCCCCCCCCCCC......",   # 13
    "..CCCCCCCCCCCCCCCC.....",   # 14
    ".CCCCCCCCCCCCCCCCC.....",   # 15
    "CCCCCCCCCCCCCCCCCC.....",   # 16 tail point
    ".CCCSSSSSSSSSSSSSS.....",   # 17 belly
    "...SSSSSSSSSSSSSSS.....",   # 18
    ".....SSSSSSSSSSSS......",   # 19
    ".......SSSSSSSSSS......",   # 20
    ".........SSSSSSS.......",   # 21
    "...........SSSS........",   # 22
    "............LL.........",   # 23 leg
    "............LL.........",   # 24
    "............LL.........",   # 25
    "............LL.........",   # 26
    "............LL.........",   # 27
    "............LL.........",   # 28
    "............LL.........",   # 29
    "............FFFF.......",   # 30 foot
]
# ---------------------------------------------------------------- layout
PANEL_W, PANEL_H = 64, 32
HEART_SHAPE = [".##..##.",   # 8x6, centred on the panel; a 2px point reads,
               "########",   # a 1px one does not
               "########",
               ".######.",
               "..####..",
               "...##..."]


@dataclass
class Layout:
    """Everything that depends on which bird is on the panel."""
    name: str
    poses: list                # NEUTRAL, HALF, LEAN grids
    sleep: list
    top_margin: int            # rows of air over the heads
    gap_rows: int              # blank rows between art and wordmark
    text_rows: int             # wordmark widget height; 0 = no wordmark
    ox: int                    # left bird's column 0; the right bird mirrors
    cup: dict                  # canvas row -> cols, left cup, mirrored
    counter_cols: range        # under the cups, mirrored; stops clear of legs
    puff_col: int              # left column of the 2px puff, left cup
    z_floor: int               # the z climb ends this far below the top
    bird_w: int = field(init=False)
    bird_h: int = field(init=False)
    canvas_h: int = field(init=False)

    def __post_init__(self):
        self.bird_h = len(self.poses[0])
        self.bird_w = len(self.poses[0][0])
        self.canvas_h = self.bird_h + self.top_margin
        for g in self.poses + [self.sleep]:
            assert len(g) == self.bird_h and all(len(r) == self.bird_w for r in g), "%s: ragged pose grid" % self.name
            assert all(set(r) <= set(".CSBELF") for r in g), "%s: unknown symbol in a pose grid" % self.name
        for g in self.poses:
            assert sum(r.count("E") for r in g) == 1, "%s: each awake pose needs exactly one eye" % self.name
        assert "E" not in "".join(self.sleep), "%s: a sleeping bird's eye is shut" % self.name
        assert self.canvas_h + self.gap_rows + self.text_rows == PANEL_H, "%s: rows do not add up to the panel" % self.name
        assert 2 * (self.ox + self.bird_w) <= PANEL_W, "%s: the birds overlap" % self.name
        # The counter the cups stand on: 2 rows (1 was a dotted line through
        # the gutters), spanning the corridor and stopping clear of the legs
        # -- joined to a leg it read as a shelf the bird was standing on.
        self.counter_rows = (max(self.cup) + 1, max(self.cup) + 2)
        self.steam_base_row = min(self.cup) - 1
        self.heart_top = self.steam_base_row - len(HEART_SHAPE) + 1   # point between the cups
        assert self.heart_top >= 0 and max(self.counter_rows) + self.top_margin < self.canvas_h


# 24px birds under the name. 25 art rows + 2 blank + 5 wordmark = 32. The
# blank rows are not optional: LED bloom closes a 0px gap and the feet fuse
# with the text.
WORDMARK_LAYOUT = Layout(
    name="wordmark", poses=[NEUTRAL, HALF, LEAN], sleep=SLEEP,
    top_margin=1, gap_rows=2, text_rows=5, ox=5,
    cup={18: [26, 27, 28, 29],        # rim
         19: [25, 26, 27, 28, 29],    # body + handle, high on the cup: a row
                                      # lower and the cup was widest at the
                                      # bottom and read as a bell
         20: [26, 27, 28, 29],        # body
         21: [27, 28]},               # tapered base
    counter_cols=range(24, PANEL_W // 2),
    puff_col=27, z_floor=3,
)
# 31px birds, no name: 5px text is unreadable past ~6ft on this pitch, the
# mark carries to ~30ft, so this spends the wordmark's rows on the birds.
BIG_LAYOUT = Layout(
    name="big", poses=[NEUTRAL_BIG, HALF_BIG, LEAN_BIG], sleep=SLEEP_BIG,
    top_margin=1, gap_rows=0, text_rows=0, ox=9,
    cup={23: [26, 27, 28, 29],
         24: [25, 26, 27, 28, 29],
         25: [26, 27, 28, 29],
         26: [26, 27, 28, 29],
         27: [27, 28]},
    counter_cols=range(26, PANEL_W // 2),   # the taller legs stand closer
    puff_col=28,               # one column further in than the small layout:
                               # the taller bird's belly reaches col 26
    z_floor=4,
)
LAYOUTS = [WORDMARK_LAYOUT, BIG_LAYOUT]

# ---------------------------------------------------------------- motion
# Pose-to-pose with holds, never tweened 1px at a time -- at this size
# smooth interpolation reads as the sprite melting, not as movement.
# 48 frames @ 66ms = 3.17s; frame 47 flows into frame 0.
BEATS = [0] * 13 + [1] * 3 + [2] * 11 + [1] * 3 + [0] * 18
N_FRAMES = len(BEATS)
DIP_POSE = 2               # on the full lean the body sits 1 row lower with
                           # the feet planted -- a knee bend, so the lean
                           # reads as intent rather than a wobble
LEAN_LANDS = 16            # first frame of the full-lean hold
FLICK_FRAMES = range(LEAN_LANDS + 2, LEAN_LANDS + 5)   # tail tip lifts a row
BLINK_FRAMES = {"left": (6, 7), "right": (36, 37)}    # eye fills, 132ms
PUFF_HOLD = 8              # frames per climb step
PUFF_STEPS = 6             # 6 x 8 = the loop; the sixth step is the gap
PUFF_OFFSETS = (0, 3)      # two puffs per cup, half a cycle apart
RIGHT_PUFF_PHASE = 4       # frames; mirrored steam looks mechanical
HEART = True               # the two steams meet as a heart on the deep lean
HEART_FRAMES = range(LEAN_LANDS, LEAN_LANDS + 8)
Z_ROWS, Z_HOLD, Z_OFFSETS = 12, 4, (0, 6)
# 12 steps of fade, bright at birth. A 3x3 z with a 1px diagonal read as a
# blue chip through the gutters; this is a 4x4 Z with a 2px diagonal.
ZED = [tuple(round(a + (b - a) * i / 11) for a, b in zip((178, 194, 240), (72, 82, 124)))
       for i in range(12)]
Z_SHAPE = ["####", "..##", "##..", "####"]
DELAY_MS = 66
TIMEZONE = "America/New_York"
OPEN_HOUR = 8
CLOSE_HOUR = {"Mon": 17, "Tue": 17, "Wed": 17, "Thu": 17,
              "Fri": 18, "Sat": 18, "Sun": 18}
# Keys are Go weekday abbreviations (now.format("Mon")). A typo would not
# raise -- is_open() falls back to OPEN_HOUR, i.e. shut all day -- so assert.
assert set(CLOSE_HOUR) == {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
assert all(h >= OPEN_HOUR for h in CLOSE_HOUR.values())
assert N_FRAMES == 48 and N_FRAMES % (PUFF_HOLD * PUFF_STEPS) == 0 and N_FRAMES % (Z_ROWS * Z_HOLD) == 0
assert len(PUFF) < PUFF_STEPS, "at least one step of the puff cycle must be empty"
assert BEATS[LEAN_LANDS] == DIP_POSE and BEATS[LEAN_LANDS - 1] != DIP_POSE
assert all(BEATS[f] == DIP_POSE for f in HEART_FRAMES)
assert all(BEATS[f] == 0 for fr in BLINK_FRAMES.values() for f in fr)
assert 0 not in FLICK_FRAMES and 0 not in HEART_FRAMES
assert len(set(len(r) for r in HEART_SHAPE)) == 1 and len(HEART_SHAPE[0]) % 2 == 0


# ---------------------------------------------------------------- drawing
def frame_state(t):
    f = t % N_FRAMES
    pose = BEATS[f]
    return dict(pose=pose, dip=1 if pose == DIP_POSE else 0,
                flick=f in FLICK_FRAMES,
                blink_left=f in BLINK_FRAMES["left"],
                blink_right=f in BLINK_FRAMES["right"],
                heart=HEART and f in HEART_FRAMES,
                puff_tick=t)   # deliberately NOT wrapped: the wrap assert
                               # then really tests the climb comes round


def _flick_tail(rows):
    """Lift the tail tip one row: everything in the two outermost columns
    moves up as a unit, so the point itself moves (moving only the bottom
    pixel of each column was a 1px thickening nobody could see)."""
    grid = [list(r) for r in rows]
    n = len(rows)
    for c in (0, 1):
        col = [grid[y][c] for y in range(n)]
        col = col[1:] + ["."]
        for y in range(n):
            grid[y][c] = col[y]
    return ["".join(r) for r in grid]


def paint_bird(L, px, pose_rows, mirror, bird_px, dip=0, blink=False, flick=False):
    rows = _flick_tail(pose_rows) if flick else list(pose_rows)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == ".":
                continue
            yy = y + (0 if ch in "LF" else dip)
            if ch in "LF" and dip and y - dip >= 0 and rows[y - dip][x] not in ".LF":
                continue        # the dropped body covers this leg row
            cx = L.ox + x
            if mirror:
                cx = PANEL_W - 1 - cx
            cy = yy + L.top_margin
            if not (0 <= cy < L.canvas_h):
                continue
            if ch == "E":
                color = CORAL if blink else UNLIT
            elif ch == "B":
                color = BEAK
            elif ch == "S":
                color = SHADOW
            else:
                color = CORAL
            px[cx, cy] = color
            bird_px.add((cx, cy))


def draw_frame(L, t=0, awake=True):
    st = frame_state(t)
    img = Image.new("RGB", (PANEL_W, L.canvas_h), (0, 0, 0))
    px = img.load()
    birds = set()

    def put(x, y, color):
        px[x, y] = color

    def mirrored(x):
        return PANEL_W - 1 - x

    if not awake:
        paint_bird(L, px, L.sleep, False, birds)
        paint_bird(L, px, L.sleep, True, birds)
        return img, birds     # machines off: no cups, no counter, no steam

    pose = L.poses[st["pose"]]
    paint_bird(L, px, pose, False, birds, dip=st["dip"], blink=st["blink_left"], flick=st["flick"])
    paint_bird(L, px, pose, True, birds, dip=st["dip"], blink=st["blink_right"], flick=st["flick"])

    for row in L.counter_rows:                   # the counter, under the cups
        for x in L.counter_cols:
            put(x, row + L.top_margin, DARK)
            put(mirrored(x), row + L.top_margin, DARK)
    for row, cols in L.cup.items():              # the two espresso cups
        for x in cols:
            put(x, row + L.top_margin, GOLD)
            put(mirrored(x), row + L.top_margin, GOLD)

    if st["heart"]:
        left = PANEL_W // 2 - len(HEART_SHAPE[0]) // 2
        for r, line in enumerate(HEART_SHAPE):
            for c, ch in enumerate(line):
                if ch == "#":
                    put(left + c, L.heart_top + r + L.top_margin, HEART_COLOR)
        return img, birds

    for phase, col0 in ((0, L.puff_col), (RIGHT_PUFF_PHASE, mirrored(L.puff_col + 1))):
        for offset in PUFF_OFFSETS:
            step = ((st["puff_tick"] + phase) // PUFF_HOLD + offset) % PUFF_STEPS
            if step >= len(PUFF):
                continue                         # dissipated
            top = L.steam_base_row - 2 - step    # a row of air over the rim,
                                                 # or the newborn puff fuses
                                                 # into a gray lid on the cup
            for r in (top, top + 1):
                for c in (col0, col0 + 1):
                    put(c, r + L.top_margin, PUFF[step])
    return img, birds


def zed_overlay(L, step):
    """The 'z's, at the heights they have drifted to, fading as they climb."""
    img = Image.new("RGBA", (PANEL_W, L.canvas_h), (0, 0, 0, 0))
    px = img.load()
    left = PANEL_W // 2 - len(Z_SHAPE[0]) // 2
    for offset in Z_OFFSETS:
        i = (step + offset) % Z_ROWS
        row = (Z_ROWS - 1) - i + L.top_margin + L.z_floor
        color = ZED[i] + (255,)
        for r, line in enumerate(Z_SHAPE):
            for c, ch in enumerate(line):
                if ch == "#" and 0 <= row + r < L.canvas_h:
                    px[left + c, row + r] = color
    return img


def encode(img):
    buf = io.BytesIO()
    if img.mode == "RGBA":
        img.save(buf, "PNG", optimize=True)
    else:
        img.convert("P", palette=Image.ADAPTIVE, colors=16).save(buf, "PNG", optimize=True)
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


def _symmetry_guard(L, img):
    """The mark is a mirrored pair; the cups, counter and heart must be too
    (the steam and blinks are deliberately not)."""
    px = img.load()
    for y in range(L.canvas_h):
        for x in range(PANEL_W // 2):
            a, b = px[x, y], px[PANEL_W - 1 - x, y]
            if GOLD in (a, b) or DARK in (a, b) or HEART_COLOR in (a, b):
                assert a == b, "asymmetric cup/counter/heart at (%d,%d)" % (x, y)


def build(L):
    frames = []
    for t in range(N_FRAMES):
        img, birds = draw_frame(L, t)
        _steam_guard(L, img, birds, t)
        _symmetry_guard(L, img)
        frames.append(img)
    wrap, _ = draw_frame(L, N_FRAMES)
    assert wrap.tobytes() == frames[0].tobytes(), "%s: loop is not seamless" % L.name
    assert frames[BLINK_FRAMES["left"][0]].tobytes() != frames[5].tobytes(), "blink changed nothing"
    assert frames[FLICK_FRAMES[0]].tobytes() != frames[FLICK_FRAMES[0] - 1].tobytes(), "flick changed nothing"
    sleep, _ = draw_frame(L, 0, awake=False)
    return frames, sleep, [zed_overlay(L, i) for i in range(Z_ROWS)]


TEMPLATE = '''"""Kaleidoscope Coffee -- the shop's flamingo mark, animated.

Two mirrored flamingos lean in toward each other over a pair of espresso cups
while steam puffs rise off the crema. A short seamless loop by design: a
Tidbyt only buffers a few seconds of a pushed animation and replays that
chunk, so the whole cycle fits inside the buffer and frame {last} flows back
into 0.

Outside shop hours they sleep: heads drooping, the machines off so no steam,
and a pair of "z"s drifting up between them. A closed card with no motion at
all would read as a crashed display rather than a shut shop.

Two layouts are baked in. `wordmark=on`: 24px birds over the name.
`wordmark=off`: 31px birds filling the panel, no name -- 5px text is
unreadable past ~6ft on this pitch anyway, the mark carries to ~30ft.

That choice is made HERE, at render time, so a plain re-push always puts up
the right thing without touching any code. It is also why this app is pushed
every fifteen minutes even though its artwork never changes: a pushed WebP is
frozen until it is replaced, so the cadence is what bounds how stale the card
can be at an 8am open or a 5pm close.

Frames are generated by make_frames.py -- edit the pose grids and constants
there and re-run, don't hand-edit the blobs below.
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

# ---- wordmark layout: 24px birds + the name
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

# ---- big layout: 31px birds, no name
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

    if config.str("wordmark", "on") == "off":
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
        print("%-8s %d frames (%dKB) + sleep" % (L.name, len(frames), sum(map(len, out[L.name][0])) // 1024))

    def blob_list(blobs):
        return ",\n".join('    "%s"' % b for b in blobs)

    wm, big = out["wordmark"], out["big"]
    OUT_STAR.write_text(TEMPLATE.format(
        frames=blob_list(wm[0]), sleep=wm[1], zeds=blob_list(wm[2]),
        frames_big=blob_list(big[0]), sleep_big=big[1], zeds_big=blob_list(big[2]),
        zeds_seq=repr([(i // Z_HOLD) % Z_ROWS for i in range(N_FRAMES)]),
        z_hold=Z_HOLD, n=N_FRAMES, last=N_FRAMES - 1,
        open_hour=OPEN_HOUR, close_hour=repr(CLOSE_HOUR),
        wordmark_color="#%02X%02X%02X" % WORDMARK_COLOR, wordmark_font=WORDMARK_FONT,
        delay=DELAY_MS, tz=TIMEZONE, panel_w=PANEL_W,
        gap_rows=WORDMARK_LAYOUT.gap_rows, text_rows=WORDMARK_LAYOUT.text_rows,
    ))
    print("-> %s (%dKB)" % (OUT_STAR, OUT_STAR.stat().st_size // 1024))


if __name__ == "__main__":
    main()
