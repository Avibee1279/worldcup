import threading
import time

from football_api import sync_matches_from_api
from scoring import recalculate_points


def auto_sync_loop():
    while True:
        try:
            print("AUTO SYNC: Checking latest scores...")

            updated = sync_matches_from_api()
            recalculate_points()

            print(f"AUTO SYNC: Done. {updated} matches updated. Points recalculated.")

        except Exception as e:
            print("AUTO SYNC ERROR:", e)

        # Wait 60 seconds before checking again
        time.sleep(60)


def start_auto_sync():
    thread = threading.Thread(target=auto_sync_loop)
    thread.daemon = True
    thread.start()