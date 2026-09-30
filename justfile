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

# Run locally: update bins.ics and print its path and events
generate: run show
    @echo "Wrote $(realpath bins.ics)"

# Show the events currently in bins.ics
show:
    @{{venv}}/bin/python bins.py --show

# Remove the virtualenv and caches
clean:
    rm -rf {{venv}} __pycache__
