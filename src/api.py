# api.py
# Flask server that serves our earthquake data
# Think of this as a waiter between database and dashboard

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import pandas as pd
from config import DB_CONFIG

# ----------------------------------------
# FLASK APP SETUP
# ----------------------------------------
app = Flask(__name__)
CORS(app)

# ----------------------------------------
# HELPER FUNCTION
# ----------------------------------------
def get_db_connection():
    """Opens connection to PostgreSQL"""
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Database error: {e}")
        return None

# ----------------------------------------
# API ROUTES
# ----------------------------------------

# Route 1 — Get earthquakes, with optional filters
# http://localhost:5000/api/earthquakes?min_magnitude=5&alert=red&tsunami_only=true&search=japan
@app.route("/api/earthquakes", methods=["GET"])
def get_earthquakes():
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        min_magnitude = request.args.get("min_magnitude", type=float)
        alert = request.args.get("alert")
        tsunami_only = request.args.get("tsunami_only", "false").lower() == "true"
        search = request.args.get("search")

        conditions = []
        params = []

        if min_magnitude is not None:
            conditions.append("magnitude >= %s")
            params.append(min_magnitude)
        if alert and alert != "all":
            if alert == "none":
                conditions.append("alert IS NULL")
            else:
                conditions.append("alert = %s")
                params.append(alert)
        if tsunami_only:
            conditions.append("tsunami = true")
        if search:
            conditions.append("place ILIKE %s")
            params.append(f"%{search}%")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM earthquakes
            {where_clause}
            ORDER BY event_time DESC
            LIMIT 500;
        """

        df = pd.read_sql(query, connection, params=params)
        connection.close()

        earthquakes = df.to_dict(orient="records")

        return jsonify({
            "success": True,
            "total": len(earthquakes),
            "data": earthquakes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route 2 — Get summary statistics
# http://localhost:5000/api/stats
@app.route("/api/stats", methods=["GET"])
def get_stats():
    connection = get_db_connection()
    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor()

        # Total earthquakes
        cursor.execute("SELECT COUNT(*) FROM earthquakes;")
        total = cursor.fetchone()[0]

        # Tsunami-flagged count
        cursor.execute("SELECT COUNT(*) FROM earthquakes WHERE tsunami = true;")
        tsunami_count = cursor.fetchone()[0]

        # Strongest earthquake (and where it happened)
        cursor.execute("""
            SELECT place, magnitude FROM earthquakes
            ORDER BY magnitude DESC NULLS LAST LIMIT 1;
        """)
        strongest_row = cursor.fetchone()
        strongest = strongest_row[1] if strongest_row else None
        strongest_place = strongest_row[0] if strongest_row else None

        # Top 5 strongest individual events, for the leaderboard chart
        cursor.execute("""
            SELECT place, magnitude FROM earthquakes
            ORDER BY magnitude DESC NULLS LAST LIMIT 5;
        """)
        top_events = [
            {"place": row[0], "magnitude": float(row[1])}
            for row in cursor.fetchall()
        ]

        # Average magnitude
        cursor.execute("SELECT ROUND(AVG(magnitude), 2) FROM earthquakes;")
        avg_magnitude = cursor.fetchone()[0]

        # Earthquakes by magnitude range
        cursor.execute("""
            SELECT
                CASE
                    WHEN magnitude < 3 THEN 'Minor (<3)'
                    WHEN magnitude < 4 THEN 'Light (3-4)'
                    WHEN magnitude < 5 THEN 'Moderate (4-5)'
                    WHEN magnitude < 6 THEN 'Strong (5-6)'
                    WHEN magnitude < 7 THEN 'Major (6-7)'
                    ELSE 'Great (7+)'
                END AS magnitude_range,
                COUNT(*) as count
            FROM earthquakes
            GROUP BY magnitude_range
            ORDER BY MIN(magnitude);
        """)
        by_magnitude = [
            {"range": row[0], "count": row[1]}
            for row in cursor.fetchall()
        ]

        # Earthquakes by alert level
        cursor.execute("""
            SELECT COALESCE(alert, 'none') as alert_level, COUNT(*) as count
            FROM earthquakes
            GROUP BY alert_level
            ORDER BY count DESC;
        """)
        by_alert = [
            {"alert": row[0], "count": row[1]}
            for row in cursor.fetchall()
        ]

        # Earthquakes per day (last 30 days of data)
        cursor.execute("""
            SELECT DATE(event_time) as day, COUNT(*) as count
            FROM earthquakes
            GROUP BY day
            ORDER BY day ASC;
        """)
        by_day = [
            {"day": row[0].isoformat(), "count": row[1]}
            for row in cursor.fetchall()
        ]

        # Depth vs magnitude, for a scatter chart
        cursor.execute("""
            SELECT depth_km, magnitude
            FROM earthquakes
            WHERE depth_km IS NOT NULL AND magnitude IS NOT NULL
            LIMIT 500;
        """)
        depth_vs_magnitude = [
            {"depth": float(row[0]), "magnitude": float(row[1])}
            for row in cursor.fetchall()
        ]

        connection.close()

        return jsonify({
            "success": True,
            "total": total,
            "tsunami_count": tsunami_count,
            "strongest": float(strongest) if strongest else 0,
            "strongest_place": strongest_place,
            "avg_magnitude": float(avg_magnitude) if avg_magnitude else 0,
            "by_magnitude": by_magnitude,
            "by_alert": by_alert,
            "by_day": by_day,
            "depth_vs_magnitude": depth_vs_magnitude,
            "top_events": top_events,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route 3 — Health check
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "running",
        "message": "Earthquake Tracker API is live!"
    })

# ----------------------------------------
# START THE SERVER
# ----------------------------------------
if __name__ == "__main__":
    print("Starting Earthquake Tracker API...")
    print("API running at: http://localhost:5000")
    print("Test it at: http://localhost:5000/api/health")

    app.run(debug=True, port=5000)
