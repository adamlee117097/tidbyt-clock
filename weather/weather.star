"""Warm-dark weather face for Tidbyt (64x32) — Greenpoint, Brooklyn.

Blends two keyless sources for the shop's location: NWS gridpoint
forecasts (daily high/low, condition label, precip odds) with Open-Meteo
(~1km HRRR blend) for the current temperature, day/night state, a
raining-right-now icon override, and short-horizon precip probability.
Renders: big current temp, pixel-art condition icon (animated for
rain/snow/storms), condition label, daily high/low and precip chance.
Pushed by GitHub Actions every 10 minutes; the short looping animation
plays natively on-device between pushes.

Config params (pixlet render weather.star key=value):
  $tz - IANA timezone (default America/New_York)
"""

load("render.star", "render")
load("http.star", "http")
load("time.star", "time")

HOURLY_URL = "https://api.weather.gov/gridpoints/OKX/35,43/forecast/hourly"
DAILY_URL = "https://api.weather.gov/gridpoints/OKX/35,43/forecast"

# Open-Meteo blends the ~1km HRRR model at the exact shop coordinates —
# sharper "right now" temp than NWS airport observations, and a
# short-horizon precip probability. NWS stays the forecast backbone.
OM_URL = ("https://api.open-meteo.com/v1/forecast" +
          "?latitude=40.7295&longitude=-73.9540" +
          "&current=temperature_2m,precipitation,weather_code,is_day" +
          "&hourly=precipitation_probability&forecast_hours=6" +
          "&temperature_unit=fahrenheit&timezone=America%2FNew_York")
UA = "tidbyt-weather (github.com/adamlee117097/tidbyt-clock)"
DEFAULT_TZ = "America/New_York"

GOLD = "#FFB000"
AMBER = "#8A6420"
DIM = "#5A3D08"
CLOUD = "#8C8478"
CLOUD_DK = "#5C564E"
RAIN = "#5B8DB8"
SNOW = "#D8D8D8"
FLASH = "#FFE066"
HI_RED = "#FF4D2E"
LO_BLUE = "#4FA0E0"
COLD_BLUE = "#7EC8FF"
MOON = "#D8B45A"

# ---- pixel-art icons ------------------------------------------------------
# strings of palette keys; "." = transparent

PAL = {
    "y": GOLD,
    "o": AMBER,
    "g": CLOUD,
    "d": CLOUD_DK,
    "b": RAIN,
    "w": SNOW,
    "f": FLASH,
    "m": MOON,
    "h": "#78889B",
    "u": HI_RED,
    "v": LO_BLUE,
}

SUN = [
    ".......yy.......",
    ".......yy.......",
    "..y..........y..",
    "...y........y...",
    "......yyyy......",
    ".....yyyyyy.....",
    "....yyyyyyyy....",
    "yy..yyyyyyyy..yy",
    "yy..yyyyyyyy..yy",
    "....yyyyyyyy....",
    ".....yyyyyy.....",
    "......yyyy......",
    "...y........y...",
    "..y..........y..",
    ".......yy.......",
    ".......yy.......",
]

MOON_ICON = [
    "......mmmm......",
    "....mmmmmm......",
    "...mmmm....m....",
    "..mmm.....mmm...",
    "..mmm......m....",
    ".mmm............",
    ".mmm............",
    ".mmm............",
    ".mmm............",
    ".mmm............",
    "..mmm...........",
    "..mmmm..........",
    "...mmmmm........",
    "....mmmmmmm.....",
    "......mmmm......",
    "................",
]

CLOUD_ICON = [
    "................",
    "................",
    "......ggggg.....",
    "....ggggggg.....",
    "...ggggggggg....",
    "..ggggggggggg...",
    ".ggggggggggggg..",
    ".gggggggggggggg.",
    ".gggggggggggggg.",
    "..gggggggggggg..",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]

PARTSUN = [
    "................",
    ".y..yy..........",
    "...yyyy.........",
    "..yyyyyy........",
    "..yyyyyy........",
    "..yyyyyy........",
    "..yyyy.ggggg....",
    "...ggggggggg....",
    "..ggggggggggg...",
    ".ggggggggggggg..",
    ".gggggggggggggg.",
    "..gggggggggggg..",
    "................",
    "................",
    "................",
    "................",
]

FOG = [
    "................",
    "................",
    "..gggggggggg....",
    "................",
    "....gggggggggg..",
    "................",
    "..gggggggggg....",
    "................",
    "....gggggggggg..",
    "................",
    "..gggggggggg....",
    "................",
    "................",
    "................",
    "................",
    "................",
]

CLOUD_TOP = [
    "......ggggg.....",
    "....ggggggg.....",
    "...ggggggggg....",
    "..ggggggggggg...",
    ".ggggggggggggg..",
    ".gggggggggggggg.",
    ".gggggggggggggg.",
    "..gggggggggggg..",
]

