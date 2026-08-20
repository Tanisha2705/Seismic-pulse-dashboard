# scheduler.py
# Automatically updates the database every hour.
# Earthquakes happen constantly, so this refreshes far more often than
# a typical daily-update scheduler would.

import schedule
import time
import logging
from datetime import datetime
from fetch_data import fetch_earthquakes, parse_earthquakes
from store_data import connect_to_db, store_earthquakes, create_table
from config import DEFAULT_DAYS_BACK, DEFAULT_MIN_MAGNITUDE, DEFAULT_LIMIT

# ----------------------------------------
# LOGGING SETUP
# ----------------------------------------
logging.basicConfig(
    filename="scheduler.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def update_database():
    """Fetches fresh earthquake data and updates database"""

    print(f"\n{'='*50}")
    print(f"Update started at: {datetime.now()}")
    print(f"{'='*50}")
    logging.info("Hourly update started")

    try:
        # Step 1 - Fetch fresh data
        print("Fetching fresh data from USGS...")
        raw_data = fetch_earthquakes(
            days_back=DEFAULT_DAYS_BACK,
            min_magnitude=DEFAULT_MIN_MAGNITUDE,
            limit=DEFAULT_LIMIT,
        )
        df = parse_earthquakes(raw_data)

        if df is None or df.empty:
            print("No data fetched — skipping update")
            logging.warning("No data fetched from API")
            return

        print(f"Fetched {len(df)} earthquakes successfully")
        logging.info(f"Fetched {len(df)} earthquakes from API")

        # Step 2 - Connect to database
        print("Connecting to database...")
        connection = connect_to_db()

        if connection is None:
            print("Database connection failed")
            logging.error("Database connection failed")
            return

        # Step 3 - Make sure table exists
        create_table(connection)

        # Step 4 - Store new data
        # ON CONFLICT DO NOTHING means only NEW earthquakes get added
        # existing ones are skipped automatically
        print("Storing new earthquakes...")
        store_earthquakes(connection, df)

        # Step 5 - Close connection
        connection.close()

        print(f"Update completed at: {datetime.now()}")
        print(f"{'='*50}\n")
        logging.info("Hourly update completed successfully")

    except Exception as e:
        print(f"Error during update: {e}")
        logging.error(f"Update failed: {e}")

def run_scheduler():
    """Sets up automatic hourly schedule"""

    print("="*50)
    print("Earthquake Tracker Scheduler Started!")
    print("Database updates every hour")
    print("Press Ctrl+C to stop")
    print("="*50)

    logging.info("Scheduler started")

    # Run immediately on start
    print("\nRunning first update now...")
    update_database()

    # Then every hour after that
    schedule.every(1).hours.do(update_database)

    # Keep running forever
    # Checks every 60 seconds if update is due
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run_scheduler()
