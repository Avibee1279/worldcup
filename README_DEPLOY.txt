# World Cup Prediction App - Latest Render Ready Version

This package contains the latest combined version:

- Phone number + PIN login
- Nickname shown on leaderboard only
- Improved account/login screen
- Dynamic live points
- Dynamic group standings
- Prediction status display
- Input reset fix while typing predictions
- WhatsApp message preparation only, not sending
- Render fixed app.py startup so tables are created under Gunicorn

## Do not upload these to GitHub

- .env
- worldcup_game.db
- venv/
- __pycache__/

## Render settings

Build command:

pip install -r requirements.txt

Start command:

gunicorn -w 1 app:app

Environment variable:

FOOTBALL_DATA_TOKEN = your football-data token

## After deploying

Open your site, create/login a user, then test saving a prediction.

Admin routes still need protection before sharing widely.


LATEST UPDATE:
- Login screen now appears before Create account.
- Users can login with phone number OR nickname.
- After login, the login/signup forms vanish and a current-player card is shown.
- Render start command should be: gunicorn -w 1 app:app
- Render environment variable required: FOOTBALL_DATA_TOKEN

UPDATE: Login/signup is now a separate entry screen. Main app appears only after login.
