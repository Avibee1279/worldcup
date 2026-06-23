import json
import requests
from datetime import datetime, timedelta, timezone
from config import TOKEN, BASE_URL
from database import get_db


def get_headers():
    if not TOKEN:
        raise ValueError("FOOTBALL_DATA_TOKEN is missing in .env file.")
    return {"X-Auth-Token": TOKEN}


def sync_matches_from_api():
    url = BASE_URL + "/competitions/WC/matches"
    response = requests.get(url, headers=get_headers(), timeout=20)
    if response.status_code != 200:
        raise Exception(response.text)

    data = response.json()
    matches = data.get("matches", [])

    conn = get_db()
    cur = conn.cursor()

    for match in matches:
        home = match.get("homeTeam", {})
        away = match.get("awayTeam", {})
        score = match.get("score", {})
        full_time = score.get("fullTime", {})

        values = (
            match.get("utcDate"),
            match.get("status"),
            match.get("stage"),
            match.get("group"),
            home.get("id"),
            away.get("id"),
            home.get("name"),
            away.get("name"),
            home.get("crest"),
            away.get("crest"),
            full_time.get("home"),
            full_time.get("away"),
            match.get("id")
        )

        cur.execute("""
        UPDATE matches
        SET utc_date=?, status=?, stage=?, group_name=?, home_team_id=?, away_team_id=?,
            home_team=?, away_team=?, home_crest=?, away_crest=?, home_score=?, away_score=?
        WHERE match_api_id=?
        """, values)

        if cur.rowcount == 0:
            cur.execute("""
            INSERT INTO matches (
                utc_date, status, stage, group_name, home_team_id, away_team_id,
                home_team, away_team, home_crest, away_crest, home_score, away_score, match_api_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)

    conn.commit()
    conn.close()
    return len(matches)


def sync_team_crests_from_api():
    url = BASE_URL + "/competitions/WC/teams"
    response = requests.get(url, headers=get_headers(), timeout=20)
    if response.status_code != 200:
        raise Exception(response.text)

    teams = response.json().get("teams", [])
    conn = get_db()
    cur = conn.cursor()
    updated = 0

    for team in teams:
        team_id = team.get("id")
        crest = team.get("crest")
        if not crest:
            continue
        cur.execute("UPDATE matches SET home_crest=? WHERE home_team_id=?", (crest, team_id))
        updated += cur.rowcount
        cur.execute("UPDATE matches SET away_crest=? WHERE away_team_id=?", (crest, team_id))
        updated += cur.rowcount

    conn.commit()
    conn.close()
    return updated


def get_team_squad_from_api(team_id):
    url = BASE_URL + f"/teams/{team_id}"
    response = requests.get(url, headers=get_headers(), timeout=20)
    if response.status_code != 200:
        raise Exception(response.text)

    data = response.json()
    squad_payload = {
        "team_id": data.get("id"),
        "name": data.get("name"),
        "short_name": data.get("shortName"),
        "tla": data.get("tla"),
        "crest": data.get("crest"),
        "squad": data.get("squad", [])
    }

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO team_squads (team_id, team_name, crest, squad_json, updated_at)
    VALUES (?, ?, ?, ?, ?)
    """, (
        team_id,
        squad_payload.get("name"),
        squad_payload.get("crest"),
        json.dumps(squad_payload, ensure_ascii=False),
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()
    return squad_payload


def get_team_squad(team_id, force_refresh=False):
    conn = get_db()
    cur = conn.cursor()
    cached = cur.execute("SELECT squad_json, updated_at FROM team_squads WHERE team_id=?", (team_id,)).fetchone()
    conn.close()

    if cached and not force_refresh:
        try:
            updated_at = datetime.fromisoformat(cached["updated_at"])
            if datetime.now(timezone.utc) - updated_at < timedelta(hours=24):
                return json.loads(cached["squad_json"])
        except Exception:
            pass

    return get_team_squad_from_api(team_id)
