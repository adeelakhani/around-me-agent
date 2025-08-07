# backend/routes/locations.py
from fastapi import APIRouter, Query
from scrapers.reddit import scrape_reddit_local
from scrapers.weather import get_weather_data
from scrapers.events import get_local_events
from scrapers.news import get_local_news
from agents.summarizer import create_summarizer_agent
from utils.location import get_user_location, get_radius_coordinates, get_location_name

router = APIRouter()

@router.get("/locations")
async def get_locations(
    lat: float = Query(None, description="User latitude"),
    lon: float = Query(None, description="User longitude")
):
    return [
        {
            "lat": 43.6532,
            "lng": -79.3832,
            "name": "Weather - Toronto",
            "summary": "Perfect sunny day! 22°C, great for outdoor activities. Humidity: 45%. Location: Toronto",
            "type": "weather",
            "radius": 20
        },
        {
            "lat": 43.6632,
            "lng": -79.3932,
            "name": "Event - Farmers Market",
            "summary": "Event: Farmers Market. Time: Today 10AM-4PM. Venue: Downtown Park. Location: Toronto",
            "type": "event",
            "radius": 20
        },
        {
            "lat": 43.6432,
            "lng": -79.3732,
            "name": "News - New Restaurant Opens",
            "summary": "News: New Restaurant Opens Downtown. Local favorite expands to downtown location. Published: 2024-01-15. Location: Toronto",
            "type": "news",
            "radius": 20
        },
        {
            "lat": 43.6732,
            "lng": -79.3632,
            "name": "Reddit - Coffee Shop Review",
            "summary": "Reddit: Best coffee shop in the area. From: r/toronto. Location: Toronto",
            "type": "reddit",
            "radius": 20
        }
    ]

@router.get("/user-location")
async def get_user_location_endpoint():
    lat, lon = get_user_location()
    radius_coords = get_radius_coordinates(lat, lon, 20)
    return {
        "lat": lat,
        "lon": lon,
        "radius_km": 20,
        "bounding_box": radius_coords
    }