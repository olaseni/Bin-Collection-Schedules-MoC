#!/usr/bin/env python3
"""Scrape East Dunbartonshire bin dates into a merged, idempotent bins.ics.

The council page only shows the *next* collection per bin, so each run merges
new dates into the existing file. Events have deterministic UIDs and
timestamps, so re-running never duplicates or churns the file.
"""
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UPRN = "132020155"
URL = ("https://www.eastdunbarton.gov.uk/services/a-z-of-services/"
       "bins-waste-and-recycling/bins-and-recycling/collections/")
PICKUP_TIME = time(7, 0)  # local (Europe/London) collection time
OUT = Path(__file__).parent / "bins.ics"
EVENT_RE = re.compile(r"BEGIN:VEVENT\r?\n(.*?)END:VEVENT", re.S)


def scrape():
    r = requests.get(URL, params={"uprn": UPRN}, timeout=30,
                     headers={"User-Agent": "bin-calendar-hobby/1.0"})
    r.raise_for_status()
    rows = BeautifulSoup(r.text, "html.parser").select("table.bin-table tbody tr")
    found = {}
    for row in rows:
        name = row.find("td").get_text(strip=True)
        date_txt = row.find("span").get_text(strip=True)
        date = datetime.strptime(date_txt, "%A, %d %B %Y").date()
        found[(name, date)] = True
    if not found:
        sys.exit("No collections parsed - page layout may have changed")
    return set(found)


def load_existing():
    if not OUT.exists():
        return set()
    items = set()
    for block in EVENT_RE.findall(OUT.read_bytes().decode()):
        summary = re.search(r"SUMMARY:(.*)", block).group(1).strip()
        start = re.search(r"DTSTART[^:]*:(\d{8})", block).group(1)
        items.add((summary, datetime.strptime(start, "%Y%m%d").date()))
    return items


TIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/London
BEGIN:STANDARD
DTSTART:19701025T020000
TZOFFSETFROM:+0100
TZOFFSETTO:+0000
TZNAME:GMT
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700329T010000
TZOFFSETFROM:+0000
TZOFFSETTO:+0100
TZNAME:BST
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
END:VTIMEZONE""".split("\n")


def alarm(trigger, text):
    return ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{text}",
            f"TRIGGER:{trigger}", "END:VALARM"]


def render(items):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//bin-collection-schedules//EN",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:Bin collections",
             "X-WR-TIMEZONE:Europe/London", *TIMEZONE]
    for name, d in sorted(items, key=lambda x: (x[1], x[0])):
        slug = name.lower().replace(" ", "-")
        start = datetime.combine(d, PICKUP_TIME)
        end = start + timedelta(minutes=15)
        lines += [
            "BEGIN:VEVENT",
            f"UID:bin-{UPRN}-{slug}-{d:%Y%m%d}@bin-collection-schedules",
            f"DTSTAMP:{d:%Y%m%d}T000000Z",  # fixed per event => stable output
            "SEQUENCE:1",
            f"DTSTART;TZID=Europe/London:{start:%Y%m%dT%H%M%S}",
            f"DTEND;TZID=Europe/London:{end:%Y%m%dT%H%M%S}",
            f"SUMMARY:{name}",
            *alarm("-PT12H", f"{name} collection tomorrow at 07:00"),
            *alarm("-PT10M", f"{name} collection in 10 minutes"),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def show():
    for name, d in sorted(load_existing(), key=lambda x: (x[1], x[0])):
        days = (d - date.today()).days
        when = "today" if days == 0 else "tomorrow" if days == 1 else (
            f"in {days} days" if days > 1 else f"{-days} day(s) ago")
        print(f"{d:%a %d %b %Y}  {when:<12} {name}")


if __name__ == "__main__":
    if "--show" in sys.argv:
        show()
        sys.exit()
    merged = load_existing() | scrape()
    new = render(merged)
    if not OUT.exists() or OUT.read_bytes().decode() != new:
        OUT.write_bytes(new.encode())
        print(f"Updated {OUT.name}: {len(merged)} events")
    else:
        print("No changes")
