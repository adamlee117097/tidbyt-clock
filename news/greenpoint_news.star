"""Hyper-local Greenpoint news for Tidbyt (64x32).

Merges the outlets that actually cover the neighborhood -- Greenpointers,
Brooklyn Paper's Greenpoint tag, NY YIMBY and Greenline (North Brooklyn
News) -- and mixes in what is coming up in its parks and streets, from the
city's permitted-event and NYC Parks event listings. Each render vertically
scrolls two items: white headline, gray one-line summary, a colored line
saying where it came from and how old it is (or, for an event, when). A
story fresher than an hour goes breaking-news yellow with +++ brackets and
holds the first slot for that hour. Free feeds, no API keys.

Only Greenpoint makes the card: a story stays if its headline names
Greenpoint or one of its streets, parks or landmarks, or if it is filed
under Greenpoint and under no other neighborhood. That drops the Williamsburg
openings that took about a fifth of the airtime. Sponsored posts and op-eds
are dropped too.

Stories older than MAX_AGE_DAYS drop out. Five days, because nobody here
publishes on weekends: with three (and fewer stories once Williamsburg
went) the same two headlines looped from Monday afternoon to Tuesday
morning. If the window still comes up empty, the freshest few are shown
anyway; each carries an honest "5D AGO".

The pool rotates by push number (one push per 10 minutes; the workflow
passes it as slot=), so every story in the pool gets reached and, while the
pool holds steady, no story airs twice in a row.
Every other push, the second slot goes to the next event of the coming
week.

Pushed by GitHub Actions, which first copies every source to a mirror on the
runner (mirror=URL) and keeps the last good copy of each. pixlet's HTTP
timeout is a fixed 5s and Starlark cannot catch it, so read live, one slow
site would fail the whole render -- it did, six times in two weeks of
Greenpointers stalls. sources=1 prints the list the workflow mirrors. Run
by hand without mirror=, the star fetches the live URLs itself.

Pushed apps are cut off at the device's app cycle speed (15s by default) --
Tidbyt ignores show_full_animation for API pushes -- so a render gets 200
frames at 75ms. fit_budget() trims summaries, then the second item, until
the scroll fits.

Both fonts draw N three pixels wide -- tom-thumb's as a solid block that
reads as M, CG-pixel-3x5's as an arch -- so text_line() draws every N itself,
four pixels wide like pixlet's 4x5 font does, and leaves every other letter to
the font. That is also why text is wrapped here, not by WrappedText: an N
line is one pixel wider than WrappedText would think.
"""

load("encoding/json.star", "json")
load("http.star", "http")
load("re.star", "re")
load("render.star", "render")
load("time.star", "time")
load("xpath.star", "xpath")

FEEDS = [
    {"key": "gptrs", "tag": "GPTRS", "url": "https://greenpointers.com/feed/", "accent": "#57AB5A"},
    {"key": "bkpaper", "tag": "BK PAPER", "url": "https://www.brooklynpaper.com/tag/greenpoint/feed/", "accent": "#6BB1FF"},
    # the site's /tag/greenpoint/ feed died in 2018; the search feed is live
    {"key": "yimby", "tag": "YIMBY", "url": "https://newyorkyimby.com/?s=greenpoint&feed=rss2", "accent": "#C38BFF"},
    # a monthly paper: it posts a whole issue at once, then nothing for weeks
    {"key": "greenline", "tag": "GREENLINE", "url": "https://northbrooklynnews.com/tag/greenpoint/feed/", "accent": "#2EC4B6"},
]

# Permits filed with the city for events in the 94th Precinct, plus races
# and parades that pass through it (the marathon runs up Manhattan Ave).
# Youth and adult league games are most of the rows; they are left out.
PERMITS = {
    "key": "permits",
    "url": "https://data.cityofnewyork.us/resource/tvpp-9vvx.json?$select=event_name,start_date_time,end_date_time,event_type,event_location&$where=(police_precinct%3D%2794%2C%27%20OR%20(police_precinct%20like%20%27%2594%2C%25%27%20AND%20event_type%20in(%27Parade%27%2C%27Athletic%20Race%20%2F%20Tour%27)))%20AND%20event_type%20not%20like%20%27Sport%25%27&$order=start_date_time&$limit=1000",
}

