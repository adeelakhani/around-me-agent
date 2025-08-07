# backend/routes/locations.py
from fastapi import APIRouter, Query
from scrapers.reddit import scrape_reddit_local
from scrapers.weather import get_weather_data
from scrapers.events import get_local_events
from scrapers.news import get_local_news
from agents.summarizer import create_summarizer_agent
from utils.location import get_user_location, get_radius_coordinates
import asyncio

router = APIRouter()

@router.get("/api/locations")
async def get_locations(
    lat: float = Query(None, description="User latitude"),
    lon: float = Query(None, description="User longitude")
):
    if lat and lon:
        user_lat, user_lon = lat, lon
    else:
        user_lat, user_lon = get_user_location()
    
    radius_coords = get_radius_coordinates(user_lat, user_lon, 30)
    
    reddit_data = await scrape_reddit_local()
    weather_data = get_weather_data()
    events_data = get_local_events()
    news_data = get_local_news()
    
    agent = create_summarizer_agent()
    result = agent.invoke({
        "reddit_data": reddit_data,
        "weather_data": weather_data,
        "events_data": events_data,
        "news_data": news_data,
        "location": {"lat": user_lat, "lon": user_lon}
    })
    
    return [
        {
            "lat": user_lat,
            "lng": user_lon,
            "summary": result["summary"],
            "type": "local_data",
            "radius": 30
        },
        {
            "lat": user_lat + 0.1, 
            "lng": user_lon + 0.1,
            "summary": "Additional local insights",
            "type": "nearby_data",
            "radius": 30
        }
    ]

@router.get("/api/user-location")
async def get_user_location_endpoint():
    lat, lon = get_user_location()
    radius_coords = get_radius_coordinates(lat, lon, 30)
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": 30,
        "bounding_box": radius_coords
    }