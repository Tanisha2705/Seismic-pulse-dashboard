# fetch_data.py
# Pulls real earthquake data from the USGS Earthquake Catalog API.
# This is a completely free, keyless API run by the US Geological Survey.

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

USGS_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def fetch_earthquakes(days_back=30, min_magnitude=2.5, limit=1000):
    """
    Fetches earthquakes from the last `days_back` days with at least
    `min_magnitude`. Returns the raw GeoJSON response as a Python dict.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)

    params = {
        "format": "geojson",
        "starttime": start_time.strftime("%Y-%m-%d"),
        "endtime": end_time.strftime("%Y-%m-%d"),
        "minmagnitude": min_magnitude,
        "limit": limit,
        "orderby": "time",
    }

    print(f"Fetching earthquakes (min magnitude {min_magnitude}, last {days_back} days)...")
    response = requests.get(USGS_API_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    print(f"Fetched {len(data.get('features', []))} earthquakes")
    return data


def parse_earthquakes(raw_data):
    """
    Converts the raw GeoJSON response into a clean pandas DataFrame,
    one row per earthquake, ready to store in PostgreSQL.
    """
    records = []

    for feature in raw_data.get("features", []):
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", [None, None, None])

        # USGS gives time as milliseconds since epoch
        event_time = None
        if props.get("time"):
            event_time = datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc)

        records.append({
            "earthquake_id": feature.get("id"),
            "place": props.get("place") or "Unknown location",
            "magnitude": props.get("mag"),
            "mag_type": props.get("magType"),
            "depth_km": coordinates[2] if len(coordinates) > 2 else None,
            "longitude": coordinates[0] if len(coordinates) > 0 else None,
            "latitude": coordinates[1] if len(coordinates) > 1 else None,
            "event_time": event_time,
            "tsunami": bool(props.get("tsunami", 0)),
            "alert": props.get("alert"),
            "significance": props.get("sig"),
            "status": props.get("status"),
        })

    df = pd.DataFrame(records)

    # Drop any rows missing a magnitude or id — not usable data
    df = df.dropna(subset=["earthquake_id", "magnitude"])

    return df


if __name__ == "__main__":
    raw = fetch_earthquakes(days_back=7, min_magnitude=4.0)
    df = parse_earthquakes(raw)
    print(df.head())
    print(f"\nTotal parsed: {len(df)} earthquakes")
