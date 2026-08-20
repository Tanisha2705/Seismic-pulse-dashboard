# config.py
# Loads database settings from a local .env file instead of hardcoding
# them in every script. Copy .env.example to .env and fill in your
# real values — .env is gitignored, so your password never gets committed.

import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "earthquake_tracker"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port": os.getenv("DB_PORT", "5432"),
}

# How many days back to fetch, the minimum magnitude to include, and the
# max number of records per fetch — all overridable via .env.
DEFAULT_DAYS_BACK = int(os.getenv("EARTHQUAKE_DAYS_BACK", "30"))
DEFAULT_MIN_MAGNITUDE = float(os.getenv("EARTHQUAKE_MIN_MAGNITUDE", "2.5"))
DEFAULT_LIMIT = int(os.getenv("EARTHQUAKE_LIMIT", "1000"))
