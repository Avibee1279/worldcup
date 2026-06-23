from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

from database import create_tables_if_needed, get_match_count
from football_api import sync_matches_from_api
from routes import register_routes
from scheduler_jobs import live_sync_if_needed, smart_sync_after_matches
from scoring import recalculate_points


app = Flask(__name__, template_folder="templates", static_folder="static")
register_routes(app)


_scheduler = None


def startup():
    """
    This runs when Gunicorn imports app:app on Render.
    Do not put important setup only inside if __name__ == "__main__",
    because Render/Gunicorn will not execute that block.
    """
    global _scheduler

    create_tables_if_needed()

    try:
        if get_match_count() == 0:
            print("No matches found in database. Running first API sync...")
            sync_matches_from_api()
            recalculate_points()
            print("Initial match sync completed.")
    except Exception as e:
        print("Initial sync failed:", e)

    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            func=live_sync_if_needed,
            trigger="interval",
            minutes=1,
            id="live_sync_if_needed",
            replace_existing=True
        )
        _scheduler.add_job(
            func=smart_sync_after_matches,
            trigger="interval",
            minutes=5,
            id="smart_sync_after_matches",
            replace_existing=True
        )
        _scheduler.start()
        print("Scheduler started.")


startup()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )
