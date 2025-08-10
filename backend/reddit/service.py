from agents.reddit_scraper import create_reddit_scraper_agent
import random
import time

def get_reddit_pois(city: str, province: str, country: str, user_lat: float, user_lon: float) -> list:
    """Get Reddit POIs for a location"""
    print(f"Starting LangGraph agent for coordinates: {user_lat}, {user_lon} in {city}, {province}, {country}")
    
    # Create different coordinates and subreddits for variety
    timestamp = int(time.time())
    random.seed(timestamp)
    
    # Simple rule: r/{city}
    subreddit = city.lower()
    print(f"=== USING SUBREDDIT ===")
    print(f"City: {city}")
    print(f"Subreddit: r/{subreddit}")
    print(f"Timestamp: {timestamp}")
    print("=" * 50)
    
    # Use just one location for faster results
    location_configs = [
        {"coords": (user_lat, user_lon), "subreddit": subreddit, "area": "Downtown"},
    ]
    
    # Create location objects with different Reddit data
    all_pois = []
    
    for i, config in enumerate(location_configs):
        poi_lat, poi_lon = config["coords"]
        subreddit = config["subreddit"]
        area = config["area"]
        
        # Create LangGraph agent for each location
        agent = create_reddit_scraper_agent(subreddit, city)
        
        # Create location data with specific coordinates
        location_data = {
            "name": f"{area} {city}",
            "type": "reddit",
            "lat": poi_lat,
            "lng": poi_lon,
            "subreddit": subreddit,
            "city": city,
            "province": province, 
            "country": country,
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
    
    return all_pois
