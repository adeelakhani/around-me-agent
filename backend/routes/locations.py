# backend/routes/locations.py
from fastapi import APIRouter, Query
from reddit.service import get_reddit_pois
from news.service import get_news_pois
from utils.location import get_user_location, get_location_details
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)

router = APIRouter()

def get_dummy_pois():
    """Return dummy POI data for UI testing - matches real API structure"""
    # Reddit POIs
    reddit_pois = [
        {
            "name": "Hidden Coffee Shop",
            "lat": 43.6532,
            "lng": -79.3832,
            "summary": "A cozy local coffee shop with amazing pastries and friendly baristas. Perfect spot for remote work or catching up with friends. Reddit users love the quiet atmosphere and great wifi.",
            "type": "reddit",
            "radius": 20
        },
        {
            "name": "Urban Park Trail", 
            "lat": 43.6545,
            "lng": -79.3845,
            "summary": "Beautiful walking trail through the city park with scenic views, perfect for morning runs or evening strolls. Features a small lake and picnic areas. Great for families and outdoor enthusiasts.",
            "type": "reddit",
            "radius": 20
        },
        {
            "name": "Vintage Bookstore",
            "lat": 43.6520,
            "lng": -79.3820,
            "summary": "Charming independent bookstore specializing in rare and vintage books. Cozy reading nooks and knowledgeable staff who love to recommend hidden gems. Book lovers rave about the selection.",
            "type": "reddit",
            "radius": 20
        },
        {
            "name": "Artisan Bakery",
            "lat": 43.6550,
            "lng": -79.3850,
            "summary": "Family-owned bakery known for their sourdough bread and custom cakes. Everything is made fresh daily using traditional methods and local ingredients. Locals swear by their pastries.",
            "type": "reddit",
            "radius": 20
        },
        {
            "name": "I Miss You Man",
            "lat": 43.6538,
            "lng": -79.3883,
            "summary": "Popular restaurant mentioned frequently in Reddit discussions. Known for great food and atmosphere. Many users recommend trying their signature dishes.",
            "type": "reddit",
            "radius": 20
        }
    ]
    
    # News POIs
    news_pois = [
        {
            "name": "Toronto International Film Festival",
            "lat": 43.6487,
            "lng": -79.3774,
            "summary": "TIFF 2024 announces exciting lineup featuring world premieres and award-winning films. The festival brings together filmmakers and movie enthusiasts from around the globe.",
            "type": "news",
            "radius": 20,
            "source": "Toronto Star",
            "url": "https://www.thestar.com/entertainment/movies/tiff-2024"
        },
        {
            "name": "CN Tower Restaurant",
            "lat": 43.6426,
            "lng": -79.3871,
            "summary": "New seasonal menu launched at the iconic CN Tower restaurant. Diners can enjoy panoramic city views while sampling locally-sourced ingredients.",
            "type": "news",
            "radius": 20,
            "source": "Toronto Life",
            "url": "https://torontolife.com/food/cn-tower-restaurant-new-menu"
        },
        {
            "name": "Kensington Market Festival",
            "lat": 43.6548,
            "lng": -79.4000,
            "summary": "Annual street festival returns to Kensington Market with live music, food vendors, and cultural performances. The event celebrates the neighborhood's diverse community.",
            "type": "news",
            "radius": 20,
            "source": "BlogTO",
            "url": "https://www.blogto.com/events/kensington-market-festival-2024"
        },
        {
            "name": "High Park Cherry Blossoms",
            "lat": 43.6467,
            "lng": -79.4654,
            "summary": "Cherry blossoms in full bloom at High Park. Thousands of visitors flock to see the beautiful pink flowers. Peak viewing time expected this weekend.",
            "type": "news",
            "radius": 20,
            "source": "CBC Toronto",
            "url": "https://www.cbc.ca/news/canada/toronto/high-park-cherry-blossoms-2024"
        }
    ]
    
    # Combine both types
    return reddit_pois + news_pois

@router.get("/locations")
async def get_locations(
    lat: float = Query(None, description="User latitude"),
    lon: float = Query(None, description="User longitude")
):
    dummy = True
    print(f"🔍 DEBUG: dummy parameter = {dummy}, type = {type(dummy)}")
    
    # Return dummy data for UI testing
    if dummy:
        await asyncio.sleep(5)
        print("🧪 Returning dummy data for UI testing")
        return get_dummy_pois()
    
    print("🚀 Proceeding with real API calls...")
    
    if lat and lon:
        user_lat, user_lon = lat, lon
    else:
        user_lat, user_lon = get_user_location()
    
    # Get location details from coordinates
    location_details = get_location_details(user_lat, user_lon)
    city = location_details["city"]
    province = location_details["province"]
    country = location_details["country"]
    
    all_pois = []
    
    # Get Reddit POIs
    reddit_pois = await get_reddit_pois(city, province, country, user_lat, user_lon)
    all_pois.extend(reddit_pois)
    
    # Get News POIs using the new service structure
    print(f"🗞️ Fetching news for {city}, {province}, {country}")
    try:
        # news_pois = get_news_pois(city, province, country, user_lat, user_lon)  # TEMPORARILY DISABLED (API token limit)
        news_pois = []  # Empty list for now
        print(f"✅ News API temporarily disabled (API token limit)")
        all_pois.extend(news_pois)  # Add news POIs to the list
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
    
    print(f"Returning {len(all_pois)} total POIs (Reddit + News)")
    return all_pois

