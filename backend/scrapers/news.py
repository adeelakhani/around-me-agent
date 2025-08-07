import requests
import os
from utils.location import get_location_name, get_user_location

def get_local_news():
    lat, lon = get_user_location()
    location_name = get_location_name(lat, lon)
    api_key = os.getenv("NEWS_API_KEY")
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": location_name,
        "apiKey": api_key,
        "sortBy": "publishedAt",
        "pageSize": 10
    }
    response = requests.get(url, params=params)
    return response.json()