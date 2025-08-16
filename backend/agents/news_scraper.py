import requests
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
import re
load_dotenv(override=True)

def get_news_for_city(city: str, province: str, country: str, lat: float, lng: float, max_pois_per_article: int = 3) -> list:
    """Get news articles as POIs using NewsAPI.ai with proper location extraction
    
    Args:
        city: City name
        province: Province/state name  
        country: Country name
        lat: City latitude
        lng: City longitude
        max_pois_per_article: Maximum number of POIs to extract per article (default: 3)
    """
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        print("❌ NEWS_API_KEY not found in environment variables")
        return []
    
    url = "https://eventregistry.org/api/v1/article/getArticles"
    
    keyword = f"{city} {province}"
    
    # Enhanced search queries focused on events, openings, and things to do with locations
    search_queries = [
        f"{city} event",
        f"{city} opening",
        f"{city} new restaurant",
        f"{city} things to do",
        f"{city} entertainment",
        f"{city} local",
        f"{city} downtown",
        f"{city} festival"
    ]
    
    # Reduced date range and article count to save tokens
    from datetime import datetime, timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Get articles from last month only
    
    params = {
        "resultType": "articles",
        "keyword": keyword,
        "lang": "eng",
        "articlesSortBy": "date",
        "articlesCount": 5,
        "apiKey": news_api_key,
        "dataType": ["news", "blog", "pr"],
        "locationUri": f"http://en.wikipedia.org/wiki/{city.replace(' ', '_')}",
        "dateStart": start_date.strftime("%Y-%m-%d"),
        "dateEnd": end_date.strftime("%Y-%m-%d")
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
        
        # STRONG DEDUPLICATION - Create unique article hash based on title and content
        unique_articles = []
        seen_article_hashes = set()
        
        for article in all_articles:
            title = article.get('title', '').strip()
            body = article.get('body', '').strip()
            
            # Create a hash based on title and first 100 chars of body
            content_for_hash = f"{title}_{body[:100]}"
            import hashlib
            article_hash = hashlib.md5(content_for_hash.encode()).hexdigest()
            
            # Also check for similar titles (case-insensitive) - MORE AGGRESSIVE
            title_lower = title.lower().strip()
            is_duplicate = False
            
            for existing_article in unique_articles:
                existing_title = existing_article.get('title', '').lower().strip()
                # If titles are very similar OR contain the same key words, consider it a duplicate
                if (title_lower == existing_title or 
                    title_lower in existing_title or 
                    existing_title in title_lower or
                    # Check if they share key words (3+ words in common)
                    len(set(title_lower.split()) & set(existing_title.split())) >= 3):
                    is_duplicate = True
                    print(f"❌ Skipped similar title: {title[:50]}...")
                    break
            
            if article_hash not in seen_article_hashes and not is_duplicate:
                unique_articles.append(article)
                seen_article_hashes.add(article_hash)
                print(f"✅ Added unique article: {title[:50]}...")
            else:
                if is_duplicate:
                    print(f"❌ Skipped similar title: {title[:50]}...")
                else:
                    print(f"❌ Skipped duplicate hash: {title[:50]}...")
        
        filtered_articles = filter_relevant_articles(unique_articles, city)
        articles = filtered_articles[:10]  # Reduced from 20 to save tokens
        
        print(f"📰 Found {len(articles)} unique articles from NewsAPI.ai")
        
        if articles:
            first_article = articles[0]
            print(f"🔍 First article title: {first_article.get('title', 'No title')}")
        
        news_pois = []
        
        for article in articles:
            print(f"\n🔍 Processing article: {article.get('title', 'No title')[:60]}...")
            
            # Use LLM to extract real locations from article content
            content_locations = extract_locations_from_content(article, city, province, country, max_pois_per_article)
            if content_locations:
                print(f"   ✅ Found {len(content_locations)} locations from LLM extraction")
                for location in content_locations:
                    poi = create_news_poi(article, location, city)
                    if poi:
                        news_pois.append(poi)
                        print(f"   ✅ Created POI from LLM: {location['name']} at {location['lat']:.4f}, {location['lng']:.4f}")
            else:
                # NO FAKE COORDINATES - skip articles without real locations
                print(f"   ❌ Skipped article without real location: {article.get('title', 'No title')[:50]}...")
        
        # FINAL DEDUPLICATION - Remove any remaining duplicates by name
        final_pois = []
        seen_names = set()
        for poi in news_pois:
            name_lower = poi['name'].lower().strip()
            if name_lower not in seen_names:
                final_pois.append(poi)
                seen_names.add(name_lower)
            else:
                print(f"❌ Final dedup: Skipped duplicate name: {poi['name']}")
        
        print(f"✅ Created {len(final_pois)} unique news POIs with real geocoding")
        return final_pois
        
    except Exception as e:
        print(f"❌ Error fetching news from NewsAPI.ai: {e}")
        if hasattr(e, 'response'):
            print(f"❌ Response content: {e.response.text if hasattr(e.response, 'text') else 'No response text'}")
        return []

def filter_relevant_articles(articles: List[Dict[str, Any]], city: str) -> List[Dict[str, Any]]:
    """Filter articles to prioritize local lifestyle news over business/financial news"""
    relevant_keywords = [
        # Events and activities
        'event', 'festival', 'concert', 'show', 'performance', 'theater', 'museum', 'exhibition',
        'opening', 'launch', 'grand opening', 'ribbon cutting', 'ceremony',
        'things to do', 'activities', 'attractions', 'tourist', 'visitor',
        'entertainment', 'nightlife', 'party', 'celebration', 'gathering',
        
        # Food and dining
        'restaurant', 'cafe', 'bar', 'food', 'dining', 'eat', 'drink', 'bistro', 'pub',
        'new restaurant', 'opening soon', 'coming soon', 'soft opening',
        
        # Recreation and lifestyle
        'park', 'trail', 'outdoor', 'recreation', 'sports', 'fitness', 'gym', 'studio',
        'shopping', 'market', 'store', 'mall', 'plaza', 'district', 'boutique',
        
        # Culture and arts
        'culture', 'arts', 'music', 'film', 'art', 'gallery', 'venue', 'stage',
        'community', 'neighborhood', 'local', 'downtown', 'uptown',
        
        # Transportation and accessibility
        'transit', 'subway', 'bus', 'train', 'transportation', 'station', 'stop',
        
        # Development and new places
        'construction', 'development', 'building', 'project', 'renovation', 'expansion'
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
        # Generic local news sources that work for any city
        local_sources = ['star', 'sun', 'globe', 'mail', 'post', 'news', 'times', 'herald', 'tribune', 'journal', 'gazette']
        for local_source in local_sources:
            if local_source in source:
                relevance_score += 3
        
        date = article.get('date', '')
        if date:
            relevance_score += 1
        
        scored_articles.append((article, relevance_score))
    
    scored_articles.sort(key=lambda x: x[1], reverse=True)
    
    return [article for article, score in scored_articles]



def extract_locations_from_content(article: Dict[str, Any], city: str, province: str, country: str, max_pois_per_article: int = 3) -> List[Dict[str, Any]]:
    """Use LLM to extract real locations from article content"""
    from openai import OpenAI
    import os
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    title = article.get("title", "")
    body = article.get("body", "")
    content = f"Title: {title}\n\nBody: {body}"
    
    prompt = f"""
    Extract ONLY real, specific location names from this news article about {city}, {province}, {country}.
    
    Return ONLY the names of actual places, venues, businesses, streets, neighborhoods, or landmarks mentioned in the article.
    Examples: restaurants, cafes, theaters, museums, parks, shopping centers, stadiums, universities, hospitals, specific street names, neighborhood names, business names, etc.
    
    Do NOT include generic terms, partial matches, or non-location words.
    
    IMPORTANT: Format location names as they would appear in Google Maps search.
    - Use full business names: "Casa Loma" not "Casa"
    - Use proper venue names: "Toronto Hydro" not "Hydro"
    - Use street names with type: "King Street West" not "King"
    - Use neighborhood names: "Yorkville" not "York"
    
    Format: Return a simple list of location names, one per line.
    
    Article:
    {content}
    
    Real locations found:
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1
        )
        
        locations_text = response.choices[0].message.content.strip()
        location_names = [name.strip() for name in locations_text.split('\n') if name.strip()]
        
        print(f"   🤖 LLM found {len(location_names)} potential locations: {location_names}")
        
        locations = []
        # Only geocode the first N locations to save time (configurable)
        for location_name in location_names[:max_pois_per_article]:
            if location_name and len(location_name) > 2:  # Skip very short names
                geocoded_location = geocode_location(location_name, city, province, country)
                if geocoded_location:
                    locations.append(geocoded_location)
                    print(f"   ✅ Geocoded: {location_name} -> {geocoded_location['lat']:.4f}, {geocoded_location['lng']:.4f}")
                else:
                    print(f"   ❌ Failed to geocode: {location_name}")
        
        return locations
        
    except Exception as e:
        print(f"   ❌ LLM extraction error: {e}")
        return []

def geocode_location(location_name: str, city: str, province: str, country: str) -> Dict[str, Any]:
    """Simple, fast geocoding using Google Places API directly"""
    print(f"   🗺️ Quick geocoding: {location_name}")
    
    try:
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not google_api_key:
            print(f"   ❌ No Google Places API key")
            return None
        
        # Simple search with city context
        search_input = f"{location_name}, {city}"
        
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": search_input,
            "inputtype": "textquery",
            "fields": "geometry/location,name",
            "key": google_api_key
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "OK" and result.get("candidates"):
            location = result["candidates"][0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
            
            return {
                "name": location_name,
                "lat": lat,
                "lng": lng,
                "type": "geocoded",
                "confidence": 0.8
            }
        else:
            print(f"   ❌ No results for: {location_name}")
            return None
            
    except Exception as e:
        print(f"   ❌ Geocoding error: {e}")
        return None

def create_news_poi(article: Dict[str, Any], location: Dict[str, Any], city: str) -> Dict[str, Any]:
    """Create a POI from a news article with specific location data"""
    title = article.get("title", "")
    body = article.get("body", "")
    source = article.get("source", {}).get("title", "Unknown Source")
    url = article.get("url", "")
    date = article.get("date", "")
    
    summary = create_authentic_news_summary(title, body, source, location["name"], date)
    
    poi = {
        "name": location["name"],
        "lat": location["lat"],
        "lng": location["lng"],
        "summary": summary,
        "type": "news",
        "radius": 20,
        "source": source,
        "url": url,
        "date": date
    }
    
    return poi



def create_authentic_news_summary(title: str, body: str, source: str, location_name: str, date: str = "") -> str:
    """Create an authentic news summary using actual article content"""
    
    if body:
        content_preview = body[:200] + "..." if len(body) > 200 else body
        summary = f"Breaking news from {source}: {content_preview}"
    else:
        summary = f"Breaking news from {source}: {title}"
    
    if location_name and location_name not in summary:
        summary = f"Breaking news from {source} about {location_name}: {title}"
    
    # Add date if available
    if date:
        try:
            # Format the date nicely
            from datetime import datetime
            parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            formatted_date = parsed_date.strftime("%B %d, %Y")
            summary += f"\n📅 Published: {formatted_date}"
        except:
            summary += f"\n📅 Published: {date}"
    
    return summary[:400]
