from database import get_db


def calculate_group_standings():
    conn = get_db()
    cur = conn.cursor()

    rows = cur.execute("""
    SELECT 
        group_name,
        home_team_id,
        away_team_id,
        home_team,
        away_team,
        home_score,
        away_score,
        status
    FROM matches
    WHERE group_name IS NOT NULL
    ORDER BY group_name, utc_date
    """).fetchall()

    conn.close()

    groups = {}

    def create_team(group_name, team_id, team_name):
        if group_name not in groups:
            groups[group_name] = {}

        key = str(team_id) if team_id else team_name

        if key not in groups[group_name]:
            groups[group_name][key] = {
                "team_id": team_id,
                "team": team_name,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": 0,
                "points": 0
            }

        return groups[group_name][key]

    # Count both finished matches and live matches.
    # This makes the group table dynamic while a match is being played.
    statuses_to_count = (
        "FINISHED",
        "IN_PLAY",
        "LIVE",
        "PAUSED"
    )

    for row in rows:
        group_name = row["group_name"]

        home = create_team(group_name, row["home_team_id"], row["home_team"])
        away = create_team(group_name, row["away_team_id"], row["away_team"])

        # Do not count matches that have not started yet.
        if row["status"] not in statuses_to_count:
            continue

        # Do not count if score is not available yet.
        if row["home_score"] is None or row["away_score"] is None:
            continue

        home_score = row["home_score"]
        away_score = row["away_score"]

        home["played"] += 1
        away["played"] += 1

        home["goals_for"] += home_score
        home["goals_against"] += away_score

        away["goals_for"] += away_score
        away["goals_against"] += home_score

        if home_score > away_score:
            home["won"] += 1
            home["points"] += 3
            away["lost"] += 1

        elif home_score < away_score:
            away["won"] += 1
            away["points"] += 3
            home["lost"] += 1

        else:
            home["drawn"] += 1
            away["drawn"] += 1
            home["points"] += 1
            away["points"] += 1

    result = {}

    for group_name, teams in groups.items():
        table = []

        for team in teams.values():
            team["goal_difference"] = team["goals_for"] - team["goals_against"]
            table.append(team)

        # Sort by points, goal difference, goals for, then team name.
        table.sort(
            key=lambda x: (
                -x["points"],
                -x["goal_difference"],
                -x["goals_for"],
                x["team"]
            )
        )

        for index, team in enumerate(table, start=1):
            team["rank"] = index

        result[group_name] = table

    return result
