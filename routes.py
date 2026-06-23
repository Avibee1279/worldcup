from flask import render_template, request, jsonify

from database import get_db
from helpers import is_prediction_open, parse_utc_date, result_type
from football_api import sync_matches_from_api, sync_team_crests_from_api, get_team_squad
from scoring import recalculate_points
from scheduler_jobs import smart_sync_after_matches, live_sync_if_needed
from group_standings import calculate_group_standings

from datetime import datetime, timedelta, timezone


POINT_STATUSES = (
    "FINISHED",
    "IN_PLAY",
    "LIVE",
    "PAUSED"
)


def clean_phone_number(phone_number):
    if not phone_number:
        return ""

    phone_number = str(phone_number).strip()
    phone_number = phone_number.replace(" ", "")
    phone_number = phone_number.replace("-", "")
    phone_number = phone_number.replace("(", "")
    phone_number = phone_number.replace(")", "")

    return phone_number


def calculate_prediction_points(home_pred, away_pred, home_score, away_score, status):
    """
    Dynamic points:
    - Exact current/final score = 3 points
    - Correct current/final result = 1 point
    - Otherwise = 0 points

    For matches not started, return saved/pending points as 0.
    """
    if status not in POINT_STATUSES:
        return 0

    if home_pred is None or away_pred is None:
        return 0

    if home_score is None or away_score is None:
        return 0

    if home_pred == home_score and away_pred == away_score:
        return 3

    if result_type(home_pred, away_pred) == result_type(home_score, away_score):
        return 1

    return 0


