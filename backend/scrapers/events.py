import requests
import os
from utils.location import get_user_location

def get_local_events():
    lat, lon = get_user_location()
    api_key = os.getenv("EVENTBRITE_API_KEY")
    url = "https://www.eventbriteapi.com/v3/events/search/"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "location.latitude": lat,
        "location.longitude": lon,
        "location.within": "20km" 
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json()