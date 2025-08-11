"""
Geocoding utilities for Reddit POI extraction
"""
import os
import requests
from typing import Optional, Dict
from utils.location import is_coordinates_in_city

def search_serper(query: str) -> dict:
    """Search using Serper.dev API"""
    serper_key = os.getenv("SERPER_API_KEY")
    if not serper_key:
        print("⚠️ SERPER_API_KEY not found, using fallback coordinates")
        return {"organic": [], "knowledgeGraph": None}
        
    try:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": serper_key,
            "Content-Type": "application/json"
        }
        payload = {"q": query}
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Serper search error: {e}")
        return {"organic": [], "knowledgeGraph": None}

def geocode_with_fallback(poi_name: str, city: str, province: str, country: str) -> Optional[Dict[str, float]]:
    """Try multiple geocoding methods with fallbacks"""
    print(f"🗺️ Geocoding {poi_name} with fallback methods...")
    
    # Method 1: Try OpenStreetMap Nominatim (free, no API key required)
    try:
        search_query = f"{poi_name}, {city}, {province}, {country}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": search_query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        headers = {"User-Agent": "AroundMeAgent/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        
        if results and len(results) > 0:
            result = results[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            
            # Check if coordinates are within reasonable bounds for the city
            if is_coordinates_in_city(lat, lon, city):
                print(f"✅ OpenStreetMap found coordinates: ({lat}, {lon})")
                return {"lat": lat, "lng": lon}
            else:
                print(f"⚠️ OpenStreetMap coordinates outside city bounds: ({lat}, {lon})")
        else:
            print("❌ OpenStreetMap returned no results")
            
    except Exception as e:
        print(f"❌ OpenStreetMap geocoding error: {e}")
    
    # Method 2: Try Google Places API (if API key is available)
    try:
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if google_api_key:
            url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            params = {
                "input": f"{poi_name} {city}",
                "inputtype": "textquery",
                "fields": "geometry/location",
                "key": google_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "OK" and result.get("candidates"):
                location = result["candidates"][0]["geometry"]["location"]
                lat = location["lat"]
                lng = location["lng"]
                
                if is_coordinates_in_city(lat, lng, city):
                    print(f"✅ Google Places found coordinates: ({lat}, {lng})")
                    return {"lat": lat, "lng": lng}
                else:
                    print(f"⚠️ Google Places coordinates outside city bounds: ({lat}, {lng})")
            else:
                print(f"❌ Google Places error: {result.get('status')}")
        else:
            print("⚠️ GOOGLE_PLACES_API_KEY not found, skipping Google Places")
            
    except Exception as e:
        print(f"❌ Google Places geocoding error: {e}")
    
    # Method 3: Try Geopy (if installed)
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
        
        geolocator = Nominatim(user_agent="AroundMeAgent/1.0")
        search_query = f"{poi_name}, {city}, {province}, {country}"
        
        location = geolocator.geocode(search_query, timeout=10)
        
        if location:
            lat = location.latitude
            lon = location.longitude
            
            if is_coordinates_in_city(lat, lon, city):
                print(f"✅ Geopy found coordinates: ({lat}, {lon})")
                return {"lat": lat, "lng": lon}
            else:
                print(f"⚠️ Geopy coordinates outside city bounds: ({lat}, {lon})")
        else:
            print("❌ Geopy returned no results")
            
    except ImportError:
        print("⚠️ Geopy not installed, skipping Geopy geocoding")
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"❌ Geopy geocoding error: {e}")
    except Exception as e:
        print(f"❌ Geopy unexpected error: {e}")
    
    print(f"❌ All geocoding methods failed for {poi_name}")
    return None
