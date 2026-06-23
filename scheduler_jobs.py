from datetime import datetime, timedelta, timezone
from database import get_db
from helpers import parse_utc_date
from football_api import sync_matches_from_api
from scoring import recalculate_points

LAST_LIVE_API_CALL = None
LIVE_API_COOLDOWN_SECONDS = 60


def get_due_matches_for_sync():
    conn = get_db()
    rows = conn.execute("""
    SELECT match_api_id, utc_date, status, stage, home_team, away_team
    FROM matches
    WHERE status NOT IN ('FINISHED', 'POSTPONED', 'CANCELLED', 'CANCELED')
    ORDER BY utc_date
    """).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    due = []
    for row in rows:
        if not row["utc_date"]:
            continue
        start = parse_utc_date(row["utc_date"])
        finish = start + (timedelta(minutes=135) if row["stage"] == "GROUP_STAGE" else timedelta(minutes=210))
        if now >= finish:
            due.append(row)
    return due


def smart_sync_after_matches():
    due = get_due_matches_for_sync()
    if not due:
        print("No match due for final-score sync.")
        return
    try:
        count = sync_matches_from_api()
        print(f"API sync completed. {count} matches updated.")
        recalculate_points()
        print("Points recalculated.")
    except Exception as e:
        print("Smart sync failed:", e)


def get_matches_in_live_window():
    conn = get_db()
    rows = conn.execute("""
    SELECT match_api_id, utc_date, status, stage, group_name, home_team, away_team,
           home_crest, away_crest, home_score, away_score
    FROM matches
    WHERE status NOT IN ('FINISHED', 'POSTPONED', 'CANCELLED', 'CANCELED')
    ORDER BY utc_date
    """).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    live = []
    for row in rows:
        if not row["utc_date"]:
            continue
        start = parse_utc_date(row["utc_date"])
        window_start = start - timedelta(minutes=15)
        window_end = start + (timedelta(minutes=150) if row["stage"] == "GROUP_STAGE" else timedelta(minutes=240))
        if window_start <= now <= window_end:
            live.append(row)
    return live


def live_sync_if_needed(force=False):
    global LAST_LIVE_API_CALL
    live_matches = get_matches_in_live_window()
    if not live_matches and not force:
        print("No live match window. No API call.")
        return 0

    now = datetime.now(timezone.utc)
    if not force and LAST_LIVE_API_CALL:
        if (now - LAST_LIVE_API_CALL).total_seconds() < LIVE_API_COOLDOWN_SECONDS:
            print("Live API call skipped. Cooldown active.")
            return 0

    count = sync_matches_from_api()
    LAST_LIVE_API_CALL = now
    recalculate_points()
    print(f"Live sync completed. {count} matches updated.")
    return count
