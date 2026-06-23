import sqlite3
from database import DB_NAME


def get_user_total_points_and_rank(user_id):
    """
    Returns (total_points, rank) using saved points.
    This is enough for finished-match WhatsApp notification preparation.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            u.id,
            COALESCE(SUM(p.points), 0) AS total_points
        FROM users u
        LEFT JOIN predictions p ON p.user_id = u.id
        GROUP BY u.id
        ORDER BY total_points DESC, u.id ASC
    """)
    rows = cur.fetchall()
    conn.close()

    rank = 0
    previous_points = None
    position = 0

    for row in rows:
        position += 1
        if previous_points is None or row["total_points"] != previous_points:
            rank = position
            previous_points = row["total_points"]

        if row["id"] == user_id:
            return row["total_points"], rank

    return 0, 0


def get_prepared_notification_count():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT COUNT(*)
            FROM notification_logs
            WHERE status = 'PREPARED'
        """)
        count = cur.fetchone()[0]
    except sqlite3.OperationalError:
        count = 0

    conn.close()
    return count


def prepare_whatsapp_notifications_for_finished_matches():
    """
    Prepares WhatsApp messages for finished matches only.
    It does NOT send WhatsApp messages.
    It saves prepared messages into notification_logs.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.user_id,
            p.match_api_id,
            p.home_pred,
            p.away_pred,
            p.points,
            u.nickname,
            u.phone_number,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score
        FROM predictions p
        JOIN users u ON u.id = p.user_id
        JOIN matches m ON m.api_id = p.match_api_id
        WHERE m.status = 'FINISHED'
          AND m.home_score IS NOT NULL
          AND m.away_score IS NOT NULL
          AND u.whatsapp_opt_in = 1
          AND u.phone_number IS NOT NULL
          AND TRIM(u.phone_number) <> ''
    """)

    rows = cur.fetchall()

    created = 0
    skipped = 0
    sample_messages = []

    for row in rows:
        notification_type = "MATCH_RESULT"

        cur.execute("""
            SELECT id
            FROM notification_logs
            WHERE user_id = ?
              AND match_api_id = ?
              AND notification_type = ?
        """, (row["user_id"], row["match_api_id"], notification_type))

        if cur.fetchone():
            skipped += 1
            continue

        total_points, rank = get_user_total_points_and_rank(row["user_id"])

        message = (
            f"🏆 World Cup Prediction\n\n"
            f"Hi {row['nickname']},\n\n"
            f"{row['home_team']} {row['home_score']} - {row['away_score']} {row['away_team']}\n\n"
            f"Your prediction: {row['home_pred']} - {row['away_pred']}\n"
            f"You earned: {row['points']} point(s)\n\n"
            f"Total points: {total_points}\n"
            f"Current rank: {rank}\n\n"
            f"Keep predicting before kick-off!"
        )

        cur.execute("""
            INSERT INTO notification_logs
            (
                user_id,
                match_api_id,
                notification_type,
                phone_number,
                message,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'PREPARED')
        """, (
            row["user_id"],
            row["match_api_id"],
            notification_type,
            row["phone_number"],
            message
        ))

        created += 1

        if len(sample_messages) < 5:
            sample_messages.append({
                "phone_number": row["phone_number"],
                "message": message
            })

    conn.commit()
    conn.close()

    return {
        "created": created,
        "skipped": skipped,
        "prepared_total": get_prepared_notification_count(),
        "sample_messages": sample_messages
    }