def register_routes(app):

    @app.route("/")
    def home():
        return render_template("index.html")


    @app.route("/api/register", methods=["POST"])
    def register_user():
        data = request.json

        nickname = data.get("nickname", "").strip()
        phone_number = clean_phone_number(data.get("phone_number"))
        pin = data.get("pin", "").strip()
        whatsapp_opt_in = 1 if data.get("whatsapp_opt_in") else 0

        if not nickname or not phone_number or not pin:
            return jsonify({
                "error": "Nickname, phone number and PIN are required"
            }), 400

        if len(phone_number) < 7:
            return jsonify({
                "error": "Please enter a valid phone number"
            }), 400

        conn = get_db()
        cur = conn.cursor()

        existing_user = cur.execute("""
        SELECT *
        FROM users
        WHERE phone_number = ?
           OR username = ?
        """, (phone_number, phone_number)).fetchone()

        if existing_user is not None:
            conn.close()
            return jsonify({
                "error": "This phone number is already registered. Please login instead."
            }), 400

        cur.execute("""
        INSERT INTO users (
            username,
            nickname,
            phone_number,
            pin,
            whatsapp_opt_in
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            phone_number,
            nickname,
            phone_number,
            pin,
            whatsapp_opt_in
        ))

        conn.commit()
        user_id = cur.lastrowid
        conn.close()

        return jsonify({
            "message": "Registration successful",
            "user_id": user_id,
            "nickname": nickname
        })


    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.json

        phone_number = clean_phone_number(data.get("phone_number"))
        pin = data.get("pin", "").strip()

        if not phone_number or not pin:
            return jsonify({
                "error": "Phone number and PIN are required"
            }), 400

        conn = get_db()
        cur = conn.cursor()

        user = cur.execute("""
        SELECT *
        FROM users
        WHERE phone_number = ?
           OR username = ?
        """, (phone_number, phone_number)).fetchone()

        if user is None:
            conn.close()
            return jsonify({
                "error": "Phone number not found. Please sign up first."
            }), 404

        if user["pin"] != pin:
            conn.close()
            return jsonify({
                "error": "Wrong PIN"
            }), 401

        nickname = user["nickname"] if user["nickname"] else user["username"]

        conn.close()

        return jsonify({
            "message": "Login successful",
            "user_id": user["id"],
            "nickname": nickname
        })


    @app.route("/api/matches")
    def get_matches():
        user_id = request.args.get("user_id")

        conn = get_db()
        cur = conn.cursor()

        if user_id:
            rows = cur.execute("""
            SELECT 
                m.match_api_id,
                m.utc_date,
                m.status,
                m.stage,
                m.group_name,
                m.home_team_id,
                m.away_team_id,
                m.home_team,
                m.away_team,
                m.home_crest,
                m.away_crest,
                m.home_score,
                m.away_score,
                p.home_pred,
                p.away_pred,
                p.points
            FROM matches m
            LEFT JOIN predictions p
                ON m.match_api_id = p.match_api_id
                AND p.user_id = ?
            ORDER BY m.utc_date
            """, (user_id,)).fetchall()
        else:
            rows = cur.execute("""
            SELECT 
                match_api_id,
                utc_date,
                status,
                stage,
                group_name,
                home_team_id,
                away_team_id,
                home_team,
                away_team,
                home_crest,
                away_crest,
                home_score,
                away_score,
                NULL AS home_pred,
                NULL AS away_pred,
                NULL AS points
            FROM matches
            ORDER BY utc_date
            """).fetchall()

        conn.close()

        matches = []

        for row in rows:
            match = dict(row)

            if user_id and match["home_pred"] is not None and match["away_pred"] is not None:
                match["points"] = calculate_prediction_points(
                    match["home_pred"],
                    match["away_pred"],
                    match["home_score"],
                    match["away_score"],
                    match["status"]
                )

            matches.append(match)

        return jsonify(matches)


    @app.route("/api/predict", methods=["POST"])
    def save_prediction():
        data = request.json

        user_id = data.get("user_id")
        match_api_id = data.get("match_api_id")
        home_pred = data.get("home_pred")
        away_pred = data.get("away_pred")

        if user_id is None or match_api_id is None or home_pred is None or away_pred is None:
            return jsonify({
                "error": "Missing prediction details"
            }), 400

        conn = get_db()
        cur = conn.cursor()

        match = cur.execute(
            "SELECT * FROM matches WHERE match_api_id = ?",
            (match_api_id,)
        ).fetchone()

        if match is None:
            conn.close()
            return jsonify({
                "error": "Match not found"
            }), 404

        if not is_prediction_open(match):
            conn.close()
            return jsonify({
                "error": "Prediction locked. Match already started or finished."
            }), 400

        cur.execute("""
        INSERT OR REPLACE INTO predictions (
            user_id,
            match_api_id,
            home_pred,
            away_pred
        )
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            match_api_id,
            home_pred,
            away_pred
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Prediction saved"
        })


    @app.route("/api/leaderboard")
    def leaderboard():
        conn = get_db()
        cur = conn.cursor()

        users = cur.execute("""
        SELECT
            id,
            COALESCE(NULLIF(nickname, ''), username) AS nickname
        FROM users
        """).fetchall()

        leaderboard_rows = []

        for user in users:
            predictions = cur.execute("""
            SELECT
                p.home_pred,
                p.away_pred,
                m.home_score,
                m.away_score,
                m.status
            FROM predictions p
            JOIN matches m ON p.match_api_id = m.match_api_id
            WHERE p.user_id = ?
            """, (user["id"],)).fetchall()

            total_points = 0

            for prediction in predictions:
                total_points += calculate_prediction_points(
                    prediction["home_pred"],
                    prediction["away_pred"],
                    prediction["home_score"],
                    prediction["away_score"],
                    prediction["status"]
                )

            leaderboard_rows.append({
                "nickname": user["nickname"],
                "total_points": total_points,
                "predictions_made": len(predictions)
            })

        conn.close()

        leaderboard_rows.sort(
            key=lambda row: (
                -row["total_points"],
                -row["predictions_made"],
                row["nickname"].lower()
            )
        )

        return jsonify(leaderboard_rows)


    @app.route("/api/live-scores")
    def api_live_scores():
        conn = get_db()
        cur = conn.cursor()

        rows = cur.execute("""
        SELECT 
            match_api_id,
            utc_date,
            status,
            stage,
            group_name,
            home_team,
            away_team,
            home_crest,
            away_crest,
            home_score,
            away_score
        FROM matches
        ORDER BY utc_date
        """).fetchall()

        conn.close()

        now = datetime.now(timezone.utc)
        live_matches = []

        for row in rows:
            if not row["utc_date"]:
                continue

            start_time = parse_utc_date(row["utc_date"])
            window_start = start_time - timedelta(minutes=15)

            if row["stage"] == "GROUP_STAGE":
                window_end = start_time + timedelta(minutes=150)
            else:
                window_end = start_time + timedelta(minutes=240)

            if window_start <= now <= window_end or row["status"] in ("IN_PLAY", "PAUSED", "LIVE"):
                live_matches.append(dict(row))

        return jsonify(live_matches)


    @app.route("/api/group-standings")
    def group_standings():
        return jsonify(calculate_group_standings())


    @app.route("/api/team-squad/<int:team_id>")
    def api_team_squad(team_id):
        try:
            force_refresh = request.args.get("refresh") == "1"
            squad = get_team_squad(team_id, force_refresh=force_refresh)
            return jsonify(squad)
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route("/admin/sync")
    def admin_sync():
        try:
            count = sync_matches_from_api()
            return f"Sync completed successfully. {count} matches updated."
        except Exception as e:
            return f"Sync failed: {e}", 500


    @app.route("/admin/sync-crests")
    def admin_sync_crests():
        try:
            updated = sync_team_crests_from_api()
            return f"Team crests synced. {updated} records updated."
        except Exception as e:
            return f"Crest sync failed: {e}", 500


    @app.route("/admin/calculate")
    def calculate_points():
        recalculate_points()
        return "Points calculated successfully."


    @app.route("/admin/smart-check")
    def admin_smart_check():
        smart_sync_after_matches()
        return "Smart check completed. Check the Python console."


    @app.route("/admin/live-sync")
    def admin_live_sync():
        try:
            count = live_sync_if_needed(force=True)
            return f"Live sync completed. {count} matches updated."
        except Exception as e:
            return f"Live sync failed: {e}", 500