# NYC Parks programming in the next 14 days in Greenpoint's parks, by ID
# (a name like 'Newtown' also matches a playground in Queens): American
# Playground B001, Greenpoint Playground B043, McCarren B058, McGolrick
# B114, Newtown Barge B135, Transmitter Park B385, 61 Franklin St Garden
# B553, Java Garden B580, Greenpoint Public Park B588, Box Street Park
# B589, Greenpoint Landing B595.
PARKS = {
    "key": "parks",
    "url": "https://data.cityofnewyork.us/resource/w3wp-dpdi.json?$select=title,parknames,starttime,endtime,categories&$where=parkids%20like%20%27%25B001%25%27%20OR%20parkids%20like%20%27%25B043%25%27%20OR%20parkids%20like%20%27%25B058%25%27%20OR%20parkids%20like%20%27%25B114%25%27%20OR%20parkids%20like%20%27%25B135%25%27%20OR%20parkids%20like%20%27%25B385%25%27%20OR%20parkids%20like%20%27%25B553%25%27%20OR%20parkids%20like%20%27%25B580%25%27%20OR%20parkids%20like%20%27%25B588%25%27%20OR%20parkids%20like%20%27%25B589%25%27%20OR%20parkids%20like%20%27%25B595%25%27&$order=starttime&$limit=500",
}

SCAN = 20  # items read per feed, enough to see past the ones filtered out
PER_FEED = 8  # stories kept per feed
SHOW_PER_CYCLE = 2
CACHE_TTL_SECONDS = 600
ANIMATION_SPEED = 75  # ms per frame; see the docstring before raising it
FRAME_BUDGET = 15000 // ANIMATION_SPEED
TZ = "America/New_York"
BREAKING_SECS = 3600
MAX_AGE_DAYS = 5
EVENT_DAYS = 7  # how far ahead events are announced
MULTI_DAY_ROWS = 10  # a permit name with this many rows is a daily run ('Circus': 27 days)
LINE_PX = 64

# The drawn N (see the docstring): 4 pixels wide, 5 tall, like the caps of
# both fonts; with its gap it takes 5 pixels to the fonts' 4.
N_GLYPH = ["#..#", "##.#", "#.##", "#..#", "#..#"]

GP_GREEN = "#1E7A33"
GOLD = "#FFB000"
WHITE = "#FFFFFF"
STORY = "#B8BEC6"
BREAKING = "#FFE100"
EVENT = "#FF8A3D"
HAIRLINE = "#3A3A3A"
HEADER_H = 6
BODY_H = 32 - HEADER_H - 1

# Greenpoint itself, its parks, landmarks and streets. "Greenpoint" also
# matches Greenpointers, which titles its own election guides and markets.
GREENPOINT = r"(?i)\bgreenpoint|mccarren|mcgolrick|mcguinness|transmitter park|newtown creek|monitor point|pulaski bridge|\bg train\b|11222|\b(manhattan|nassau|norman|kingsland|meserole) ave|\b(franklin|india|java|kent|box|huron|milton|noble|eagle|dupont|commercial|west|freeman|green|clay|oak|quay|calyer|guernsey|russell|newel|jewel|diamond) st"

# Neighborhood categories that mark a post as being about somewhere else.
ELSEWHERE = r"(?i)^((east )?williamsburg|bushwick|bed[- ]?stuy|bedford[- ]stuyvesant|long island city|lic|astoria|sunnyside|ridgewood|queens|manhattan|dumbo|downtown brooklyn|fort greene|clinton hill|crown heights|park slope|east new york)$"

