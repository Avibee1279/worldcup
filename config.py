import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
BASE_URL = "https://api.football-data.org/v4"
DB_NAME = str(BASE_DIR / "worldcup_game.db")
