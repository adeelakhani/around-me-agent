"""
311 Service Module

Handles fetching and processing data from municipal 311 APIs.
Converts 311 data into POI format for integration with the main app.
"""

import os
import time
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
from utils.location import get_location_details

from .discovery import discover_311_endpoint
from .fetcher import fetch_data_from_endpoint
from .parser import parse_data_into_pois

load_dotenv(override=True)

def get_311_pois(city: str, province: str, country: str, user_lat: float, user_lon: float, max_pois: int = 25) -> List[Dict[str, Any]]:
    """
    Get 311 service requests as POIs.
    
    This function follows a clear procedural approach:
    1. Log the start of the process
    2. Discover the API endpoint
    3. Fetch data from the endpoint
    4. Parse the data into POIs
    5. Return the results
    """
    
    print(f"Starting 311 API for coordinates: {user_lat}, {user_lon} in {city}, {province}, {country}")
    
    timestamp = int(time.time())
    print(f"=== USING 311 MUNICIPAL API ===")
    print(f"City: {city}")
    print(f"Province: {province}")
    print(f"Country: {country}")
    print(f"Timestamp: {timestamp}")
    print("=" * 50)
    
    try:
        pois = []
        
        print(f"Fetching 311 data for {city}, {province}, {country}")
        api_endpoint = discover_311_endpoint(city, province, country)
        
        if not api_endpoint:
            print(f"No 311 API found for {city}, {province}, {country}")
            return []
        
        raw_data = fetch_data_from_endpoint(api_endpoint)
        
        if not raw_data:
            print("Failed to fetch data from API endpoint")
            return []
        
        pois = parse_data_into_pois(raw_data, city, province, country, max_pois, user_lat, user_lon)
        
        if pois:
            print(f"=== FOUND {len(pois)} 311 POIs ===")
            for i, poi in enumerate(pois, 1):
                print(f"311 POI {i}: {poi['name']} at {poi['lat']}, {poi['lng']}")
                print(f"Type: {poi['type']}")
                print(f"Summary: {poi['summary'][:100]}...")
                print("-" * 30)
        else:
            print("No 311 POIs found")
            
        return pois
        
    except Exception as e:
        print(f"311 API error: {e}")
        import traceback
        traceback.print_exc()
        return []






