# backend/routes/locations.py
from fastapi import APIRouter, Query
from reddit.service import get_reddit_pois
from news.service import get_news_pois
from utils.location import get_user_location, get_location_details
from three11.service import get_311_pois
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
    # try:
        # reddit_pois = await get_reddit_pois(city, province, country, user_lat, user_lon)
        # all_pois.extend(reddit_pois)
    # except Exception as e:
        # print(f"Error fetching Reddit data: {e}")
        

    # Get News POIs using the new service structure
    # print(f"🗞️ Fetching news for {city}, {province}, {country}")
    # try:
        # news_pois = get_news_pois(city, province, country, user_lat, user_lon)
        # all_pois.extend(news_pois)  # Add news POIs to the list
    # except Exception as e:
        # print(f"❌ Error fetching news: {e}")
    
    # print(f"Fetching 311 data for {city}, {province}, {country}")
    try:
        three11_pois = get_311_pois(city, province, country, user_lat, user_lon)
        all_pois.extend(three11_pois)
    except Exception as e:
        print(f"Error fetching 311 data: {e}")
    
    print(f"Returning {len(all_pois)} total POIs (Reddit + News + 311)")
    return all_pois

