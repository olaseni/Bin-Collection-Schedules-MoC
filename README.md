# Bin collection calendar

Scrapes the East Dunbartonshire Council bin collections page for one address
and maintains a subscribable calendar feed, `bins.ics`.

The process has two legs:

1. **Producer (this repo):** a script scrapes the council page and keeps
   `bins.ics` up to date, on a schedule, via GitHub Actions.
2. **Consumer (you, once):** your calendar app subscribes to the hosted
   `bins.ics` URL and refreshes it periodically. See [Subscribing](#subscribing-to-the-feed).

## Source

Crawled URL (server-rendered HTML, no JavaScript or login needed):

```
https://www.eastdunbarton.gov.uk/services/a-z-of-services/bins-waste-and-recycling/bins-and-recycling/collections/?uprn=132020155
```

- `uprn` is the Unique Property Reference Number for the address. It is the
  only address-specific input. To find yours, search your address on the
  council's collections page; the resulting URL contains `?uprn=<number>`.
- The council offers **no calendar export or API**, hence the scraping.
- The page shows a table (`table.bin-table`) with one row per bin (food caddy,
  green, brown, blue, grey). Each row has the bin name (first `<td>`) and the
  **next** collection date (in a `<span>`, formatted like
  `Sunday, 04 October 2026`).

## Strategy

### Accumulate, don't replace

The council only exposes the *next* collection per bin, not a full schedule.
So each run **merges** the freshly scraped dates into the existing `bins.ics`
(union of old and new events). The calendar therefore fills in over time, and
past events are kept. Nothing is ever deleted.

### Idempotency

Running the script any number of times must not duplicate events or churn the
file. This is achieved by:

- **Deterministic `UID`:** `bin-<uprn>-<bin-slug>-<yyyymmdd>@bin-collection-schedules`.
  Calendar apps treat the same UID as the same event, so re-importing or
  re-subscribing updates rather than duplicates.
- **Fixed `DTSTAMP`:** derived from the event date, not the current time, so
  output is byte-identical when nothing changed.
- **Sorted output** with CRLF line endings (as the iCalendar spec requires).
- The file is only rewritten when the content differs, so the workflow only
  commits on genuinely new dates.

Events are all-day (`DTSTART;VALUE=DATE`) and marked `TRANSP:TRANSPARENT`
(show as free, not busy).

### Failure behaviour

If the table yields no rows (e.g. the council changes its layout), `bins.py`
exits with an error and the workflow run fails visibly rather than writing an
empty file.

## Automation (GitHub Actions)

[.github/workflows/bins.yml](.github/workflows/bins.yml):

- Runs Monday, Wednesday and Friday at 06:00 UTC, and on demand via
  **Actions → Update bin calendar → Run workflow**.
- Installs dependencies, runs `python bins.py`, and commits `bins.ics` back to
  the repo only if it changed. Needs `contents: write` (already set in the
  workflow).
- Bins are collected roughly weekly/fortnightly, so three runs a week means a
  date is almost always captured well before collection day. A collection that
  falls entirely between two successful runs would be missed.
- GitHub disables scheduled workflows after 60 days of repo inactivity. The
  commits this job makes count as activity, but if the council dates never
  change for a long period you may need to re-enable it from the Actions tab.

## Local usage

Requires Python 3 and [just](https://github.com/casey/just).

```sh
just generate  # update bins.ics locally and show its events
just run       # same, without the event listing
just show      # list events with readable dates and days remaining
just clean     # remove the virtualenv
```

`just show` output looks like:

```
Fri 02 Oct 2026  in 2 days    Grey bin
Sun 04 Oct 2026  in 4 days    Blue bin
```

Local runs modify `bins.ics` in your working copy; commit and push it if you
want the hosted feed to include it (otherwise the next scheduled run will
catch up anyway).

## Setup from scratch

1. Create a GitHub repo and push this project. **Make it public** so calendar
   apps can fetch the raw file without authentication. (A private repo's raw
   URL requires a token, which calendar apps cannot supply.)
2. In the repo settings, confirm **Actions → General → Workflow permissions**
   allows read and write (the workflow also declares this itself).
3. Trigger the workflow once manually to confirm it runs, or run
   `just generate` locally and push.
4. Subscribe your calendar (next section).

## Subscribing to the feed

This is the step that happens once, in your calendar app, outside this repo.
Use the **raw file URL**:

```
https://raw.githubusercontent.com/<user>/<repo>/main/bins.ics
```

Subscribe by URL rather than importing the file. Importing copies events once
and never updates; subscribing keeps the calendar in sync as the repo updates.

| Calendar | How |
|----------|-----|
| Google Calendar (web) | Other calendars **+** → **From URL** → paste the URL → Add calendar |
| Apple Calendar (macOS) | File → New Calendar Subscription → paste URL → choose refresh interval |
| Apple Calendar (iOS) | Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar |
| Outlook (web) | Add calendar → Subscribe from web → paste URL |

Notes:

- **Refresh is controlled by the calendar app, not us.** Google Calendar can
  take 12-24 hours or more to pick up changes; Apple lets you choose an
  interval. The feed is read-only from the calendar's side.
- Google only supports subscribing on the web, but the subscription then syncs
  to its mobile apps.
- Importing the same `.ics` file manually is also safe: stable UIDs mean
  re-imports update existing events instead of duplicating them.
- To unsubscribe, delete the subscribed calendar; events disappear with it.
- If the repo URL, owner or default branch changes, the subscription breaks
  and must be recreated with the new URL.

## Files

| File | Purpose |
|------|---------|
| `bins.py` | Scraper, merger and ICS writer; `--show` lists events |
| `bins.ics` | The generated calendar feed (committed) |
| `justfile` | Local commands |
| `requirements.txt` | `requests`, `beautifulsoup4` |
| `.github/workflows/bins.yml` | Scheduled update job |

## Changing address

Edit `UPRN` in `bins.py`. Existing events for the old address remain in
`bins.ics` unless you delete the file first (their UIDs embed the old UPRN, so
they won't collide with new ones).
