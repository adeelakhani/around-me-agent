import requests
import os
from dotenv import load_dotenv
load_dotenv(override=True)

def get_news_for_city(city: str, province: str, country: str, lat: float, lng: float) -> list:
    """Get news articles as POIs using NewsAPI.ai"""
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        print("❌ NEWS_API_KEY not found in environment variables")
        return []
    
    # Use NewsAPI.ai endpoint for article search
    url = "https://eventregistry.org/api/v1/article/getArticles"
    
    # Create search query with city, province, country
    keyword = f"{city} {province} {country}"
    
    params = {
        "resultType": "articles",
        "keyword": keyword,
        "lang": "eng",
        "articlesSortBy": "date",
        "articlesCount": 10,
        "apiKey": news_api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # NewsAPI.ai returns articles in different format
        articles = data.get("articles", {}).get("results", [])
        
        # Convert to POI format like Reddit scraper
        news_pois = []
        for article in articles[:10]:  # Limit to top 10
            title = article.get("title", "")
            body = article.get("body", "")
            source = article.get("source", {}).get("title", "Unknown Source")
            
            # Create summary like Reddit does
            # Use first 200 chars of body or title if no body
            description = body[:200] + "..." if body else title
            summary = f"Breaking news from {source}: {description}"
            
            # Return in exact same format as Reddit POIs
            poi = {
                "name": title,
                "lat": lat,  # Use city coordinates
                "lng": lng,  # Use city coordinates
                "summary": summary,
                "type": "news",
                "radius": 20
            }
            news_pois.append(poi)
        
        print(f"✅ Found {len(news_pois)} news articles from NewsAPI.ai")
        return news_pois
        
    except Exception as e:
        print(f"❌ Error fetching news from NewsAPI.ai: {e}")
        # Also print the response if it's an HTTP error
        if hasattr(e, 'response'):
            print(f"❌ Response content: {e.response.text if hasattr(e.response, 'text') else 'No response text'}")
        return []
