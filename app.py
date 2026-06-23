from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from database import create_tables_if_needed, get_match_count
from football_api import sync_matches_from_api
from routes import register_routes
from scheduler_jobs import live_sync_if_needed, smart_sync_after_matches
from auto_sync import start_auto_sync

app = Flask(__name__, template_folder="templates", static_folder="static")
register_routes(app)

if __name__ == "__main__":
    create_tables_if_needed()

    if get_match_count() == 0:
        print("No matches found in database. Running first API sync...")
        try:
            sync_matches_from_api()
            print("Initial match sync completed.")
        except Exception as e:
            print("Initial sync failed:", e)

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=live_sync_if_needed, trigger="interval", minutes=1, max_instances=1, coalesce=True)
    scheduler.add_job(func=smart_sync_after_matches, trigger="interval", minutes=5, max_instances=1, coalesce=True)
    scheduler.start()

    print("World Cup Prediction App running.")
    print("Live score sync checks every 1 minute.")
    print("Final-score smart sync checks every 5 minutes.")
    print("API is only called when needed.")

    start_auto_sync()
    app.run(debug=True, use_reloader=False)