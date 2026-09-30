# Bin collection calendar

Scrapes the East Dunbartonshire Council bin collections page for one address
and maintains a subscribable calendar feed, `bins.ics`.

## How it works

- `bins.py` fetches the collections page for the configured `UPRN` and parses
  the next collection date for each bin.
- The council only shows the *next* date per bin, so each run **merges** new
  dates into the existing `bins.ics`. The calendar fills in over time.
- Each event has a deterministic `UID` (`bin-<uprn>-<bin>-<date>`) and a fixed
  `DTSTAMP`, so re-running never duplicates events and never changes the file
  unless there is a genuinely new date.
- A GitHub Actions workflow runs on Monday, Wednesday and Friday (06:00 UTC)
  and commits `bins.ics` when it changes. It can also be run manually from the
  Actions tab.

## Usage

Requires Python 3 and [just](https://github.com/casey/just).

```sh
just run    # set up the venv and update bins.ics
just show   # list events in bins.ics
just clean  # remove the venv
```

## Subscribe

Push this repo to GitHub (public, so calendar apps can fetch it), then add a
calendar by URL:

```
https://raw.githubusercontent.com/<user>/<repo>/main/bins.ics
```

Calendar apps refresh subscribed feeds slowly (often 12-24 hours).

## Changing address

Edit `UPRN` in `bins.py`. Find yours in the `?uprn=` parameter of the council's
collections page after searching for your address.

## Caveats

- If the council changes its page layout, `bins.py` exits with an error and the
  workflow fails visibly.
- A collection that falls entirely between two successful runs is missed.
