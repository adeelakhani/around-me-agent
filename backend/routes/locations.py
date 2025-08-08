# backend/routes/locations.py
from fastapi import APIRouter, Query
from agents.reddit_scraper import create_reddit_scraper_agent
from utils.location import get_user_location, get_radius_coordinates
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
    
    # Different subreddit combinations for variety - focus on local knowledge
    # Use just the main city subreddit for faster, universal results
    subreddit_combinations = [
        ["toronto"]  # Just use r/toronto for now, can be made dynamic later
    ]
    
    # Pick a random combination
    subreddit_combo = random.choice(subreddit_combinations)
    print(f"=== USING SUBREDDIT COMBINATION ===")
    print(f"Combination: {subreddit_combo}")
    print(f"Timestamp: {timestamp}")
    print("=" * 50)
    
    # Use just one location for faster results
    location_configs = [
        {"coords": (user_lat, user_lon), "subreddit": subreddit_combo[0], "area": "Downtown"},
    ]
    
    # Create location objects with different Reddit data
    all_pois = []
    
    for i, config in enumerate(location_configs):
        poi_lat, poi_lon = config["coords"]
        subreddit = config["subreddit"]
        area = config["area"]
        
        # Create LangGraph agent for each location
        agent = create_reddit_scraper_agent(subreddit)
        
        # Create location data with specific coordinates
        city = "Toronto"  # Use Toronto since we're in Toronto coordinates
        location_data = {
            "name": f"{area} {city}",
            "type": "reddit",
            "lat": poi_lat,
            "lng": poi_lon,
            "subreddit": subreddit,
            "city": city,
            "province": "Ontario", 
            "country": "Canada",
            "data": {}
        }
        
        # Run LangGraph agent to scrape and create one POI
        initial_state = {
            "messages": [],
            "location_data": location_data,
            "reddit_data": [],
            "current_step": "scrape_reddit",
            "pois": [],
            "subreddit": subreddit,
            "city": city,
            "scraped_content": None,
            "extracted_pois": []
        }
        
        print(f"Invoking LangGraph agent for POI {i+1} at coordinates {poi_lat}, {poi_lon}...")
        try:
            # Call the compiled workflow
            result = agent.invoke(initial_state, config={"recursion_limit": 50})
            print(f"LangGraph result keys: {list(result.keys())}")
            print(f"LangGraph messages count: {len(result.get('messages', []))}")
            
            # Get POI from the result
            pois = result.get("pois", [])
            print(f"Found {len(pois)} POIs for location {i+1}")
            
            if pois:
                print(f"=== FOUND {len(pois)} POIs FOR LOCATION {i+1} ===")
                # Add ALL POIs found, not just the first one
                for j, poi in enumerate(pois):
                    print(f"POI {i+1}.{j+1}: {poi['name']} at {poi['lat']}, {poi['lng']}")
                    print(f"Summary: {poi['summary'][:100]}...")
                    print(f"Subreddit: {subreddit}")
                    print(f"Area: {area}")
                    print("-" * 30)
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