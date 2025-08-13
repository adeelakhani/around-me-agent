import requests
import os
import time
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv(override=True)

def get_events_pois(city: str, province: str, country: str, user_lat: float, user_lon: float, max_pois: int = 15) -> List[Dict[str, Any]]:
    """Get Events POIs for a location using Ticketmaster Discovery API"""
    print(f"Starting Ticketmaster API for coordinates: {user_lat}, {user_lon} in {city}, {province}, {country}")
    
    timestamp = int(time.time())
    print(f"=== USING TICKETMASTER DISCOVERY API ===")
    print(f"City: {city}")
    print(f"Province: {province}")
    print(f"Country: {country}")
    print(f"Timestamp: {timestamp}")
    print("=" * 50)
    
    try:
        ticketmaster_key = os.getenv("TICKETMASTER_API_KEY")
        if not ticketmaster_key:
            print("TICKETMASTER_API_KEY not found in environment variables")
            return []
        
        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        
        from datetime import datetime, timedelta
        
        now = datetime.now()
        start_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_date = (now + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        params = {
            "apikey": ticketmaster_key,
            "latlong": f"{user_lat},{user_lon}",
            "radius": "30",
            "unit": "miles",
            "size": max_pois,
            "sort": "date,asc",
            "startDateTime": start_date,
            "endDateTime": end_date
        }
        
        print(f"Making request to Ticketmaster API with params: {params}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
        data = response.json()
        events = data.get("_embedded", {}).get("events", [])
        
        print(f"Received {len(events)} events from Ticketmaster API")
        
        event_pois = []
        for event in events:
            try:
                venues = event.get("_embedded", {}).get("venues", [])
                if not venues:
                    print(f"Skipping event '{event.get('name', 'Unknown')}' - no venue information")
                    continue
                
                venue = venues[0]
                location = venue.get("location", {})
                
                lat = location.get("latitude")
                lng = location.get("longitude")
                
                if not lat or not lng:
                    print(f"Skipping event '{event.get('name', 'Unknown')}' - no coordinates")
                    continue
                
                event_name = event.get("name", "Unknown Event")
                event_description = event.get("info", "")
                
                dates = event.get("dates", {})
                start_date = dates.get("start", {}).get("localDate", "")
                start_time = dates.get("start", {}).get("localTime", "")
                
                venue_address = venue.get("address", {})
                venue_city = venue_address.get("city", {}).get("name", "")
                venue_state = venue_address.get("state", {}).get("name", "")
                venue_address_line = venue_address.get("line1", "")
                
                summary = f"Event: {event_name}\n"
                if venue_address_line:
                    summary += f"Location: {venue_address_line}\n"
                if venue_city and venue_state:
                    summary += f"City: {venue_city}, {venue_state}\n"
                if start_date:
                    date_time = f"{start_date}"
                    if start_time:
                        date_time += f" at {start_time}"
                    summary += f"Date: {date_time}\n"
                if event_description:
                    desc_preview = event_description[:500] + "..." if len(event_description) > 500 else event_description
                    summary += f"Description: {desc_preview}"
                
                poi = {
                    "name": event_name,
                    "lat": float(lat),
                    "lng": float(lng),
                    "summary": summary,
                    "type": "event",
                    "radius": 0.1,
                    "source": "ticketmaster",
                    "url": event.get("url", ""),
                    "start_date": start_date
                }
                
                event_pois.append(poi)
                print(f"Added event: {event_name} at {lat}, {lng}")
                
            except Exception as e:
                print(f"Error processing event: {e}")
                continue
        
        if event_pois:
            print(f"=== FOUND {len(event_pois)} EVENT POIs ===")
            for i, poi in enumerate(event_pois, 1):
                print(f"Event POI {i}: {poi['name']} at {poi['lat']}, {poi['lng']}")
                print(f"Summary: {poi['summary'][:100]}...")
                print(f"Type: {poi['type']}")
                print("-" * 30)
        else:
            print("No event POIs found")
            
        return event_pois
        
    except requests.exceptions.RequestException as e:
        print(f"Ticketmaster API request error: {e}")
        return []
    except Exception as e:
        print(f"Ticketmaster API error: {e}")
        import traceback
        traceback.print_exc()
        return []
