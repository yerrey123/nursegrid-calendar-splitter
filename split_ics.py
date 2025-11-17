import json
import os
import urllib.request

CONFIG_PATH = "config.json"
OUTPUT_DIR = "docs"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_ics(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        return resp.read().decode("utf-8")


def split_events(ics_text: str):
    """
    Split raw ICS text into:
      - header (everything before first BEGIN:VEVENT)
      - list of event blocks (each from BEGIN:VEVENT to END:VEVENT)
    """
    lines = ics_text.splitlines()
    header_lines = []
    events = []

    in_event = False
    current_event_lines = []

    for line in lines:
        if line.startswith("BEGIN:VEVENT"):
            in_event = True
            current_event_lines = [line]
        elif line.startswith("END:VEVENT"):
            current_event_lines.append(line)
            events.append("\n".join(current_event_lines))
            in_event = False
        elif in_event:
            current_event_lines.append(line)
        else:
            header_lines.append(line)

    header = "\n".join(header_lines)
    return header, events


def event_matches(event_text: str, keyword: str) -> bool:
    """
    Return True if keyword appears in SUMMARY / DESCRIPTION / LOCATION
    (case-insensitive).
    """
    kw = keyword.lower()
    for line in event_text.splitlines():
        if line.upper().startswith(("SUMMARY", "DESCRIPTION", "LOCATION")):
            if kw in line.lower():
                return True
    return False


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_calendar_file(header: str, events, slug: str):
    # Remove any END:VCALENDAR from header if present
    header_lines = [
        l for l in header.splitlines() if not l.strip().upper().startswith("END:VCALENDAR")
    ]
    base_header = "\n".join(header_lines)

    ics_body = base_header + "\n"
    ics_body += "\n".join(events) + "\n"
    ics_body += "END:VCALENDAR\n"

    out_path = os.path.join(OUTPUT_DIR, f"{slug}.ics")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(ics_body)
    print(f"Wrote {out_path} with {len(events)} events")


def main():
    cfg = load_config()
    source_url = cfg["source_url"]
    calendars = cfg["calendars"]

    print(f"Fetching ICS from {source_url} ...")
    ics_text = fetch_ics(source_url)
    print("Fetched ICS, splitting events...")
    header, events = split_events(ics_text)
    print(f"Found {len(events)} events in source calendar")

    ensure_output_dir()

    for cal in calendars:
        slug = cal["name"]
        keyword = cal["keyword"]
        print(f"Building calendar '{slug}' for keyword '{keyword}'")

        matched = [e for e in events if event_matches(e, keyword)]

        write_calendar_file(header, matched, slug)


if __name__ == "__main__":
    main()
