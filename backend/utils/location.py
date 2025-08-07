import requests
from typing import Tuple, Dict
import os

def get_user_location() -> Tuple[float, float]:
    """Get the user's location using IP geolocation."""
    # try:
    #     response = requests.get("https://ipinfo.io/json")
    #     data = response.json()
    #     return float(data["loc"].split(",")[0]), float(data["loc"].split(",")[1])
    # except Exception as e:
    #     print(f"Error getting user location: {e}")
    return 43.6532, -79.3832  # Downtown Toronto

def get_location_name(lat: float, lon: float) -> str:
    """Get the city name using coordinates."""
    # For now, return Toronto since we're focusing on Toronto
    return "Toronto"
    
    # Uncomment this when you have a Mapbox access token
    # url: str = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
    # params = {
    #     "access_token": os.getenv("MAPBOX_ACCESS_TOKEN"),
    #     "types": "place",
    # }
    # response = requests.get(url, params=params)
    # data = response.json()
    # if data.get("features"):
    #     return data["features"][0]["text"]
    # return "Unknown Location"

def get_radius_coordinates(lat: float, lon: float, radius_km: int = 20) -> Dict:
    """Calculate bounding box for 20km radius"""
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * abs(lat) / 90.0)
    
    return {
        "min_lat": lat - lat_delta,
        "max_lat": lat + lat_delta,
        "min_lon": lon - lon_delta,
        "max_lon": lon + lon_delta,
        "center_lat": lat,
        "center_lon": lon
    }
