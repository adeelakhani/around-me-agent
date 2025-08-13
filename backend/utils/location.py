import requests
from typing import Tuple, Dict
import os

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
        return True
    
    try:
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
            bbox = feature.get("bbox")
            
            if bbox:
                min_lon, min_lat, max_lon, max_lat = bbox
                
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
        return True


