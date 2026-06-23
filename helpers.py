from datetime import datetime, timezone


def parse_utc_date(utc_date_text):
    return datetime.fromisoformat(utc_date_text.replace("Z", "+00:00"))


def result_type(home, away):
    if home > away:
        return "HOME"
    if home < away:
        return "AWAY"
    return "DRAW"


def is_prediction_open(match):
    if match["status"] not in ("TIMED", "SCHEDULED"):
        return False
    if not match["utc_date"]:
        return False
    start_time = parse_utc_date(match["utc_date"])
    now = datetime.now(timezone.utc)
    return now < start_time
