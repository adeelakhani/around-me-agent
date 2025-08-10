# backend/routes/locations.py
from fastapi import APIRouter, Query
from reddit.service import get_reddit_pois
from agents.news_scraper import get_news_for_city
from utils.location import get_user_location, get_location_details
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
    
    # Get location details from coordinates
    location_details = get_location_details(user_lat, user_lon)
    city = location_details["city"]
    province = location_details["province"]
    country = location_details["country"]
    
    all_pois = []
    
    # Get Reddit POIs
    reddit_pois = get_reddit_pois(city, province, country, user_lat, user_lon)
    all_pois.extend(reddit_pois)
    
    # Also get news POIs for the same location
    print(f"🗞️ Fetching news for {city}, {province}, {country}")
    try:
        news_pois = get_news_for_city(city, province, country, user_lat, user_lon)
        print(f"✅ Found {len(news_pois)} news POIs")
        all_pois.extend(news_pois)  # Add news POIs to the list
    except Exception as e:
        print(f"❌ Error fetching news: {e}")
    
    print(f"Returning {len(all_pois)} total POIs (Reddit + News)")
    return all_pois

