from datetime import datetime
import re


def get_timestamp():
    """Get the current timestamp in the format YYYY-MM-DD HH:MM:SS:MMM"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f":{datetime.now().microsecond // 1000:03d}"


def process_line(line):
    """Process a line from the server."""
    # Regex to parse log lines
    pattern = re.compile(r"\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[:,]\d{3}) (?P<level>\w+)\](?: (?P<message>.*))?")
    match = pattern.match(line)
    if match:
        timestamp = match.group("timestamp")
        # Replace comma with colon in timestamp for consistency
        timestamp = timestamp.replace(",", ":")
        level = match.group("level")
        # Calculate spacing for alignment
        spacing = " " * (max(9 - len(level), 1))
        # Get the message part ('or ""' to handle None case)
        message = match.group("message") or ""
        # Return the formatted line
        return [f"{timestamp} {level}{spacing}", message]
    else:
        # If the line doesn't contain a timestamp, return it with an 'RAW' level
        return [f"{get_timestamp()} RAW      ", line]
