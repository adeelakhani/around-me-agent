# backend/routes/locations.py
from fastapi import APIRouter, Query
from scrapers.reddit import scrape_reddit_local
from scrapers.weather import get_weather_data
from scrapers.events import get_local_events
from scrapers.news import get_local_news
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
    #     return [
    #     {
    #         "lat": 43.6532,
    #         "lng": -79.3832,
    #         "name": "Weather - Toronto",
    #         "summary": "Perfect sunny day! 22°C, great for outdoor activities. Humidity: 45%. Location: Toronto",
    #         "type": "weather",
    #         "radius": 20
    #     },
    #     {
    #         "lat": 43.6632,
    #         "lng": -79.3932,
    #         "name": "Event - Farmers Market",
    #         "summary": "Event: Farmers Market. Time: Today 10AM-4PM. Venue: Downtown Park. Location: Toronto",
    #         "type": "event",
    #         "radius": 20
    #     },
    #     {
    #         "lat": 43.6432,
    #         "lng": -79.3732,
    #         "name": "News - New Restaurant Opens",
    #         "summary": "News: New Restaurant Opens Downtown. Local favorite expands to downtown location. Published: 2024-01-15. Location: Toronto",
    #         "type": "news",
    #         "radius": 20
    #     },
    #     {
    #         "lat": 43.6732,
    #         "lng": -79.3632,
    #         "name": "Reddit - Coffee Shop Review",
    #         "summary": "Reddit: Best coffee shop in the area. From: r/toronto. Location: Toronto",
    #         "type": "reddit",
    #         "radius": 20
    #     }
    # ]
    if lat and lon:
        user_lat, user_lon = lat, lon
    else:
        user_lat, user_lon = get_user_location()
    
    print(f"🔍 Fetching Reddit data for coordinates: {user_lat}, {user_lon}")
    
    # Step 1: Get real Reddit data
    try:
        print("🚀 Starting Reddit scraping...")
        reddit_posts = await scrape_reddit_local()
        print(f"📱 Found {len(reddit_posts)} Reddit posts")
        
        if len(reddit_posts) == 0:
            print("⚠️ No Reddit posts found, using fallback data")
            return [
                {
                    "lat": 43.6532,
                    "lng": -79.3832,
                    "name": "Reddit - No posts found",
                    "summary": "No Reddit posts found for this location. Try again later.",
                    "type": "reddit",
                    "radius": 20
                }
            ]
        
        # Step 2: Create LangGraph agent
        print("🤖 Creating LangGraph agent...")
        agent = create_summarizer_agent()
        
        # Step 3: Process each Reddit post through LangGraph
        location_summaries = []
        
        for i, post in enumerate(reddit_posts[:4]):  # Limit to 4 posts for demo
            print(f"🤖 Processing Reddit post {i+1}: {post.get('title', 'No title')[:50]}...")
            
            # Create location data for this post
            location_data = {
                "name": f"Reddit Post {i+1}",
                "type": "reddit",
                "lat": user_lat + (i * 0.01),  # Spread posts around the area
                "lng": user_lon + (i * 0.01),
                "data": post  # The actual Reddit post data
            }
            
            # Step 4: Run LangGraph agent with real data
            initial_state = {
                "messages": [],
                "location_data": location_data,
                "reddit_data": reddit_posts,  # All Reddit data
                "weather_data": {},  # Empty for now
                "events_data": [],
                "news_data": [],
                "summary": None
            }
            
            # This is where LangGraph processes the data!
            result = agent.invoke(initial_state)
            
            print(f"✅ LangGraph generated summary: {result.get('summary', 'No summary')[:100]}...")
            
            # Step 5: Create location object with AI summary
            location_summaries.append({
                "lat": location_data["lat"],
                "lng": location_data["lng"],
                "name": f"Reddit - {post.get('source', 'Unknown')}",
                "summary": result.get("summary", "No summary available"),
                "type": "reddit",
                "radius": 20
            })
        
        print(f"🎉 Returning {len(location_summaries)} Reddit locations with AI summaries")
        return location_summaries
        
    except Exception as e:
        print(f"❌ Error fetching Reddit data: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to dummy data if Reddit fails
        return [
            {
                "lat": 43.6532,
                "lng": -79.3832,
                "name": "Reddit - Error occurred",
                "summary": f"Error fetching Reddit data: {str(e)}",
                "type": "reddit",
                "radius": 20
            }
        ]

@router.get("/test-reddit")
async def test_reddit_scraping():
    """Test endpoint to debug Reddit scraping"""
    try:
        print("🧪 Testing Reddit scraping...")
        reddit_posts = await scrape_reddit_local()
        return {
            "success": True,
            "posts_found": len(reddit_posts),
            "posts": reddit_posts[:3]  # Return first 3 posts
        }
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "posts": []
        }

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