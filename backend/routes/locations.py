from fastapi import APIRouter, Query
from reddit.service import get_reddit_pois
from news.service import get_news_pois
from events.service import get_events_pois
from utils.location import get_location_details
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
        user_lat, user_lon = 43.6532, -79.3832  # Toronto fallback
    
    location_details = get_location_details(user_lat, user_lon)
    city = location_details["city"]
    province = location_details["province"]
    country = location_details["country"]
    
    all_pois = []
    
    # # Reddit POIs
    # try:
    #     reddit_pois = await get_reddit_pois(city, province, country, user_lat, user_lon)
    #     all_pois.extend(reddit_pois)
    # except Exception as e:
    #     print(f"Error fetching Reddit data: {e}")
        

    # News POIs
    # print(f"🗞️ Fetching news for {city}, {province}, {country}")
    # try:
    #     news_pois = get_news_pois(city, province, country, user_lat, user_lon)
    #     all_pois.extend(news_pois)  # Add news POIs to the list
    # except Exception as e:
    #     print(f"❌ Error fetching news: {e}")
    
    # # 311 POIs
    # print(f"Fetching 311 data for {city}, {province}, {country}")
    # try:
    #     three11_pois = get_311_pois(city, province, country, user_lat, user_lon, max_pois=15)
    #     all_pois.extend(three11_pois)
    # except Exception as e:
    #     print(f"Error fetching 311 data: {e}")
    
    # try:
    #     events_pois = get_events_pois(city, province, country, user_lat, user_lon, max_pois=15)
    #     all_pois.extend(events_pois)
    # except Exception as e:
    #     print(f"Error fetching events data: {e}")
    
    # ------------------------------------------------------------
    import time
    import random
    
    print("🔄 Adding dummy test data...")
    time.sleep(3)  # 5-second timeout
    
    # Dummy Reddit POIs
    reddit_pois = [
        {
            "name": "Best Coffee Shop in Downtown",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Reddit users love this hidden gem! Great coffee and atmosphere. Posted by u/coffeelover123",
            "type": "reddit",
            "radius": 0.1,
            "source": "reddit"
        },
        {
            "name": "Amazing Pizza Place",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Best pizza in the area according to r/toronto. Authentic Italian style!",
            "type": "reddit",
            "radius": 0.1,
            "source": "reddit"
        },
        {
            "name": "Secret Park Discovery",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Hidden park that locals know about. Perfect for picnics!",
            "type": "reddit",
            "radius": 0.1,
            "source": "reddit"
        },
        {
            "name": "Local Brewery Tour",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Great craft beer and friendly staff. Highly recommended!",
            "type": "reddit",
            "radius": 0.1,
            "source": "reddit"
        },
        {
            "name": "Street Art Walking Tour",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Amazing murals and street art in this neighborhood. Instagram worthy!",
            "type": "reddit",
            "radius": 0.1,
            "source": "reddit"
        }
    ]
    
    # Dummy News POIs
    news_pois = [
        {
            "name": "New Restaurant Opening",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Breaking news from Toronto Star: New fusion restaurant opening this weekend. Expected to be a hit!",
            "type": "news",
            "radius": 0.1,
            "source": "Toronto Star",
            "date": "2025-08-12"
        },
        {
            "name": "Community Festival Announcement",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Breaking news from CBC: Annual street festival returning next month with live music and food trucks.",
            "type": "news",
            "radius": 0.1,
            "source": "CBC",
            "date": "2025-08-12"
        },
        {
            "name": "Park Renovation Project",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Breaking news from Globe and Mail: Local park getting major renovation with new playground and walking trails.",
            "type": "news",
            "radius": 0.1,
            "source": "Globe and Mail",
            "date": "2025-08-12"
        },
        {
            "name": "Art Gallery Exhibition",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Breaking news from Toronto Life: New contemporary art exhibition featuring local artists opens this week.",
            "type": "news",
            "radius": 0.1,
            "source": "Toronto Life",
            "date": "2025-08-12"
        },
        {
            "name": "Transit Improvement News",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Breaking news from CP24: New bus routes being added to improve connectivity in the downtown area.",
            "type": "news",
            "radius": 0.1,
            "source": "CP24",
            "date": "2025-08-12"
        }
    ]
    
    # Dummy 311 POIs
    three11_pois = [
        {
            "name": "Street Light Repair",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Street Light Repair. Division: Transportation Services. Section: Street Lighting. Status: In Progress. Location: Downtown",
            "type": "311_service",
            "radius": 0.1,
            "source": "311_csv",
            "creation_date": "2025-08-12 10:30:00"
        },
        {
            "name": "Pothole Repair",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Pothole Repair. Division: Transportation Services. Section: Road Operations. Status: New. Location: Main Street",
            "type": "311_service",
            "radius": 0.1,
            "source": "311_csv",
            "creation_date": "2025-08-12 09:15:00"
        },
        {
            "name": "Garbage Collection Issue",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Garbage Collection Issue. Division: Solid Waste Management. Section: Collections. Status: Completed. Location: Residential Area",
            "type": "311_service",
            "radius": 0.1,
            "source": "311_csv",
            "creation_date": "2025-08-12 08:45:00"
        },
        {
            "name": "Tree Maintenance",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Tree Maintenance. Division: Parks and Recreation. Section: Urban Forestry. Status: Scheduled. Location: Park Area",
            "type": "311_service",
            "radius": 0.1,
            "source": "311_csv",
            "creation_date": "2025-08-12 11:20:00"
        },
        {
            "name": "Traffic Signal Problem",
            "lat": user_lat + random.uniform(-0.01, 0.01),
            "lng": user_lon + random.uniform(-0.01, 0.01),
            "summary": "Traffic Signal Problem. Division: Transportation Services. Section: Traffic Operations. Status: In Progress. Location: Intersection",
            "type": "311_service",
            "radius": 0.1,
            "source": "311_csv",
            "creation_date": "2025-08-12 12:00:00"
        }
    ]
    
    # Add all dummy data
    all_pois.extend(reddit_pois)
    all_pois.extend(news_pois)
    all_pois.extend(three11_pois)
    
    # Add real events data
    try:
        events_pois = get_events_pois(city, province, country, user_lat, user_lon, max_pois=15)
        all_pois.extend(events_pois)
    except Exception as e:
        print(f"Error fetching events data: {e}")
        # ------------------------------------------------------------

    print(f"Returning {len(all_pois)} total POIs (Reddit + News + 311 + Events)")
    return all_pois

