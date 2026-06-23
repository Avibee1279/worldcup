from flask import render_template, request, jsonify

from database import get_db, is_postgres
from helpers import is_prediction_open, parse_utc_date, result_type
from football_api import sync_matches_from_api, sync_team_crests_from_api, get_team_squad
from scoring import recalculate_points
from whatsapp_service import prepare_whatsapp_notifications_for_finished_matches, get_prepared_notification_count
from scheduler_jobs import smart_sync_after_matches, live_sync_if_needed
from group_standings import calculate_group_standings
from config import TOKEN, BASE_URL, ADMIN_KEY

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


def kickoff_has_passed(utc_date_text):
    if not utc_date_text:
        return False

    start_time = parse_utc_date(utc_date_text)
    return datetime.now(timezone.utc) >= start_time


def get_effective_live_score(row):
    """
    If kick-off has passed but the football API has not returned a score yet,
    the match should display as 0 - 0 instead of Pending.
    This does not overwrite the database. It is only for display and live points.
    """
    home_score = row["home_score"]
    away_score = row["away_score"]

    if home_score is not None and away_score is not None:
        return home_score, away_score

    if row["status"] not in ("FINISHED", "POSTPONED", "CANCELLED", "CANCELED"):
        if kickoff_has_passed(row["utc_date"]):
            return 0, 0

    return home_score, away_score


def sync_live_scores_before_read():
    """
    Strong live-score behaviour:
    before serving matches, live scores, or leaderboard, ask the backend
    to pull the latest football-data scores. Cooldown is handled in scheduler_jobs.py.
    """
    try:
        live_sync_if_needed(force=True, bypass_cooldown=False)
    except Exception as e:
        print("Live sync before read failed:", e)



ALLOWED_ADMIN_TABLES = {
    "users": "id",
    "matches": "utc_date",
    "predictions": "id",
    "team_squads": "team_id",
    "notification_logs": "id"
}


def check_admin_key():
    """
    Basic protection for admin DB pages.
    If ADMIN_KEY is set in Render, the URL must include ?key=ADMIN_KEY.
    If ADMIN_KEY is not set, pages still work for testing.
    """
    if not ADMIN_KEY:
        return True

    return request.args.get("key") == ADMIN_KEY


def admin_key_suffix():
    if ADMIN_KEY:
        return "?key=" + request.args.get("key", "")

    return ""


def row_to_dict(row):
    if row is None:
        return {}

    return dict(row)