BOLT = [
    "......fff.......",
    ".....fff........",
    "....ffffff......",
    "......fff.......",
    ".....fff........",
    "....ff..........",
    "...f............",
    "................",
]

UP_ARROW = [
    "..u..",
    ".uuu.",
    "uuuuu",
]

DOWN_ARROW = [
    "vvvvv",
    ".vvv.",
    "..v..",
]

DROP = [
    ".b.",
    "bbb",
    "bbb",
    ".b.",
]

def bitmap(rows):
    out = []
    for row in rows:
        cells = []
        for ch in row.elems():
            if ch in PAL:
                cells.append(render.Box(width = 1, height = 1, color = PAL[ch]))
            else:
                cells.append(render.Box(width = 1, height = 1))
        out.append(render.Row(children = cells))
    return render.Column(children = out)

def falling_frames(char, cols, n_frames):
    """Cloud with single flakes drifting straight down beneath it, looping."""
    frames = []
    drop_rows = 8
    for f in range(n_frames):
        rows = list(CLOUD_TOP)
        for r in range(drop_rows):
            line = ""
            for c in range(16):
                hit = False
                for i, col in enumerate(cols):
                    if c == col and (r - f + i * 3) % drop_rows == 0:
                        hit = True
                line += char if hit else "."
            rows.append(line)
        frames.append(bitmap(rows))
    return frames

def rain_cloud():
    # blue-gray storm cloud, like the rain-cloud emoji
    return [row.replace("g", "h") for row in CLOUD_TOP]

