venv := ".venv"

default:
    @just --list

# Create the virtualenv and install dependencies
setup:
    python3 -m venv {{venv}}
    {{venv}}/bin/pip install -q -r requirements.txt

# Scrape the council page and merge new dates into bins.ics
run: setup
    {{venv}}/bin/python bins.py

# Show the events currently in bins.ics
show:
    @grep -E '^(DTSTART|SUMMARY)' bins.ics | paste - - | sed 's/DTSTART;VALUE=DATE://; s/SUMMARY://'

# Remove the virtualenv and caches
clean:
    rm -rf {{venv}} __pycache__
