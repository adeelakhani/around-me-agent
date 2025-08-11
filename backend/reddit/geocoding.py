"""
Geocoding utilities for Reddit POI extraction
"""
import os
import requests
from typing import Optional, Dict
from utils.location import is_coordinates_in_city
from langchain_core.messages import SystemMessage, HumanMessage

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
    """Try multiple geocoding methods with fallbacks - SERPER FIRST for accuracy"""
    print(f"🗺️ Geocoding {poi_name} with fallback methods...")
    
    # Method 1: Try Serper.dev first (most accurate for specific places)
    try:
        print(f"🔍 Trying Serper for {poi_name}...")
        search_queries = [
            f'"{poi_name}" "{city}" exact address coordinates',
            f'"{poi_name}" "{city}" location address',
            f'"{poi_name}" "{city}" map coordinates',
            f'"{poi_name}" "{city}"'
        ]
        
        for i, search_query in enumerate(search_queries):
            print(f"  Serper search {i+1}: {search_query}")
            search_results = search_serper(search_query)
            
            if search_results.get("organic") and len(search_results["organic"]) > 0:
                print(f"✅ Serper search {i+1} returned {len(search_results['organic'])} results")
                
                # Extract text from search results
                search_text = ""
                if search_results.get("organic"):
                    for result in search_results["organic"][:3]:  # Top 3 results
                        search_text += f"Title: {result.get('title', '')}\n"
                        search_text += f"Snippet: {result.get('snippet', '')}\n\n"
                
                if search_results.get("knowledgeGraph"):
                    kg = search_results["knowledgeGraph"]
                    search_text += f"Knowledge Graph: {kg.get('title', '')}\n"
                    search_text += f"Description: {kg.get('description', '')}\n"
                
                # Use LLM to extract coordinates from search results
                from langchain_openai import ChatOpenAI
                from reddit.models import Coordinates
                
                llm = ChatOpenAI(model="gpt-4o-mini")
                llm_with_coords = llm.with_structured_output(Coordinates)
                
                coord_response = llm_with_coords.invoke([
                    SystemMessage(content="""Extract EXACT latitude and longitude coordinates for the specific place.

LOOK FOR:
- GPS coordinates like "43.6532, -79.3832" or "43°39'11.5"N 79°22'59.9"W"
- Address with street number and name
- "Located at" or "Address:" followed by coordinates
- Google Maps links with coordinates
- Business listings with exact addresses

ONLY return coordinates if they are SPECIFICALLY for the exact place mentioned.
If coordinates are for general city area, return 0.0, 0.0"""),
                    HumanMessage(content=search_text)
                ])
                
                if coord_response.lat != 0.0 and coord_response.lng != 0.0:
                    # Check if coordinates are within the city bounds
                    if is_coordinates_in_city(coord_response.lat, coord_response.lng, city):
                        coords = {
                            'lat': coord_response.lat,
                            'lng': coord_response.lng
                        }
                        print(f"✅ Serper found coordinates for {poi_name}: ({coords['lat']}, {coords['lng']})")
                        return coords
                    else:
                        print(f"❌ Serper coordinates for {poi_name} are outside {city} bounds")
                else:
                    print(f"❌ No coordinates found for {poi_name} with Serper search {i+1}")
            else:
                print(f"⚠️ Serper search {i+1} returned no results")
        
        print(f"❌ All Serper searches failed for {poi_name}")
        
    except Exception as e:
        print(f"❌ Serper geocoding error: {e}")
    
    # Method 2: Try OpenStreetMap Nominatim (fallback)
    try:
        print(f"🗺️ Trying OpenStreetMap for {poi_name}...")
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
