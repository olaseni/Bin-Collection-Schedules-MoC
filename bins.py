#!/usr/bin/env python3
"""Scrape East Dunbartonshire bin dates into a merged, idempotent bins.ics.

The council page only shows the *next* collection per bin, so each run merges
new dates into the existing file. Events have deterministic UIDs and
timestamps, so re-running never duplicates or churns the file.
"""
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UPRN = "132020155"
URL = ("https://www.eastdunbarton.gov.uk/services/a-z-of-services/"
       "bins-waste-and-recycling/bins-and-recycling/collections/")
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
    for block in EVENT_RE.findall(OUT.read_text()):
        summary = re.search(r"SUMMARY:(.*)", block).group(1).strip()
        start = re.search(r"DTSTART;VALUE=DATE:(\d{8})", block).group(1)
        items.add((summary, datetime.strptime(start, "%Y%m%d").date()))
    return items


def render(items):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//bin-collection-schedules//EN",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:Bin collections"]
    for name, d in sorted(items, key=lambda x: (x[1], x[0])):
        slug = name.lower().replace(" ", "-")
        lines += [
            "BEGIN:VEVENT",
            f"UID:bin-{UPRN}-{slug}-{d:%Y%m%d}@bin-collection-schedules",
            f"DTSTAMP:{d:%Y%m%d}T000000Z",  # fixed per event => stable output
            f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
            f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{name}",
            "TRANSP:TRANSPARENT",
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