# Permit names that say nothing about the event.
GENERIC_EVENTS = ["celebration", "concessions event", "picnic", "barbecue", "miscellaneous", "party", "yoga"]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def strip_html(s):
    # Tag mode only opens on "<" followed by a letter or "/": a bare "<"
    # in prose ("Rents < $2K") must not swallow the rest of the line.
    out = ""
    intag = False
    n = len(s)
    for i in range(n):
        ch = s[i]
        if intag:
            if ch == ">":
                intag = False
        elif ch == "<" and i + 1 < n and (s[i + 1].isalpha() or s[i + 1] == "/"):
            intag = True
        else:
            out += ch

    # Numeric entities, then named ones; bare &amp; LAST so double-encoded
    # sequences stay as text.
    out = decode_numeric(out)
    for a, b in [
        ("&nbsp;", " "),
        ("&hellip;", "..."),
        ("&rsquo;", "'"),
        ("&lsquo;", "'"),
        ("&ldquo;", "\""),
        ("&rdquo;", "\""),
        ("&ndash;", "-"),
        ("&mdash;", "-"),
        ("&apos;", "'"),
        ("&quot;", "\""),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&amp;", "&"),
        ("’", "'"),
        ("‘", "'"),
        ("“", "\""),
        ("”", "\""),
        ("—", "-"),
        ("–", "-"),
        ("…", "..."),
        ("″", "\""),
        ("\u200b", ""),
        # Polish letters have no glyph in the panel fonts and draw as
        # nothing ("Kubuś" showed as "Kubu"); é and ó do draw.
        ("ą", "a"),
        ("ć", "c"),
        ("ę", "e"),
        ("ł", "l"),
        ("ń", "n"),
        ("ś", "s"),
        ("ź", "z"),
        ("ż", "z"),
        ("Ą", "A"),
        ("Ć", "C"),
        ("Ę", "E"),
        ("Ł", "L"),
        ("Ń", "N"),
        ("Ś", "S"),
        ("Ź", "Z"),
        ("Ż", "Z"),
    ]:
        out = out.replace(a, b)
    i = out.find("[ more")
    if i >= 0:
        out = out[:i]

    # WordPress's footer, "The post X appeared first on Y." -- and only
    # that: "The post office on Nassau Avenue..." is news.
    i = out.rfind("The post ")
    if i >= 0 and "appeared first on" in out[i:]:
        out = out[:i]
    return " ".join(out.split())

HEX = "0123456789abcdefABCDEF"

def decode_numeric(s):
    """&#233; and &#xE9; -> é. The city's listings use whatever they like
    ('D&#237;a de Muertos'), so a fixed table can't keep up."""
    if "&#" not in s:
        return s
    parts = s.split("&#")
    out = parts[0]
    for part in parts[1:]:
        semi = part.find(";")
        code = part[:semi] if semi > 0 and semi <= 8 else ""
        n = -1
        if len(code) > 1 and code[0] in "xX" and all([c in HEX for c in code[1:].elems()]):
            n = int(code[1:], 16)
        elif ascii_digits(code):
            n = int(code)
        if n > 0 and n < 0x110000 and (n < 0xD800 or n > 0xDFFF):
            out += chr(n) + part[semi + 1:]
        else:
            out += "&#" + part
    return out

STOPWORDS = ["with", "this", "that", "from", "will", "after", "have",
             "been", "they", "their", "them", "were", "when", "what",
             "your", "more", "some", "just", "into", "over", "about"]

# Teaser lines that tell the reader nothing.
FILLER = ["catch up on this week", "our weekly guide"]

def stems_of(s):
    """4-char stems of significant words, so open/opening and
    prepares/preparing count as the same word."""
    out = []
    cur = ""
    for ch in s.lower().elems():
        if ch.isalnum():
            cur += ch
        else:
            if len(cur) > 3 and cur not in STOPWORDS:
                out.append(cur[:4])
            cur = ""
    if len(cur) > 3 and cur not in STOPWORDS:
        out.append(cur[:4])
    return out

# Words that end in a period without ending the sentence ("Aug. 28",
# "200 Banker St.", "P.S. 110", "8 p.m.").
ABBREVIATIONS = ["jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
                 "st", "ave", "blvd", "rd", "n", "s", "e", "w", "p.s", "a.m", "p.m", "mr", "mrs", "ms",
                 "dr", "jr", "sr", "no", "vs", "inc", "co", "mt", "ft"]

def abbreviation_at(s, i):
    """Whether the period at s[i] closes an abbreviation, or is followed
    by a digit or a lowercase letter -- either way, not a sentence end."""
    if i + 2 < len(s) and (s[i + 2].isdigit() or s[i + 2].islower()):
        return True
    start = 0
    for k in range(i - 1, -1, -1):
        if not (s[k].isalpha() or s[k] == "."):
            start = k + 1
            break
    return s[start:i].lower() in ABBREVIATIONS

def sentences_of(s):
    sents = []
    start = 0
    n = len(s)
    for i in range(n - 1):
        end = False
        if s[i] in ("!", "?") and s[i + 1] == " ":
            end = True
        elif s[i] == "." and s[i + 1] == " " and not abbreviation_at(s, i):
            end = True
        elif s[i] == "\"" and i > 0 and s[i - 1] in (".", "!", "?") and s[i + 1] == " ":
            end = True
        if end:
            sents.append(s[start:i + 1])
            start = i + 2
    if start < n:
        sents.append(s[start:])
    return sents

