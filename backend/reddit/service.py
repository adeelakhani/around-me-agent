from agents.reddit_scraper import get_reddit_pois_direct
import random
import time

async def get_reddit_pois(city: str, province: str, country: str, user_lat: float, user_lon: float) -> list:
    """Get Reddit POIs for a location"""
    print(f"Starting direct Reddit scraper for coordinates: {user_lat}, {user_lon} in {city}, {province}, {country}")
    
    timestamp = int(time.time())
    print(f"=== USING DIRECT REDDIT SCRAPER ===")
    print(f"City: {city}")
    print(f"Province: {province}")
    print(f"Country: {country}")
    print(f"Timestamp: {timestamp}")
    print("=" * 50)
    
    try:
        # Use the direct Reddit scraper
        reddit_pois = await get_reddit_pois_direct(city, province, country, user_lat, user_lon)
        
        if reddit_pois:
            print(f"=== FOUND {len(reddit_pois)} REDDIT POIs ===")
            for i, poi in enumerate(reddit_pois, 1):
                print(f"Reddit POI {i}: {poi['name']} at {poi['lat']}, {poi['lng']}")
                print(f"Summary: {poi['summary'][:100]}...")
                print(f"Type: {poi['type']}")
                print("-" * 30)
        else:
            print("No Reddit POIs found")
            
        return reddit_pois
        
    except Exception as e:
        print(f"Reddit scraper error: {e}")
        import traceback
        traceback.print_exc()
        return []
