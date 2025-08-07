# backend/routes/locations.py
from fastapi import APIRouter, Query
from agents.summarizer import create_summarizer_agent
from utils.location import get_user_location, get_radius_coordinates, get_location_name
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
    
    print(f"Starting LangGraph agent for coordinates: {user_lat}, {user_lon}")
    
    # Create LangGraph agent with Playwright tools
    agent = create_summarizer_agent()
    
    # Create location data for Reddit scraping
    location_data = {
        "name": "Toronto",
        "type": "reddit",
        "lat": user_lat,
        "lng": user_lon,
        "data": {}
    }
    
    # Run LangGraph agent to scrape and summarize Reddit data
    initial_state = {
        "messages": [],
        "location_data": location_data,
        "reddit_data": [],
        "weather_data": {},
        "events_data": [],
        "news_data": [],
        "summary": None,
        "current_step": "start"
    }
    
    print("Invoking LangGraph agent...")
    try:
        result = agent.invoke(initial_state, config={"recursion_limit": 50})
        print(f"LangGraph result keys: {list(result.keys())}")
        print(f"LangGraph messages count: {len(result.get('messages', []))}")
        
        # Check if we got a meaningful summary
        summary = result.get("summary", "")
        print(f"Raw summary: {summary}")
        
        if not summary or "error" in summary.lower() or "no summary" in summary.lower():
            print("No meaningful summary found, using fallback")
            summary = "Recent local posts from r/toronto show community discussions about local events, restaurants, and city updates. Check out the latest posts for what's happening in Toronto!"
        
    except Exception as e:
        print(f"LangGraph error: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to simple response
        summary = "Local Reddit community is active with discussions about Toronto events, restaurants, and city life. Check r/toronto for the latest local updates!"
    
    # Create location objects with AI summaries
    location_summaries = []
    
    # Create multiple locations around the center point
    for i in range(4):
        location_summaries.append({
            "lat": user_lat + (i * 0.01),
            "lng": user_lon + (i * 0.01),
            "name": f"Reddit - Toronto Local {i+1}",
            "summary": summary,
            "type": "reddit",
            "radius": 20
        })
    
    print(f"Returning {len(location_summaries)} locations with summary: {summary[:100]}...")
    return location_summaries

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