def shorten(s):
    if len(s) <= 70:
        return s
    # always cut at a word boundary — byte slicing mid-word can split a
    # multibyte character into a garbage glyph
    cut = s[:70]
    last_space = cut.rfind(" ")
    if last_space > 20:
        cut = cut[:last_space]
    return cut + "..."

def pick_summary(title, desc):
    """First sentence that ADDS information. A sentence is an echo if two
    or more of its words, and a third of them, repeat the headline, or if
    it covers a third of the headline's content (stem-matched, so
    inflections count). One shared word is not an echo: "Kaleidoscope's
    last day is November 15." shares only "kale" with its headline."""
    tstems = stems_of(title)
    if not tstems:
        return ""
    for sent in sentences_of(desc)[:4]:
        sent = sent.strip()
        if len(sent) < 20 or sent[0].isdigit() or sent[0].islower():
            continue  # a fragment, cut from a sentence we failed to see whole
        if sent[-1] not in ".!?\"')":
            continue  # cut off: Brooklyn Paper stops its excerpts mid-word
        low = sent.lower()
        if any([f in low for f in FILLER]):
            continue
        sstems = stems_of(sent)
        if not sstems:
            continue
        dup = 0
        for w in sstems:
            if w in tstems:
                dup += 1
        cov = 0
        for w in tstems:
            if w in sstems:
                cov += 1
        if dup >= 2 and dup * 3 >= len(sstems):
            continue
        if cov * 3 >= len(tstems):
            continue
        return shorten(sent)
    return ""

def is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)

