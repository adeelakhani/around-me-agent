# backend/routes/locations.py
from fastapi import APIRouter, Query
from agents.summarizer import create_summarizer_agent
from utils.location import get_user_location, get_radius_coordinates, get_location_name
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)

router = APIRouter()

@router.get("/locations")
async def get_locations(
    lat: float = Query(None, description="User latitude"),
    lon: float = Query(None, description="User longitude")
):
    if lat and lon:
        user_lat, user_lon = lat, lon
    else:
        user_lat, user_lon = get_user_location()
    
    print(f"Starting LangGraph agent for coordinates: {user_lat}, {user_lon}")
    
    # Create different coordinates and subreddits for variety
    import random
    import time
    
    # Add some randomness to get different results each time
    timestamp = int(time.time())
    random.seed(timestamp)
    
    # Different subreddit combinations for variety
    subreddit_combinations = [
        ["toronto", "askTO", "torontoevents", "torontofood"],
        ["askTO", "torontoevents", "torontofood", "toronto"],
        ["torontoevents", "torontofood", "toronto", "askTO"],
        ["torontofood", "toronto", "askTO", "torontoevents"],
    ]
    
    # Pick a random combination
    subreddit_combo = random.choice(subreddit_combinations)
    
    location_configs = [
        {"coords": (user_lat, user_lon), "subreddit": subreddit_combo[0], "area": "Downtown"},
        {"coords": (user_lat + 0.01, user_lon + 0.01), "subreddit": subreddit_combo[1], "area": "North-East"},
        {"coords": (user_lat - 0.01, user_lon - 0.01), "subreddit": subreddit_combo[2], "area": "South-West"},
        {"coords": (user_lat + 0.02, user_lon - 0.02), "subreddit": subreddit_combo[3], "area": "North-West"},
    ]
    
    # Create location objects with different Reddit data
    all_pois = []
    
    for i, config in enumerate(location_configs):
        poi_lat, poi_lon = config["coords"]
        subreddit = config["subreddit"]
        area = config["area"]
        
        # Create LangGraph agent for each location
        agent = create_summarizer_agent(subreddit)
        
        # Create location data with specific coordinates
        location_data = {
            "name": f"{area} Toronto",
            "type": "reddit",
            "lat": poi_lat,
            "lng": poi_lon,
            "subreddit": subreddit,
            "city": "Toronto",
            "province": "Ontario", 
            "country": "Canada",
            "data": {}
        }
        
        # Run LangGraph agent to scrape and create one POI
        initial_state = {
            "messages": [],
            "location_data": location_data,
            "reddit_data": [],
            "weather_data": {},
            "events_data": [],
            "news_data": [],
            "summary": None,
            "current_step": "start",
            "pois": []
        }
        
        print(f"Invoking LangGraph agent for POI {i+1} at coordinates {poi_lat}, {poi_lon}...")
        try:
            result = agent.invoke(initial_state, config={"recursion_limit": 50})
            print(f"LangGraph result keys: {list(result.keys())}")
            print(f"LangGraph messages count: {len(result.get('messages', []))}")
            
            # Get POI from the result
            pois = result.get("pois", [])
            print(f"Found {len(pois)} POIs for location {i+1}")
            
            if pois:
                # Use the POI with its real coordinates (don't override them)
                poi = pois[0]
                print(f"Using POI with real coordinates: {poi['name']} at {poi['lat']}, {poi['lng']}")
                all_pois.append(poi)
            else:
                print(f"No POI found for location {i+1}, skipping")
                continue
            
        except Exception as e:
            print(f"LangGraph error for POI {i+1}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print(f"Returning {len(all_pois)} unique POIs")
    return all_pois

@router.get("/user-location")
async def get_user_location_endpoint():
    lat, lon = get_user_location()
    radius_coords = get_radius_coordinates(lat, lon, 20)
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": 20,
        "bounding_box": radius_coords
    }