def html_page(title, body):
    return f"""
    <!doctype html>
    <html>
    <head>
        <title>{escape(title)}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #0b2252;
                margin: 0;
                padding: 20px;
                color: #0f172a;
            }}
            .wrap {{
                max-width: 1200px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 18px;
                padding: 18px;
                box-shadow: 0 20px 60px rgba(0,0,0,.22);
            }}
            h1 {{
                margin-top: 0;
            }}
            a {{
                color: #2563eb;
                font-weight: 700;
                text-decoration: none;
            }}
            .top-links {{
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
                margin-bottom: 16px;
            }}
            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
                gap: 12px;
            }}
            .card {{
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 14px;
                background: #f8fafc;
            }}
            .count {{
                font-size: 28px;
                font-weight: 900;
                margin-top: 6px;
            }}
            .table-scroll {{
                overflow-x: auto;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
            }}
            table {{
                border-collapse: collapse;
                min-width: 100%;
                font-size: 13px;
            }}
            th, td {{
                border-bottom: 1px solid #e5e7eb;
                padding: 8px 10px;
                text-align: left;
                vertical-align: top;
                max-width: 320px;
                word-break: break-word;
            }}
            th {{
                background: #eff6ff;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: .04em;
            }}
            .muted {{
                color: #64748b;
                font-size: 13px;
            }}
            .danger {{
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fecaca;
                border-radius: 12px;
                padding: 12px;
                margin: 10px 0;
            }}
            @media (max-width: 700px) {{
                body {{
                    padding: 10px;
                }}
                .wrap {{
                    padding: 14px;
                    border-radius: 14px;
                }}
                table {{
                    font-size: 12px;
                }}
                th, td {{
                    padding: 7px 8px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="wrap">
            {body}
        </div>
    </body>
    </html>
    """


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

        existing_phone = cur.execute("""
        SELECT *
        FROM users
        WHERE phone_number = ?
           OR username = ?
        """, (phone_number, phone_number)).fetchone()

        if existing_phone is not None:
            conn.close()
            return jsonify({
                "error": "This phone number is already registered. Please login instead."
            }), 400

        existing_nickname = cur.execute("""
        SELECT *
        FROM users
        WHERE LOWER(COALESCE(nickname, '')) = LOWER(?)
        """, (nickname,)).fetchone()

        if existing_nickname is not None:
            conn.close()
            return jsonify({
                "error": "This nickname is already used. Please choose another nickname."
            }), 400

        if is_postgres():
            user_row = cur.execute("""
            INSERT INTO users (
                username,
                nickname,
                phone_number,
                pin,
                whatsapp_opt_in
            )
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """, (
                phone_number,
                nickname,
                phone_number,
                pin,
                whatsapp_opt_in
            )).fetchone()

            user_id = user_row["id"]
        else:
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

            user_id = cur.lastrowid

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Registration successful. You are now logged in.",
            "user_id": user_id,
            "nickname": nickname
        })


    @app.route("/api/login", methods=["POST"])
    def login():
        data = request.json

        login_name = data.get("identifier") or data.get("phone_number") or data.get("username") or ""
        login_name = str(login_name).strip()
        login_phone = clean_phone_number(login_name)
        pin = data.get("pin", "").strip()

        if not login_name or not pin:
            return jsonify({
                "error": "Phone number / nickname and PIN are required"
            }), 400

        conn = get_db()
        cur = conn.cursor()

        user = cur.execute("""
        SELECT *
        FROM users
        WHERE phone_number = ?
           OR username = ?
           OR LOWER(COALESCE(nickname, '')) = LOWER(?)
        """, (login_phone, login_phone, login_name)).fetchone()

        if user is None:
            conn.close()
            return jsonify({
                "error": "Account not found. Please sign up first."
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

        sync_live_scores_before_read()

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

            effective_home_score, effective_away_score = get_effective_live_score(match)
            match["home_score"] = effective_home_score
            match["away_score"] = effective_away_score

            if user_id and match["home_pred"] is not None and match["away_pred"] is not None:
                match["points"] = calculate_prediction_points(
                    match["home_pred"],
                    match["away_pred"],
                    match["home_score"],
                    match["away_score"],
                    "LIVE" if kickoff_has_passed(match["utc_date"]) and match["status"] != "FINISHED" else match["status"]
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

        if is_postgres():
            cur.execute("""
            INSERT INTO predictions (
                user_id,
                match_api_id,
                home_pred,
                away_pred
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT (user_id, match_api_id)
            DO UPDATE SET
                home_pred = EXCLUDED.home_pred,
                away_pred = EXCLUDED.away_pred
            """, (
                user_id,
                match_api_id,
                home_pred,
                away_pred
            ))
        else:
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
        sync_live_scores_before_read()

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
                m.status,
                m.utc_date
            FROM predictions p
            JOIN matches m ON p.match_api_id = m.match_api_id
            WHERE p.user_id = ?
            """, (user["id"],)).fetchall()

            total_points = 0

            for prediction in predictions:
                effective_home_score, effective_away_score = get_effective_live_score(prediction)
                effective_status = "LIVE" if kickoff_has_passed(prediction["utc_date"]) and prediction["status"] != "FINISHED" else prediction["status"]

                total_points += calculate_prediction_points(
                    prediction["home_pred"],
                    prediction["away_pred"],
                    effective_home_score,
                    effective_away_score,
                    effective_status
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


    @app.route("/api/live-sync")
    def api_live_sync():
        """
        Public safe sync used by the app.
        It only calls the football API when there is a match in the live window
        and respects the cooldown inside live_sync_if_needed().
        """
        try:
            count = live_sync_if_needed(force=True, bypass_cooldown=False)
            return jsonify({
                "message": "Live sync checked",
                "updated": count
            })
        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500


    @app.route("/api/live-scores")
    def api_live_scores():
        sync_live_scores_before_read()

        conn = get_db()
        cur = conn.cursor()

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
            away_score
        FROM matches
        WHERE status NOT IN ('FINISHED', 'POSTPONED', 'CANCELLED', 'CANCELED')
        ORDER BY utc_date
        """).fetchall()

        conn.close()

        now = datetime.now(timezone.utc)
        live_matches = []

        for row in rows:
            row_dict = dict(row)

            if row_dict["status"] in ("IN_PLAY", "PAUSED", "LIVE"):
                effective_home_score, effective_away_score = get_effective_live_score(row_dict)
                row_dict["home_score"] = effective_home_score
                row_dict["away_score"] = effective_away_score
                live_matches.append(row_dict)
                continue

            # If kick-off has passed but the API has not changed status yet,
            # show it in Live Scores as "waiting for score update".
            if row_dict.get("utc_date"):
                start_time = parse_utc_date(row_dict["utc_date"])
                window_end = start_time + (
                    timedelta(minutes=150)
                    if row_dict.get("stage") == "GROUP_STAGE"
                    else timedelta(minutes=240)
                )

                if start_time <= now <= window_end:
                    effective_home_score, effective_away_score = get_effective_live_score(row_dict)
                    row_dict["home_score"] = effective_home_score
                    row_dict["away_score"] = effective_away_score
                    live_matches.append(row_dict)

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


    @app.route("/admin/db")
    def admin_db_home():
        if not check_admin_key():
            return html_page("Admin denied", """
                <h1>Access denied</h1>
                <div class="danger">Missing or wrong admin key.</div>
            """), 403

        conn = get_db()
        cur = conn.cursor()

        cards = ""

        for table_name in ALLOWED_ADMIN_TABLES:
            row = cur.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
            total = row["total"] if row else 0

            cards += f"""
                <div class="card">
                    <div><a href="/admin/db/{table_name}{admin_key_suffix()}">{table_name}</a></div>
                    <div class="count">{total}</div>
                    <div class="muted">rows</div>
                </div>
            """

        conn.close()

        body = f"""
            <div class="top-links">
                <a href="/">← Back to app</a>
                <a href="/admin/db{admin_key_suffix()}">Refresh DB page</a>
            </div>

            <h1>Database Admin</h1>
            <p class="muted">View table counts and recent records. This page does not edit or delete data.</p>

            <div class="cards">
                {cards}
            </div>
        """

        return html_page("Database Admin", body)


    @app.route("/admin/db/<table_name>")
    def admin_db_table(table_name):
        if not check_admin_key():
            return html_page("Admin denied", """
                <h1>Access denied</h1>
                <div class="danger">Missing or wrong admin key.</div>
            """), 403

        if table_name not in ALLOWED_ADMIN_TABLES:
            return html_page("Table not allowed", f"""
                <h1>Table not allowed</h1>
                <div class="danger">Table {escape(table_name)} is not allowed.</div>
                <p><a href="/admin/db{admin_key_suffix()}">Back to DB admin</a></p>
            """), 404

        order_col = ALLOWED_ADMIN_TABLES[table_name]

        conn = get_db()
        cur = conn.cursor()

        count_row = cur.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
        total = count_row["total"] if count_row else 0

        rows = cur.execute(f"""
        SELECT *
        FROM {table_name}
        ORDER BY {order_col} DESC
        LIMIT 50
        """).fetchall()

        conn.close()

        dict_rows = [row_to_dict(row) for row in rows]

        if not dict_rows:
            table_html = "<p>No records found.</p>"
        else:
            columns = list(dict_rows[0].keys())

            header_html = "".join(f"<th>{escape(col)}</th>" for col in columns)

            rows_html = ""

            for row in dict_rows:
                cells = ""

                for col in columns:
                    value = row.get(col)

                    if value is None:
                        value = ""

                    value_text = str(value)

                    if len(value_text) > 500:
                        value_text = value_text[:500] + "..."

                    cells += f"<td>{escape(value_text)}</td>"

                rows_html += f"<tr>{cells}</tr>"

            table_html = f"""
                <div class="table-scroll">
                    <table>
                        <thead>
                            <tr>{header_html}</tr>
                        </thead>
                        <tbody>
                            {rows_html}
                        </tbody>
                    </table>
                </div>
            """

        body = f"""
            <div class="top-links">
                <a href="/admin/db{admin_key_suffix()}">← Back to DB admin</a>
                <a href="/admin/db/{table_name}{admin_key_suffix()}">Refresh table</a>
                <a href="/">Back to app</a>
            </div>

            <h1>{escape(table_name)}</h1>
            <p class="muted">Showing latest 50 records. Total rows: <b>{total}</b></p>

            {table_html}
        """

        return html_page(f"Table {table_name}", body)


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


    @app.route("/admin/prepare-whatsapp")
    def admin_prepare_whatsapp():
        try:
            # Make sure finished-match points are saved before preparing messages.
            recalculate_points()

            result = prepare_whatsapp_notifications_for_finished_matches()

            return jsonify({
                "message": "WhatsApp messages prepared. They are not sent yet.",
                "created": result["created"],
                "skipped_existing": result["skipped"],
                "prepared_total": get_prepared_notification_count(),
                "sample_messages": result.get("sample_messages", [])[:5]
            })

        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500


    @app.route("/admin/live-sync")
    def admin_live_sync():
        try:
            count = live_sync_if_needed(force=True, bypass_cooldown=True)
            return f"Live sync completed. {count} matches updated."
        except Exception as e:
            return f"Live sync failed: {e}", 500
