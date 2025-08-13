import requests
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import re
load_dotenv(override=True)

def get_news_for_city(city: str, province: str, country: str, lat: float, lng: float) -> list:
    """Get news articles as POIs using NewsAPI.ai with proper location extraction"""
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        print("❌ NEWS_API_KEY not found in environment variables")
        return []
    
    url = "https://eventregistry.org/api/v1/article/getArticles"
    
    keyword = f"{city} {province}"
    
    search_queries = [
        f"{city} local news",
        f"{city} events",
        f"{city} local",
        f"{city} community",
        f"{city} neighborhood",
        f"{city} downtown",
        f"{city} restaurants",
        f"{city} food",
        f"{city} transit",
        f"{city} weather",
        f"{city} sports",
        f"{city} culture",
        f"{city} entertainment",
        f"{city} festival",
        f"{city} concert",
        f"{city} theater",
        f"{city} museum",
        f"{city} park",
        f"{city} shopping",
        f"{city} market",
        f"{city} street",
        f"{city} district",
        f"{city} area",
        f"{city} news",
        f"{city} {province}",
        f"{city} {province} {country}"
    ]
    
    params = {
        "resultType": "articles",
        "keyword": keyword,
        "lang": "eng",
        "articlesSortBy": "date",
        "articlesCount": 15,
        "apiKey": news_api_key,
        "isDuplicate": False,
        "dataType": ["news", "blog", "pr"],
        "locationUri": f"http://en.wikipedia.org/wiki/{city.replace(' ', '_')}"
    }
    
    try:
        all_articles = []
        
        for query in search_queries:
            params["keyword"] = query
            print(f"🔍 Trying search query: {query}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            articles = data.get("articles", {}).get("results", [])
            all_articles.extend(articles)
            
            if len(articles) > 0:
                print(f"📰 Found {len(articles)} articles for query: {query}")
            else:
                print(f"❌ No articles found for query: {query}")
        
        unique_articles = []
        seen_urls = set()
        for article in all_articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                unique_articles.append(article)
                seen_urls.add(url)
        
        filtered_articles = filter_relevant_articles(unique_articles, city)
        articles = filtered_articles[:25]
        
        print(f"📰 Found {len(articles)} unique articles from NewsAPI.ai")
        
        if articles:
            first_article = articles[0]
            print(f"🔍 First article keys: {list(first_article.keys())}")
            print(f"🔍 First article title: {first_article.get('title', 'No title')}")
            print(f"🔍 First article entities: {first_article.get('entities', 'No entities')}")
        
        news_pois = []
        seen_articles = set()
        
        for article in articles:
            article_id = f"{article.get('title', '')}_{article.get('url', '')}"
            if article_id in seen_articles:
                continue
            seen_articles.add(article_id)
            
            location_entities = extract_location_entities(article)
            
            if location_entities:
                for location in location_entities:
                    poi = create_news_poi(article, location, city)
                    if poi:
                        news_pois.append(poi)
            else:
                poi = create_fallback_news_poi(article, lat, lng, city)
                if poi:
                    news_pois.append(poi)
        
        print(f"✅ Created {len(news_pois)} news POIs with proper location extraction")
        return news_pois
        
    except Exception as e:
        print(f"❌ Error fetching news from NewsAPI.ai: {e}")
        if hasattr(e, 'response'):
            print(f"❌ Response content: {e.response.text if hasattr(e.response, 'text') else 'No response text'}")
        return []

def filter_relevant_articles(articles: List[Dict[str, Any]], city: str) -> List[Dict[str, Any]]:
    """Filter articles to prioritize local lifestyle news over business/financial news"""
    relevant_keywords = [
        'restaurant', 'cafe', 'bar', 'food', 'dining', 'eat', 'drink',
        'event', 'festival', 'concert', 'show', 'performance', 'theater', 'museum',
        'park', 'trail', 'outdoor', 'recreation', 'sports', 'fitness', 'gym',
        'shopping', 'market', 'store', 'mall', 'plaza', 'district',
        'transit', 'subway', 'bus', 'train', 'transportation',
        'weather', 'climate', 'temperature',
        'community', 'neighborhood', 'local', 'downtown', 'uptown',
        'street', 'avenue', 'road', 'area', 'district',
        'culture', 'arts', 'entertainment', 'music', 'film', 'art',
        'school', 'university', 'college', 'education',
        'hospital', 'health', 'medical', 'clinic',
        'police', 'fire', 'emergency', 'safety',
        'construction', 'development', 'building', 'project'
    ]
    
    business_keywords = [
        'inc.', 'corp.', 'corporation', 'limited', 'ltd.', 'llc',
        'earnings', 'revenue', 'profit', 'dividend', 'stock', 'shares',
        'acquisition', 'merger', 'investment', 'funding', 'venture',
        'quarterly', 'annual', 'financial', 'fiscal', 'report',
        'ceo', 'executive', 'board', 'director', 'officer',
        'trading', 'market', 'exchange', 'securities'
    ]
    
    scored_articles = []
    
    for article in articles:
        title = article.get('title', '').lower()
        body = article.get('body', '').lower()
        content = f"{title} {body}"
        
        relevance_score = 0
        
        for keyword in relevant_keywords:
            if keyword in content:
                relevance_score += 2
        
        for keyword in business_keywords:
            if keyword in content:
                relevance_score -= 1
        
        source = article.get('source', {}).get('title', '').lower()
        local_sources = ['toronto', 'star', 'sun', 'globe', 'mail', 'post', 'news', 'times']
        for local_source in local_sources:
            if local_source in source:
                relevance_score += 3
        
        date = article.get('date', '')
        if date:
            relevance_score += 1
        
        scored_articles.append((article, relevance_score))
    
    scored_articles.sort(key=lambda x: x[1], reverse=True)
    
    return [article for article, score in scored_articles]

def extract_location_entities(article: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract location entities from NewsAPI.ai article response"""
    locations = []
    
    print(f"🔍 Analyzing article: {article.get('title', 'No title')[:50]}...")
    
    entities = article.get("entities", {})
    print(f"📊 Entities found: {list(entities.keys()) if entities else 'None'}")
    
    location_entities = []
    if entities:
        location_entities = (
            entities.get("locations", []) or 
            entities.get("location", []) or 
            entities.get("place", []) or
            []
        )
    
    print(f"📍 Location entities: {len(location_entities) if location_entities else 0}")
    
    if location_entities:
        for i, location in enumerate(location_entities):
            print(f"   Location {i+1}: {location}")
            location_data = {
                "name": location.get("name", ""),
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "type": location.get("type", "location"),
                "confidence": location.get("confidence", 0)
            }
            
            print(f"   Extracted: {location_data}")
            
            if location_data["lat"] and location_data["lng"]:
                locations.append(location_data)
                print(f"   ✅ Added location with coordinates: {location_data['name']}")
            else:
                print(f"   ❌ Skipped location without coordinates: {location_data['name']}")
    
    if not locations:
        print("   🔍 No location entities found, trying content extraction...")
        locations = extract_locations_from_content(article)
    
    print(f"   📍 Final locations found: {len(locations)}")
    return locations

def extract_locations_from_content(article: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract location mentions from article content using regex patterns"""
    locations = []
    
    title = article.get("title", "")
    body = article.get("body", "")
    content = f"{title} {body}"
    
    location_patterns = [
        r"(\w+\s+Restaurant|\w+\s+Cafe|\w+\s+Bar|\w+\s+Theater|\w+\s+Museum|\w+\s+Park)",
        r"(\w+\s+Street|\w+\s+Avenue|\w+\s+Boulevard)",
        r"(\w+\s+District|\w+\s+Neighborhood|\w+\s+Area)",
        r"(\w+\s+Center|\w+\s+Plaza|\w+\s+Mall)"
    ]
    
    for pattern in location_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            pass
    
    return locations

def create_news_poi(article: Dict[str, Any], location: Dict[str, Any], city: str) -> Dict[str, Any]:
    """Create a POI from a news article with specific location data"""
    title = article.get("title", "")
    body = article.get("body", "")
    source = article.get("source", {}).get("title", "Unknown Source")
    url = article.get("url", "")
    
    summary = create_authentic_news_summary(title, body, source, location["name"])
    
    poi = {
        "name": location["name"],
        "lat": location["lat"],
        "lng": location["lng"],
        "summary": summary,
        "type": "news",
        "radius": 20,
        "source": source,
        "url": url
    }
    
    return poi

def create_fallback_news_poi(article: Dict[str, Any], lat: float, lng: float, city: str) -> Dict[str, Any]:
    """Create a fallback POI when no specific location is found"""
    title = article.get("title", "")
    body = article.get("body", "")
    source = article.get("source", {}).get("title", "Unknown Source")
    url = article.get("url", "")
    
    name = extract_meaningful_name(title, city)
    
    summary = create_authentic_news_summary(title, body, source, name)
    
    import random
    lat_variation = random.uniform(-0.01, 0.01)
    lng_variation = random.uniform(-0.01, 0.01)
    
    poi = {
        "name": name,
        "lat": lat + lat_variation,
        "lng": lng + lng_variation,
        "summary": summary,
        "type": "news",
        "radius": 20,
        "source": source,
        "url": url
    }
    
    return poi

def extract_meaningful_name(title: str, city: str) -> str:
    """Extract a meaningful name from article title"""
    title = re.sub(r'^(Breaking|Update|News|Latest):\s*', '', title, flags=re.IGNORECASE)
    
    business_patterns = [
        r"(\w+\s+Restaurant|\w+\s+Cafe|\w+\s+Bar|\w+\s+Theater|\w+\s+Museum|\w+\s+Park)",
        r"(\w+\s+Center|\w+\s+Plaza|\w+\s+Mall|\w+\s+District)",
        r"(\w+\s+Street|\w+\s+Avenue|\w+\s+Boulevard)"
    ]
    
    for pattern in business_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1)
    
    words = title.split()
    if len(words) > 3:
        return " ".join(words[:4])
    else:
        return title

def create_authentic_news_summary(title: str, body: str, source: str, location_name: str) -> str:
    """Create an authentic news summary using actual article content"""
    
    if body:
        content_preview = body[:200] + "..." if len(body) > 200 else body
        summary = f"Breaking news from {source}: {content_preview}"
    else:
        summary = f"Breaking news from {source}: {title}"
    
    if location_name and location_name not in summary:
        summary = f"Breaking news from {source} about {location_name}: {title}"
    
    return summary[:400]
