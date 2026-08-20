# store_data.py
# Connects to PostgreSQL and stores earthquake data

import psycopg2
from fetch_data import fetch_earthquakes, parse_earthquakes
from config import DB_CONFIG, DEFAULT_DAYS_BACK, DEFAULT_MIN_MAGNITUDE, DEFAULT_LIMIT

def connect_to_db():
    """Opens connection to PostgreSQL database"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        print("Connected to PostgreSQL successfully!")
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def create_table(connection):
    """Creates earthquakes table if it doesn't exist"""

    create_table_query = """
        CREATE TABLE IF NOT EXISTS earthquakes (
            id SERIAL PRIMARY KEY,
            earthquake_id VARCHAR(40) UNIQUE NOT NULL,
            place TEXT,
            magnitude NUMERIC(4, 2),
            mag_type VARCHAR(10),
            depth_km NUMERIC(8, 2),
            longitude NUMERIC(9, 6),
            latitude NUMERIC(9, 6),
            event_time TIMESTAMPTZ,
            tsunami BOOLEAN DEFAULT false,
            alert VARCHAR(20),
            significance INTEGER,
            status VARCHAR(20),
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """

    try:
        cursor = connection.cursor()
        cursor.execute(create_table_query)
        connection.commit()
        print("Table created successfully!")
    except Exception as e:
        print(f"Error creating table: {e}")

def store_earthquakes(connection, df):
    """Stores each earthquake from DataFrame into PostgreSQL"""

    insert_query = """
        INSERT INTO earthquakes
        (earthquake_id, place, magnitude, mag_type, depth_km, longitude,
         latitude, event_time, tsunami, alert, significance, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (earthquake_id) DO NOTHING;
    """

    try:
        cursor = connection.cursor()
        success_count = 0

        for _, row in df.iterrows():
            cursor.execute(insert_query, (
                row["earthquake_id"],
                row["place"],
                row["magnitude"],
                row["mag_type"],
                row["depth_km"],
                row["longitude"],
                row["latitude"],
                row["event_time"],
                row["tsunami"],
                row["alert"],
                row["significance"],
                row["status"],
            ))
            success_count += 1

        connection.commit()
        print(f"Successfully processed {success_count} earthquakes (new ones inserted, duplicates skipped)")

    except Exception as e:
        print(f"Error storing data: {e}")
        connection.rollback()

def verify_data(connection):
    """Checks how many records are in database"""
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM earthquakes;")
        count = cursor.fetchone()[0]
        print(f"Total earthquakes in database: {count}")

        cursor.execute("""
            SELECT place, magnitude, event_time
            FROM earthquakes
            ORDER BY magnitude DESC
            LIMIT 3;
        """)
        rows = cursor.fetchall()
        print("\nStrongest recent earthquakes:")
        for row in rows:
            print(row)

    except Exception as e:
        print(f"Error verifying data: {e}")

if __name__ == "__main__":
    print("--- Step 1: Fetching Data ---")
    raw_data = fetch_earthquakes(
        days_back=DEFAULT_DAYS_BACK,
        min_magnitude=DEFAULT_MIN_MAGNITUDE,
        limit=DEFAULT_LIMIT,
    )
    df = parse_earthquakes(raw_data)

    print("\n--- Step 2: Connecting to Database ---")
    connection = connect_to_db()

    if connection:
        print("\n--- Step 3: Creating Table ---")
        create_table(connection)

        print("\n--- Step 4: Storing Data ---")
        store_earthquakes(connection, df)

        print("\n--- Step 5: Verifying Data ---")
        verify_data(connection)

        connection.close()
        print("\nDatabase connection closed!")
