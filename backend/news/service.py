from agents.news_scraper import get_news_for_city
import time

def get_news_pois(city: str, province: str, country: str, user_lat: float, user_lon: float) -> list:
    """Get News POIs for a location"""
    print(f"Starting News API for coordinates: {user_lat}, {user_lon} in {city}, {province}, {country}")
    
    timestamp = int(time.time())
    print(f"=== USING NEWS API ===")
    print(f"City: {city}")
    print(f"Province: {province}")
    print(f"Country: {country}")
    print(f"Timestamp: {timestamp}")
    print("=" * 50)
    
    try:
        # Get news POIs using the news scraper
        news_pois = get_news_for_city(city, province, country, user_lat, user_lon)
        
        if news_pois:
            print(f"=== FOUND {len(news_pois)} NEWS POIs ===")
            for i, poi in enumerate(news_pois, 1):
                print(f"News POI {i}: {poi['name']} at {poi['lat']}, {poi['lng']}")
                print(f"Summary: {poi['summary'][:100]}...")
                print(f"Type: {poi['type']}")
                print("-" * 30)
        else:
            print("No news POIs found")
            
        return news_pois
        
    except Exception as e:
        print(f"News API error: {e}")
        import traceback
        traceback.print_exc()
        return []
