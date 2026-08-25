"""Warm-dark weather face for Tidbyt (64x32) — Greenpoint, Brooklyn.

Pulls NWS gridpoint forecasts (no API key) for the shop's location and
renders: big current temp, pixel-art condition icon (animated for
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
}

SUN = [
    ".....y.....",
    ".y...y...y.",
    "..y.....y..",
    "....yyy....",
    "...yyyyy...",
    "y..yyyyy..y",
    "...yyyyy...",
    "....yyy....",
    "..y.....y..",
    ".y...y...y.",
    ".....y.....",
]

MOON_ICON = [
    "....mmm....",
    "..mmmmm....",
    ".mmmm......",
    ".mmm.......",
    ".mmm.......",
    ".mmm.......",
    ".mmm.......",
    ".mmmm......",
    "..mmmmm..m.",
    "....mmmmm..",
    "...........",
]

CLOUD_ICON = [
    "...........",
    "...........",
    "....ggg....",
    "..ggggggg..",
    ".ggggggggg.",
    "gggggggggg.",
    ".gggggggg..",
    "...........",
    "...........",
    "...........",
    "...........",
]

PARTSUN = [
    "..y..y.....",
    "...yyy..y..",
    ".y.yyy.....",
    "...yyyy....",
    "..gggggg...",
    ".gggggggg..",
    "gggggggggg.",
    ".gggggggg..",
    "...........",
    "...........",
    "...........",
]

FOG = [
    "...........",
    "...........",
    ".ggggggg...",
    "...........",
    "..ggggggg..",
    "...........",
    ".ggggggg...",
    "...........",
    "...ggggggg.",
    "...........",
    "...........",
]

CLOUD_TOP = [
    "....ggg....",
    "..ggggggg..",
    ".ggggggggg.",
    "gggggggggg.",
    ".gggggggg..",
]

BOLT = [
    "....ff.....",
    "...ff......",
    "..ffff.....",
    "....ff.....",
    "...ff......",
    "..f........",
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
    """Cloud with precipitation falling beneath it, as n looping frames."""
    frames = []
    drop_rows = 6  # rows 5..10 under the cloud
    for f in range(n_frames):
        rows = list(CLOUD_TOP)
        for r in range(drop_rows):
            line = ""
            for c in range(11):
                hit = False
                for i, col in enumerate(cols):
                    if c == col and (r + f + i * 2) % drop_rows == i % drop_rows:
                        hit = True
                line += char if hit else "."
            rows.append(line)
        frames.append(bitmap(rows))
    return frames

def storm_frames():
    frames = []
    for f in range(8):
        rows = list(CLOUD_TOP)
        if f in (2, 3):  # lightning flash
            rows += BOLT
        else:
            for r in range(6):
                line = ""
                for c in range(11):
                    line += "b" if (c in (2, 8) and (r + f) % 6 == 0) else "."
                rows += [line]
        frames.append(bitmap(rows))
    return frames

def pick_icon(short, is_day):
    s = short.lower()
    if "thunder" in s:
        return storm_frames()
    if "snow" in s or "flurr" in s or "sleet" in s or "wintry" in s:
        return falling_frames("w", [2, 5, 8], 6)
    if "rain" in s or "shower" in s or "drizzle" in s:
        return falling_frames("b", [2, 5, 8], 6)
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

def degree_mark():
    return render.Padding(
        pad = (1, 2, 0, 0),
        child = render.Column(
            children = [
                render.Row(children = [
                    render.Box(width = 1, height = 1),
                    render.Box(width = 2, height = 1, color = GOLD),
                    render.Box(width = 1, height = 1),
                ]),
                render.Row(children = [
                    render.Box(width = 1, height = 2, color = GOLD),
                    render.Box(width = 2, height = 2),
                    render.Box(width = 1, height = 2, color = GOLD),
                ]),
                render.Row(children = [
                    render.Box(width = 1, height = 1),
                    render.Box(width = 2, height = 1, color = GOLD),
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

    d0 = daily["properties"]["periods"][0]
    d1 = daily["properties"]["periods"][1]
    if d0["isDaytime"]:
        hi, lo = int(d0["temperature"]), int(d1["temperature"])
    else:
        # evening: d0 = tonight's low, d1 = tomorrow's high
        hi, lo = int(d1["temperature"]), int(d0["temperature"])

    pop = d0.get("probabilityOfPrecipitation", {}).get("value") or 0
    # surface the more urgent of today's and the next few hours' precip odds
    for p in hourly["properties"]["periods"][:4]:
        hp = p.get("probabilityOfPrecipitation", {}).get("value") or 0
        if hp > pop:
            pop = hp

    icon_frames = pick_icon(short, is_day)

    top = render.Row(
        expanded = True,
        main_align = "center",
        cross_align = "center",
        children = [
            render.Padding(
                pad = (0, 1, 3, 0),
                child = render.Animation(children = icon_frames),
            ),
            render.Text(content = str(temp), font = "10x20", color = GOLD),
            degree_mark(),
        ],
    )

    label_row = render.Row(
        expanded = True,
        main_align = "center",
        children = [
            render.Text(content = label_for(short), font = "tom-thumb", color = AMBER),
        ],
    )

    hl_row = render.Row(
        expanded = True,
        main_align = "space_between",
        children = [
            render.Row(children = [
                render.Text(content = "H", font = "tom-thumb", color = DIM),
                render.Text(content = str(hi), font = "tom-thumb", color = AMBER),
                render.Text(content = " L", font = "tom-thumb", color = DIM),
                render.Text(content = str(lo), font = "tom-thumb", color = AMBER),
            ]),
            render.Row(children = [
                render.Box(width = 1, height = 2),
                render.Text(content = str(int(pop)) + "%", font = "tom-thumb", color = RAIN if pop >= 30 else DIM),
            ]),
        ],
    )

    return render.Root(
        delay = 180,
        child = render.Padding(
            pad = (1, 0, 1, 1),
            child = render.Column(
                expanded = True,
                main_align = "space_between",
                children = [top, label_row, hl_row],
            ),
        ),
    )
