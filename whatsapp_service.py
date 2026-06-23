from database import get_db


NOTIFICATION_TYPE_MATCH_RESULT = "MATCH_RESULT"


def get_leaderboard_positions(conn):
    """
    Uses saved points from predictions.
    This is for finished match notification messages.
    """
    rows = conn.execute("""
    SELECT
        u.id AS user_id,
        COALESCE(NULLIF(u.nickname, ''), u.username) AS nickname,
        COALESCE(SUM(p.points), 0) AS total_points,
        COUNT(p.id) AS predictions_made
    FROM users u
    LEFT JOIN predictions p ON u.id = p.user_id
    GROUP BY u.id
    ORDER BY total_points DESC, predictions_made DESC, nickname ASC
    """).fetchall()

    positions = {}

    for index, row in enumerate(rows, start=1):
        positions[row["user_id"]] = {
            "rank": index,
            "total_points": row["total_points"],
            "predictions_made": row["predictions_made"]
        }

    return positions


def build_match_result_message(row, rank_info):
    nickname = row["nickname"] or "Player"

    points_text = "point"
    if row["points"] != 1:
        points_text = "points"

    return f"""🏆 World Cup Prediction

Hi {nickname},

{row["home_team"]} {row["home_score"]} - {row["away_score"]} {row["away_team"]}

Your prediction: {row["home_pred"]} - {row["away_pred"]}
You earned: {row["points"]} {points_text}

Total points: {rank_info["total_points"]}
Current rank: {rank_info["rank"]}

Keep predicting before kick-off!"""


def prepare_whatsapp_notifications_for_finished_matches():
    """
    Prepares WhatsApp messages for finished matches only.

    This does NOT send WhatsApp yet.
    It only creates rows in notification_logs with status PREPARED.

    Later, when the official WhatsApp Cloud API is connected,
    another function will send messages from this table.
    """
    conn = get_db()
    cur = conn.cursor()

    leaderboard_positions = get_leaderboard_positions(conn)

    rows = cur.execute("""
    SELECT
        u.id AS user_id,
        COALESCE(NULLIF(u.nickname, ''), u.username) AS nickname,
        u.phone_number,
        u.whatsapp_opt_in,
        p.match_api_id,
        p.home_pred,
        p.away_pred,
        p.points,
        m.home_team,
        m.away_team,
        m.home_score,
        m.away_score,
        m.status
    FROM predictions p
    JOIN users u ON p.user_id = u.id
    JOIN matches m ON p.match_api_id = m.match_api_id
    WHERE m.status = 'FINISHED'
      AND m.home_score IS NOT NULL
      AND m.away_score IS NOT NULL
      AND u.whatsapp_opt_in = 1
      AND u.phone_number IS NOT NULL
      AND u.phone_number <> ''
    ORDER BY m.utc_date, u.nickname
    """).fetchall()

    created = 0
    skipped = 0
    prepared_messages = []

    for row in rows:
        existing = cur.execute("""
        SELECT id
        FROM notification_logs
        WHERE user_id = ?
          AND match_api_id = ?
          AND notification_type = ?
        """, (
            row["user_id"],
            row["match_api_id"],
            NOTIFICATION_TYPE_MATCH_RESULT
        )).fetchone()

        if existing:
            skipped += 1
            continue

        rank_info = leaderboard_positions.get(row["user_id"], {
            "rank": 0,
            "total_points": 0,
            "predictions_made": 0
        })

        message = build_match_result_message(row, rank_info)

        cur.execute("""
        INSERT INTO notification_logs (
            user_id,
            match_api_id,
            notification_type,
            phone_number,
            message,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row["user_id"],
            row["match_api_id"],
            NOTIFICATION_TYPE_MATCH_RESULT,
            row["phone_number"],
            message,
            "PREPARED"
        ))

        created += 1

        prepared_messages.append({
            "nickname": row["nickname"],
            "phone_number": row["phone_number"],
            "match": f'{row["home_team"]} vs {row["away_team"]}',
            "points": row["points"],
            "rank": rank_info["rank"],
            "message": message
        })

    conn.commit()
    conn.close()

    return {
        "created": created,
        "skipped": skipped,
        "messages": prepared_messages
    }


def get_prepared_notification_count():
    conn = get_db()
    row = conn.execute("""
    SELECT COUNT(*) AS total
    FROM notification_logs
    WHERE status = 'PREPARED'
    """).fetchone()
    conn.close()

    return row["total"] if row else 0
