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
    """Get the city name using coordinates via Mapbox Geocoding API."""
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("⚠️ MAPBOX_ACCESS_TOKEN not found, using fallback")
        return "Toronto"  # Fallback if no token
    
    try:
        # Mapbox expects longitude,latitude order
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
        params = {
            "access_token": mapbox_token,
            "types": "place",
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("features"):
            # Get the first (most relevant) result
            city_name = data["features"][0]["text"]
            print(f"📍 Found city: {city_name} for coordinates {lat}, {lon}")
            return city_name
        else:
            print(f"⚠️ No city found for coordinates {lat}, {lon}")
            return "Toronto"  # Fallback
            
    except Exception as e:
        print(f"❌ Mapbox geocoding error: {e}")
        return "Toronto"  # Fallback

def get_location_details(lat: float, lon: float) -> dict:
    """Get city, province/state, and country using coordinates via Mapbox Geocoding API."""
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("⚠️ MAPBOX_ACCESS_TOKEN not found, using fallback")
        return {
            "city": "Toronto",
            "province": "Ontario", 
            "country": "Canada"
        }
    
    try:
        # Mapbox expects longitude,latitude order
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lon},{lat}.json"
        params = {
            "access_token": mapbox_token,
            "types": "place",
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("features"):
            feature = data["features"][0]
            context = feature.get("context", [])
            
            # Extract city, province/state, and country from context
            city = feature["text"]
            province = "Unknown"
            country = "Unknown"
            
            for item in context:
                if item["id"].startswith("region"):
                    province = item["text"]
                elif item["id"].startswith("country"):
                    country = item["text"]
            
            print(f"📍 Found location: {city}, {province}, {country} for coordinates {lat}, {lon}")
            return {
                "city": city,
                "province": province,
                "country": country
            }
        else:
            print(f"⚠️ No location found for coordinates {lat}, {lon}")
            return {
                "city": "Toronto",
                "province": "Ontario",
                "country": "Canada"
            }
            
    except Exception as e:
        print(f"❌ Mapbox geocoding error: {e}")
        return {
            "city": "Toronto",
            "province": "Ontario",
            "country": "Canada"
        }

def is_coordinates_in_city(lat: float, lon: float, city_name: str) -> bool:
    """Check if coordinates are within the detected city bounds."""
    mapbox_token = os.getenv("MAPBOX_ACCESS_TOKEN")
    if not mapbox_token:
        print("⚠️ MAPBOX_ACCESS_TOKEN not found, skipping city bounds check")
        return True  # Skip check if no token
    
    try:
        # Search for the city to get its bounds
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{city_name}.json"
        params = {
            "access_token": mapbox_token,
            "types": "place",
            "limit": 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("features"):
            feature = data["features"][0]
            bbox = feature.get("bbox")  # [min_lon, min_lat, max_lon, max_lat]
            
            if bbox:
                min_lon, min_lat, max_lon, max_lat = bbox
                
                # Check if coordinates are within city bounds
                in_bounds = (min_lon <= lon <= max_lon) and (min_lat <= lat <= max_lat)
                
                if in_bounds:
                    print(f"✅ Coordinates ({lat}, {lon}) are within {city_name} bounds")
                else:
                    print(f"❌ Coordinates ({lat}, {lon}) are outside {city_name} bounds")
                    print(f"   City bounds: {min_lon}, {min_lat} to {max_lon}, {max_lat}")
                
                return in_bounds
            else:
                print(f"⚠️ No bounds found for {city_name}, skipping check")
                return True
        else:
            print(f"⚠️ City {city_name} not found, skipping bounds check")
            return True
            
    except Exception as e:
        print(f"❌ Error checking city bounds: {e}")
        return True  # Skip check on error


