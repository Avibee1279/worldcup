import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
BASE_URL = "https://api.football-data.org/v4"

# Local fallback only. Used on your PC if DATABASE_URL is not set.
DB_NAME = str(BASE_DIR / "worldcup_game.db")

# Render Postgres / Neon Postgres both use DATABASE_URL.
# In Render, paste the Render Postgres INTERNAL DATABASE URL here.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Optional: protect admin DB pages with /admin/db?key=your_key
ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()
