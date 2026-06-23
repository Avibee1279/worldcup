from database import get_db
from helpers import result_type


def recalculate_points():
    conn = get_db()
    cur = conn.cursor()

    predictions = cur.execute("""
    SELECT p.id, p.home_pred, p.away_pred, m.home_score, m.away_score
    FROM predictions p
    JOIN matches m ON p.match_api_id = m.match_api_id
    WHERE m.status='FINISHED' AND m.home_score IS NOT NULL AND m.away_score IS NOT NULL
    """).fetchall()

    for p in predictions:
        points = 0
        if p["home_pred"] == p["home_score"] and p["away_pred"] == p["away_score"]:
            points = 3
        elif result_type(p["home_pred"], p["away_pred"]) == result_type(p["home_score"], p["away_score"]):
            points = 1

        cur.execute("UPDATE predictions SET points=? WHERE id=?", (points, p["id"]))

    conn.commit()
    conn.close()
