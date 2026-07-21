"""Warm-dark clock face for Tidbyt (64x32).

Renders the next FRAMES seconds as a 1 fps animation so the clock keeps
ticking on-device between pushes. Pushed by push-clock.sh every minute
(tidbyt-clock-push.timer); if pushes stop, the animation loops back to
its first frame, so coverage > push interval gives slack for missed runs.

Config params (pixlet render clock.star key=value):
  frames  - seconds of animation to render (default 150)
  $tz     - IANA timezone (default America/New_York)
"""

load("render.star", "render")
load("time.star", "time")

DEFAULT_TZ = "America/New_York"
DEFAULT_FRAMES = 150

GOLD = "#FFB000"       # main digits
COLON_DIM = "#5A3D08"  # colon on off-beat seconds
DATE_AMBER = "#8A6420"  # date line
BAR_TRACK = "#241804"  # seconds bar background
BAR_FILL = "#C8860A"   # seconds bar fill

def clock_frame(t):
    sec = t.second
    colon_color = GOLD if sec % 2 == 0 else COLON_DIM
    bar_width = 64 * (sec + 1) // 60

    # Hand-drawn colon: the 10x20 font's colon glyph sits in a full-width
    # cell, which reads as "2 : 20" at this scale.
    colon = render.Padding(
        pad = (2, 0, 2, 0),
        child = render.Column(
            children = [
                render.Box(width = 2, height = 2, color = colon_color),
                render.Box(width = 2, height = 4),
                render.Box(width = 2, height = 2, color = colon_color),
            ],
        ),
    )

    time_row = render.Row(
        expanded = True,
        main_align = "center",
        cross_align = "center",
        children = [
            render.Text(content = t.format("3"), font = "10x20", color = GOLD),
            colon,
            render.Text(content = t.format("04"), font = "10x20", color = GOLD),
        ],
    )

    date_row = render.Row(
        expanded = True,
        main_align = "center",
        children = [
            render.Text(
                content = t.format("Mon, Jan 2").upper(),
                font = "tom-thumb",
                color = DATE_AMBER,
            ),
        ],
    )

    seconds_bar = render.Stack(
        children = [
            render.Box(width = 64, height = 2, color = BAR_TRACK),
            render.Box(width = bar_width, height = 2, color = BAR_FILL),
        ],
    )

    return render.Column(
        expanded = True,
        main_align = "space_between",
        children = [
            render.Box(height = 1),
            time_row,
            date_row,
            seconds_bar,
        ],
    )

def main(config):
    tz = config.get("$tz") or DEFAULT_TZ
    n_frames = int(config.get("frames") or DEFAULT_FRAMES)
    now = time.now().in_location(tz)
    one_second = time.parse_duration("1s")

    return render.Root(
        delay = 1000,
        show_full_animation = True,
        child = render.Animation(
            children = [clock_frame(now + i * one_second) for i in range(n_frames)],
        ),
    )