def real_date(y, mo, d, h, mi, s):
    """time.parse_time ERRORS on an impossible date (Starlark can't catch
    it), so every field is range-checked before it is called."""
    if mo < 1 or mo > 12 or d < 1 or h > 23 or mi > 59 or s > 59:
        return False
    days = [31, 29 if is_leap(y) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= days[mo - 1]

def ascii_digits(s):
    # str.isdigit() also passes Arabic or fullwidth digits, which int() rejects
    return len(s) > 0 and all([c in "0123456789" for c in s.elems()])

def all_digits(s, spans):
    for a, b in spans:
        if not ascii_digits(s[a:b]):
            return False
    return True

def parse_pub(pub):
    """RFC-822 date in the one shape WordPress emits --
    'Mon, 02 Jan 2006 15:04:05 +0000' -- or None. Each field is checked
    first: a bad weekday, month or digit used to crash the render."""
    if not pub or len(pub) != 31:
        return None
    if pub[0:3] not in WEEKDAYS or pub[3:5] != ", " or pub[8:11] not in MONTHS:
        return None
    if pub[7] != " " or pub[11] != " " or pub[16] != " " or pub[19] != ":" or pub[22] != ":" or pub[25] != " " or pub[26] not in ("+", "-"):
        return None
    if not all_digits(pub, [(5, 7), (12, 16), (17, 19), (20, 22), (23, 25), (27, 31)]):
        return None
    if not real_date(int(pub[12:16]), MONTHS.index(pub[8:11]) + 1, int(pub[5:7]), int(pub[17:19]), int(pub[20:22]), int(pub[23:25])):
        return None
    if int(pub[27:29]) > 14 or int(pub[29:31]) > 59:
        return None
    return time.parse_time(pub, "Mon, 02 Jan 2006 15:04:05 -0700")

def parse_local(s):
    """A city dataset timestamp, '2026-10-31T12:00:00.000', which carries
    no zone: it is New York time. None if it isn't one."""
    if not s or len(s) != 23 or s[4] != "-" or s[7] != "-" or s[10] != "T" or s[13] != ":" or s[16] != ":" or s[19] != ".":
        return None
    if not all_digits(s, [(0, 4), (5, 7), (8, 10), (11, 13), (14, 16), (17, 19), (20, 23)]):
        return None
    if not real_date(int(s[0:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16]), int(s[17:19])):
        return None
    return time.parse_time(s, format = "2006-01-02T15:04:05.000", location = TZ)

def ago(parsed):
    mins = int((time.now() - parsed).minutes)
    if mins < 1:
        return "NOW"
    if mins < 60:
        return str(mins) + "M AGO"
    if mins < 60 * 24:
        return str(mins // 60) + "H AGO"
    return str(mins // (60 * 24)) + "D AGO"

def meta_line(tag, parsed):
    """Source and age on one line: it doesn't wrap, and 'BK PAPER - 23H
    AGO' was cut off at the panel edge."""
    if parsed == None:
        return tag
    meta = tag + " " + ago(parsed)
    if not fits(meta):
        meta = meta.replace(" AGO", "")
    return meta

def looks_like_feed(body):
    head = body[:300]
    return "<rss" in head or "<?xml" in head

def fetch(src, mirror):
    """The source's body, or None if it can't be had. With mirror= set (the
    push workflow) it comes from the runner's copy, which never stalls."""
    res = http.get(mirror + "/" + src["key"] if mirror else src["url"], ttl_seconds = CACHE_TTL_SECONDS)
    if res.status_code != 200:
        return None
    return res.body()

def is_greenpoint(title, cats):
    if re.match(GREENPOINT, title):
        return True
    here = False
    for c in cats:
        if re.match(ELSEWHERE, c.strip()):
            return False
        if re.match(GREENPOINT, c):
            here = True
    return here

def wanted(title, cats):
    if not title:
        return False
    for c in cats:
        if c.strip().lower() in ("sponsored", "op-ed", "oped", "opinion"):
            return False
    if re.match(r"(?i)^(guest )?op-ed\b", title):
        return False
    return is_greenpoint(title, cats)

def get_articles(mirror):
    """Greenpoint stories from every feed that can be read, newest first,
    and how many feeds could be read."""
    items = []
    read = 0
    for feed in FEEDS:
        body = fetch(feed, mirror)
        if body == None or not looks_like_feed(body):
            # HTML error page served with a 200 -- xpath.loads would
            # hard-fail the whole render
            continue
        read += 1
        doc = xpath.loads(body)
        kept = 0
        for i in range(1, SCAN + 1):
            title = doc.query("//item[%d]/title" % i)
            if title == None:
                break
            clean_title = strip_html(title)
            if not wanted(clean_title, doc.query_all("//item[%d]/category" % i)):
                continue
            parsed = parse_pub(doc.query("//item[%d]/pubDate" % i) or "")
            items.append({
                "title": clean_title,
                "description": pick_summary(clean_title, strip_html(doc.query("//item[%d]/description" % i) or "")),
                "meta": meta_line(feed["tag"], parsed),
                "accent": feed["accent"],
                "ts": parsed.unix if parsed else 0,
            })
            kept += 1
            if kept == PER_FEED:
                break
    items = sorted(items, key = lambda a: a["ts"], reverse = True)
    cutoff = time.now().unix - MAX_AGE_DAYS * 86400
    fresh = [it for it in items if it["ts"] >= cutoff]
    if fresh:
        return fresh, read

    # Quiet stretch: nothing inside the window. Show the freshest anyway
    # rather than "no news" -- each one's meta line says how old it is.
    return items[:SHOW_PER_CYCLE], read

def json_rows(body):
    if body == None or not body.lstrip().startswith("["):
        return []
    return json.decode(body)

def street_case(s):
    """'MANHATTAN AVENUE between MILTON STREET and DRIGGS AVENUE' ->
    'Manhattan Ave, Milton St to Driggs Ave'."""
    s = " ".join(s.split()).title()
    for a, b in [(" Avenue", " Ave"), (" Street", " St"), (" Boulevard", " Blvd"), (" Between ", ", "), (" And ", " to ")]:
        s = s.replace(a, b)
    return s

def in_greenpoint(seg):
    """A location segment in Greenpoint. 'X between Y and Z' needs X and Y
    or Z to be Greenpoint streets: Queens has a Greenpoint Avenue, and
    Manhattan Avenue runs on into Williamsburg."""
    low = seg.lower()
    if " between " not in low:
        return bool(re.match(GREENPOINT, seg))
    street, cross = low.split(" between ", 1)
    if not re.match(GREENPOINT, street):
        return False
    for c in cross.split(" and "):
        if re.match(GREENPOINT, c):
            return True
    return False

def place(loc):
    """Where a permitted event is, short: the park, or the street it
    closes. A race or parade lists dozens of street segments."""
    segs = []
    for seg in loc.split(","):
        seg = " ".join(seg.split())
        if seg and seg not in segs and in_greenpoint(seg):
            segs.append(seg)
    streets = [seg for seg in segs if " between " in seg.lower()]
    if len(streets) > 2:
        return "Street closures"
    if streets:
        return street_case(streets[0])
    if segs:
        # "McCarren Park: Lawn South of Field House" -> the park
        return segs[0].split(":")[0].strip()
    return ""

def event_name(name):
    name = strip_html(name)
    m = re.match(r"(?i)^the friends of .*? presents? (.*)$", name)
    if m:
        name = m[0][1]
    name = re.sub(r"\bMUTS\b", "Movie Under the Stars", name)

    # The field is cut at 100 characters and sometimes runs on into a
    # description ("Longevity Stick Longevity Stick is a mix of Tai Chi
    # and"): stop where the name starts over.
    words = name.split(" ")
    if len(words) > 2:
        i = name.find(" " + words[0] + " " + words[1], 1)
        if i > 0:
            name = name[:i]
    return name

def park_key(park):
    """'Monsignor McGolrick Park', 'Msgr. McGolrick Park' -> 'mcgolrick park'."""
    return " ".join(park.lower().split(" ")[-2:])

def clock(t):
    return t.format("3:04PM").replace(":00", "")

def when(start, end, with_time):
    """'TODAY', 'TOMORROW 7PM', 'SAT 10/31', 'NOW TIL 9PM' -- one line
    at most. Permits get no time: theirs is when setup starts (the
    farmers' market is filed for 2:27-2:28 PM)."""
    now = time.now().in_location(TZ)
    s = start.in_location(TZ)
    if s.unix <= now.unix:
        return "NOW TIL " + clock(end.in_location(TZ)) if with_time else "TODAY"
    today = time.time(year = now.year, month = now.month, day = now.day, location = TZ)
    date = s.format("2006-01-02")
    if date == now.format("2006-01-02"):
        day = "TODAY"
    elif date == (today + time.parse_duration("36h")).format("2006-01-02"):
        day = "TOMORROW"
    else:
        day = s.format("Mon 1/2").upper()
    if not with_time:
        return day
    for line in [day + " " + clock(s), s.format("Mon").upper() + " " + clock(s)]:
        if fits(line):
            return line
    return day

def get_events(mirror):
    """What's on in Greenpoint over the next EVENT_DAYS days, soonest
    first, one entry per event."""
    now = time.now().in_location(TZ)
    today = time.time(year = now.year, month = now.month, day = now.day, location = TZ)
    horizon = (today + time.parse_duration("%dh" % (24 * EVENT_DAYS))).unix

    parks = []
    for r in json_rows(fetch(PARKS, mirror)):
        title = strip_html(r.get("title", ""))
        if not title or re.match(r"(?i)fitness|exercise", r.get("categories", "")):
            continue
        start = parse_local(r.get("starttime", ""))
        end = parse_local(r.get("endtime", "")) or start
        if start == None or end.unix < now.unix or start.unix >= horizon:
            continue

        # a canceled event is kept here only so its permit can't stand in for it
        canceled = re.match(r"(?i)^cancell?ed\W*", title)
        if canceled:
            title = title[len(canceled[0][0]):]
        parks.append({"title": title, "park": r.get("parknames", ""), "start": start, "end": end, "with_time": True, "canceled": bool(canceled)})

    rows = json_rows(fetch(PERMITS, mirror))
    count = {}
    for r in rows:
        count[r.get("event_name", "")] = count.get(r.get("event_name", ""), 0) + 1
    permits = []
    for r in rows:
        name = r.get("event_name", "")
        loc = r.get("event_location", "")
        if not name or count[name] >= MULTI_DAY_ROWS or name.lower() in GENERIC_EVENTS or re.match(r"(?i)^bike safety", name):
            continue
        where = place(loc)
        if not where:
            continue
        start = parse_local(r.get("start_date_time", ""))
        end = parse_local(r.get("end_date_time", "")) or start
        if start == None:
            continue

        # Shown by date only, so it stays up all day: the farmers' market
        # is filed for 2:27-2:28 PM.
        s = start.in_location(TZ)
        end_of_day = time.time(year = s.year, month = s.month, day = s.day, location = TZ) + time.parse_duration("24h")
        if end.unix < end_of_day.unix:
            end = end_of_day
        if end.unix < now.unix or start.unix >= horizon:
            continue

        # The same event filed as a permit and listed by Parks ("MUTS
        # McCarren" is "Movie Under the Stars: Sinners"): Parks has the
        # real title, and knows when it is canceled. Same park, overlapping
        # times and two words in common besides the park's own.
        title = event_name(name)
        dup = False
        for p in parks:
            if park_key(p["park"]) != park_key(where) or start.unix >= p["end"].unix or p["start"].unix >= end.unix:
                continue
            skip = stems_of(p["park"] + " " + where)
            shared = [w for w in stems_of(title) if w in stems_of(p["title"]) and w not in skip]
            if len(shared) >= 2:
                dup = True
        if dup:
            continue
        permits.append({"title": title, "park": where, "start": start, "end": end, "with_time": False})

    events = []
    seen = []
    for e in sorted([p for p in parks if not p["canceled"]] + permits, key = lambda e: e["start"].unix):
        if e["title"].lower() in seen:
            continue  # a weekly market or class: just the next one
        seen.append(e["title"].lower())

        # no gray line when the name already says where ("McGolrick Park
        # Farmers' Market" at "Monsignor McGolrick Park")
        events.append({
            "title": e["title"],
            "description": "" if park_key(e["park"]) in e["title"].lower() else e["park"],
            "meta": when(e["start"], e["end"], e["with_time"]),
            "accent": EVENT,
            "ts": e["start"].unix,
            "event": True,
        })
    return events

def is_breaking(article):
    if article.get("event") or article["ts"] <= 0:
        return False

    # the weekly roundups are not news
    if re.match(r"(?i)what's happening|^greenpoint this week", article["title"]):
        return False
    return (time.now().unix - article["ts"]) < BREAKING_SECS

def advance(s):
    """Pixels s takes on a line: 4 a glyph in both fonts, 5 for the drawn
    N. The last of them is the gap after the last glyph."""
    return 4 * len(list(s.codepoints())) + s.count("N")

def fits(s):
    return advance(s) <= LINE_PX + 1

def breakable(s):
    """A word wider than the panel can't wrap and gets clipped
    ('multi-generation'). Split it after a hyphen that fits, or else just
    short of the edge with a hyphen added."""
    out = []
    for word in s.split(" "):
        chars = list(word.codepoints())
        for _ in range(len(chars)):  # Starlark has no while
            if fits("".join(chars)):
                break
            n = 1  # the most characters that fit
            for j in range(2, len(chars) + 1):
                if fits("".join(chars[:j])):
                    n = j
            cut = -1
            for j in range(n):
                if chars[j] == "-":
                    cut = j + 1
            if cut <= 0:
                out.append("".join(chars[:n - 1]) + "-")
                chars = chars[n - 1:]
            else:
                out.append("".join(chars[:cut]))
                chars = chars[cut:]
        out.append("".join(chars))
    return " ".join(out)

def wrap(s):
    """s broken into lines that fit the panel, greedily on spaces, the way
    WrappedText does."""
    lines = []
    for word in breakable(s).split(" "):
        if lines and fits(lines[-1] + " " + word):
            lines[-1] = lines[-1] + " " + word
        else:
            lines.append(word)
    return lines

def headline(article):
    if is_breaking(article):
        return "+++ " + article["title"] + " +++", BREAKING
    return article["title"], WHITE

def height(article):
    """Rows an item takes in the scroll, from the same wrap() that lays it
    out: 6 a headline line, 7 a summary line, 11 for the rest."""
    h = 6 * len(wrap(headline(article)[0])) + 11
    if article["description"]:
        h += 2 + 7 * len(wrap(article["description"]))
    return h

def frames(shown):
    """Frames the Marquee runs for these items: their rows, then BODY_H to
    scroll the last one off."""
    h = BODY_H
    for a in shown:
        h += height(a)
    return h

def fit_budget(shown):
    """Past FRAME_BUDGET the device cuts the scroll off mid-story. Drop the
    second item's summary, then the first's, then the second item."""
    shown = list(shown)
    for i in [1, 0]:
        if frames(shown) <= FRAME_BUDGET:
            return shown
        if i < len(shown):
            shown[i] = dict(shown[i], description = "")
    if frames(shown) > FRAME_BUDGET:
        shown = shown[:1]
    return shown

def pick(news, events, k):
    """The items for push k (a push every 10 minutes).

    A breaking story holds the first slot through its hour. Every other
    push gives its last slot to the next event. The other news rotates on a
    cursor that counts the news slots of every earlier push, so a story
    never airs twice in a row and the whole pool gets reached."""
    shown = []
    for i in range(len(news)):
        if is_breaking(news[i]):
            # a roundup posted since doesn't unpin it
            shown.append(news[i])
            news = news[:i] + news[i + 1:]
            break
    per = SHOW_PER_CYCLE - len(shown)  # news slots on a push without an event
    event = None
    if events and k % 2 == 1:
        event = events[(k // 2) % len(events)]
        per -= 1
    if events:
        cursor = k // 2 * (2 * (SHOW_PER_CYCLE - len(shown)) - 1) + (SHOW_PER_CYCLE - len(shown) if k % 2 else 0)
    else:
        cursor = k * per
    for i in range(min(per, len(news))):
        shown.append(news[(cursor + i) % len(news)])
    if event:
        shown.append(event)

    # Too few stories, or none: fill with events.
    for i in range(len(events)):
        if len(shown) >= SHOW_PER_CYCLE:
            break
        e = events[(k * SHOW_PER_CYCLE + i) % len(events)]
        if e not in shown:
            shown.append(e)
    return shown

def n_glyph(color, height):
    rows = []
    for r in N_GLYPH:
        cells = [render.Box(width = 1, height = 1, color = color) if c == "#" else render.Box(width = 1, height = 1) for c in r.elems()]
        rows.append(render.Row(children = cells + [render.Box(width = 1, height = 1)]))
    if height > len(N_GLYPH):
        rows.append(render.Box(width = 5, height = height - len(N_GLYPH)))
    return render.Column(children = rows)

def text_line(s, font, color):
    """One line of s in font, every N drawn by n_glyph()."""
    children = []
    parts = s.split("N")
    for i in range(len(parts)):
        if i > 0:
            children.append(n_glyph(color, 6 if font == "tom-thumb" else 5))
        if parts[i]:
            children.append(render.Text(content = parts[i], font = font, color = color))
    return render.Row(children = children)

def text_block(s, color, linespacing = 0):
    rows = []
    for line in wrap(s):
        rows.append(text_line(line, "tom-thumb", color))
        if linespacing:
            rows.append(render.Box(height = linespacing))
    return render.Column(children = rows)

def render_header():
    return render.Column(
        children = [
            render.Box(
                width = 64,
                height = HEADER_H,
                color = GP_GREEN,
                child = render.Row(
                    expanded = True,
                    main_align = "center",
                    cross_align = "center",
                    children = [
                        # 63px with its two drawn N's, the gap after the S
                        # included: centering would leave the G on the edge
                        render.Padding(pad = (1, 0, 0, 0), child = text_line("GREENPOINT NEWS", "tom-thumb", WHITE)),
                    ],
                ),
            ),
            render.Box(width = 64, height = 1, color = GOLD),
        ],
    )

def render_articles(articles):
    elements = []
    for article in articles:
        title, color = headline(article)
        elements.append(text_block(title, color))
        if article["description"]:
            elements.append(render.Box(height = 2))
            elements.append(text_block(article["description"], STORY, linespacing = 1))
        if article["meta"]:
            elements.append(render.Box(height = 1))
            elements.append(text_line(article["meta"], "CG-pixel-3x5-mono", article["accent"]))
        elements.append(render.Box(height = 2))
        elements.append(render.Box(width = 64, height = 1, color = HAIRLINE))
        elements.append(render.Box(height = 2))
    return elements

def main(config):
    if config.bool("sources"):
        # for the push workflow's mirror: key, kind, live URL
        for src in FEEDS:
            print("SOURCE", src["key"], "rss", src["url"])
        for src in [PERMITS, PARKS]:
            print("SOURCE", src["key"], "json", src["url"])
        return render.Root(child = render.Box())

    mirror = config.str("mirror", "")
    news, read = get_articles(mirror)
    if not read:
        # No feed could be read at all. A failed render makes the push
        # workflow re-push the previous webp -- real stories, slightly
        # stale -- instead of putting a placeholder on the shop floor.
        fail("no Greenpoint feed could be read")
    events = get_events(mirror)
    if not news and not events:
        fail("feeds read, but nothing about Greenpoint in them")

    # slot=N (preview only) renders push N's pair
    k = time.now().unix // 600
    slot = config.str("slot", "")
    if slot.isdigit():
        k = int(slot)
    shown = fit_budget(pick(news, events, k))

    return render.Root(
        delay = ANIMATION_SPEED,
        show_full_animation = True,
        child = render.Column(
            children = [
                render_header(),
                render.Marquee(
                    height = BODY_H,
                    scroll_direction = "vertical",
                    offset_start = BODY_H,
                    offset_end = BODY_H,
                    child = render.Column(
                        children = render_articles(shown),
                    ),
                ),
            ],
        ),
    )