def rain_frames():
    """Slanted 2px rain streaks under a blue-gray cloud (a la the emoji)."""
    frames = []
    drop_rows = 8
    bases = [5, 8, 11, 14]
    for f in range(drop_rows):
        rows = rain_cloud()
        for r in range(drop_rows):
            line = ""
            for c in range(16):
                hit = False
                for i, base in enumerate(bases):
                    p = (f + i * 3) % drop_rows
                    if (r == p or r == p - 1) and c == base - (r // 2):
                        hit = True
                line += "b" if hit else "."
            rows.append(line)
        frames.append(bitmap(rows))
    return frames

def storm_frames():
    frames = []
    for f in range(8):
        rows = rain_cloud()
        if f in (2, 3):  # lightning flash
            rows += BOLT
        else:
            for r in range(8):
                line = ""
                for c in range(16):
                    line += "b" if (c in (3, 11) and (r - f) % 8 < 2) else "."
                rows.append(line)
        frames.append(bitmap(rows))
    return frames

def pick_icon(short, is_day):
    s = short.lower()
    if "thunder" in s:
        return storm_frames()
    if "snow" in s or "flurr" in s or "sleet" in s or "wintry" in s:
        return falling_frames("w", [2, 6, 10, 13], 8)
    if "rain" in s or "shower" in s or "drizzle" in s:
        return rain_frames()
    if "fog" in s or "mist" in s or "haze" in s:
        return [bitmap(FOG)]
    if "partly" in s or "mostly sunny" in s or "mostly clear" in s:
        return [bitmap(PARTSUN)] if is_day else [bitmap(MOON_ICON)]
    if "cloud" in s or "overcast" in s:
        return [bitmap(CLOUD_ICON)]
    if "sunny" in s or "clear" in s:
        return [bitmap(SUN)] if is_day else [bitmap(MOON_ICON)]
    return [bitmap(CLOUD_ICON)]

def label_for(short):
    """Compress NWS shortForecast into <=14 chars of display label."""
    s = short.lower()
    if "thunder" in s:
        return "T-STORMS"
    if "snow" in s:
        return "SNOW"
    if "sleet" in s or "wintry" in s:
        return "WINTRY MIX"
    if "drizzle" in s:
        return "DRIZZLE"
    if "shower" in s or "rain" in s:
        return "SHOWERS"
    if "fog" in s or "mist" in s:
        return "FOG"
    if "haze" in s:
        return "HAZY"
    if "partly" in s:
        return "PARTLY SUNNY"
    if "mostly sunny" in s:
        return "MOSTLY SUNNY"
    if "mostly clear" in s:
        return "MOSTLY CLEAR"
    if "cloud" in s or "overcast" in s:
        return "CLOUDY"
    if "sunny" in s:
        return "SUNNY"
    if "clear" in s:
        return "CLEAR"
    if "wind" in s or "breezy" in s:
        return "WINDY"
    return short.upper()[:14]

def temp_color(t, celsius):
    cold = 0 if celsius else 32
    hot = 32 if celsius else 90
    if t <= cold:
        return COLD_BLUE
    if t >= hot:
        return HI_RED
    return GOLD

def degree_mark(color):
    return render.Padding(
        pad = (1, 2, 0, 0),
        child = render.Column(
            children = [
                render.Row(children = [
                    render.Box(width = 1, height = 1),
                    render.Box(width = 2, height = 1, color = color),
                    render.Box(width = 1, height = 1),
                ]),
                render.Row(children = [
                    render.Box(width = 1, height = 2, color = color),
                    render.Box(width = 2, height = 2),
                    render.Box(width = 1, height = 2, color = color),
                ]),
                render.Row(children = [
                    render.Box(width = 1, height = 1),
                    render.Box(width = 2, height = 1, color = color),
                    render.Box(width = 1, height = 1),
                ]),
            ],
        ),
    )

def fetch_json(url):
    res = http.get(url, headers = {"User-Agent": UA}, ttl_seconds = 300)
    if res.status_code != 200:
        return None
    return res.json()

def offline(msg):
    return render.Root(
        child = render.Column(
            expanded = True,
            main_align = "center",
            children = [
                render.Row(expanded = True, main_align = "center", children = [
                    render.Text(content = "WEATHER", font = "tom-thumb", color = AMBER),
                ]),
                render.Row(expanded = True, main_align = "center", children = [
                    render.Text(content = msg, font = "tom-thumb", color = DIM),
                ]),
            ],
        ),
    )

def main(config):
    tz = config.get("$tz") or DEFAULT_TZ

    hourly = fetch_json(HOURLY_URL)
    daily = fetch_json(DAILY_URL)
    if hourly == None or daily == None:
        return offline("OFFLINE")

    now_p = hourly["properties"]["periods"][0]
    temp = int(now_p["temperature"])
    short = now_p["shortForecast"]
    is_day = bool(now_p.get("isDaytime", True))

    # ---- Open-Meteo blend (best-effort; NWS values stand if it's down) ----
    om_pop = 0
    om = fetch_json(OM_URL)
    if om != None and "current" in om:
        cur = om["current"]
        t = float(cur.get("temperature_2m", temp))
        temp = int(t + 0.5) if t >= 0 else int(t - 0.5)
        is_day = cur.get("is_day", 1 if is_day else 0) == 1

        # precipitating at the shop right now: let that override the icon
        if float(cur.get("precipitation", 0) or 0) > 0:
            code = int(cur.get("weather_code", 61))
            if code >= 95:
                short = "Thunderstorms"
            elif code in (71, 73, 75, 77, 85, 86):
                short = "Snow"
            else:
                short = "Rain Showers"

        probs = om.get("hourly", {}).get("precipitation_probability", [])
        for p in probs[:6]:
            if p != None and int(p) > om_pop:
                om_pop = int(p)

    d0 = daily["properties"]["periods"][0]
    d1 = daily["properties"]["periods"][1]
    if d0["isDaytime"]:
        hi, lo = int(d0["temperature"]), int(d1["temperature"])
    else:
        # evening: d0 = tonight's low, d1 = tomorrow's high
        hi, lo = int(d1["temperature"]), int(d0["temperature"])

    pop = d0.get("probabilityOfPrecipitation", {}).get("value") or 0
    # surface the most urgent of today's, the next few NWS hours', and
    # Open-Meteo's short-horizon precip odds
    for p in hourly["properties"]["periods"][:4]:
        hp = p.get("probabilityOfPrecipitation", {}).get("value") or 0
        if hp > pop:
            pop = hp
    if om_pop > pop:
        pop = om_pop

    icon_frames = pick_icon(short, is_day)

    tc = temp_color(temp, False)

    top = render.Box(
        height = 20,
        child = render.Row(
            expanded = True,
            main_align = "center",
            cross_align = "center",
            children = [
                render.Padding(
                    pad = (0, 1, 3, 0),
                    child = render.Animation(children = icon_frames),
                ),
                render.Text(content = str(temp), font = "10x20", color = tc),
                degree_mark(tc),
            ],
        ),
    )

    label_row = render.Box(
        height = 6,
        child = render.Text(content = label_for(short), font = "tom-thumb", color = AMBER),
    )

    divider = render.Box(width = 64, height = 1, color = "#33220A")

    footer = render.Box(
        height = 5,
        child = render.Padding(
            pad = (2, 0, 2, 0),
            child = render.Row(
                expanded = True,
                main_align = "space_between",
                children = [
                    render.Row(
                        children = [
                            render.Padding(pad = (0, 1, 1, 0), child = bitmap(UP_ARROW)),
                            render.Text(content = str(hi), font = "tom-thumb", color = HI_RED),
                            render.Box(width = 4, height = 1),
                            render.Padding(pad = (0, 1, 1, 0), child = bitmap(DOWN_ARROW)),
                            render.Text(content = str(lo), font = "tom-thumb", color = LO_BLUE),
                        ],
                    ),
                    render.Row(
                        children = [
                            render.Padding(pad = (0, 0, 1, 0), child = bitmap(DROP)),
                            render.Text(content = str(int(pop)) + "%", font = "tom-thumb", color = RAIN if pop >= 30 else DIM),
                        ],
                    ),
                ],
            ),
        ),
    )

    return render.Root(
        delay = 180,
        child = render.Column(
            children = [top, label_row, divider, footer],
        ),
    )
