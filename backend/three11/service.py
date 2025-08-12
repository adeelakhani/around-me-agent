"""
311 Service Module

Handles fetching and processing data from municipal 311 APIs.
Converts 311 data into POI format for integration with the main app.
"""

import requests
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import time
from utils.location import get_location_details
from agents.municipal_api_discovery import discover_municipal_api_endpoint

load_dotenv(override=True)

def get_311_pois(city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
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
        
        city_pois = fetch_city_311_data(city, province, country, user_lat, user_lon)
        pois.extend(city_pois)
        
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

def fetch_city_311_data(city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching 311 data for {city}, {province}, {country}")
    
    try:
        api_endpoint = discover_municipal_api_endpoint(city, province, country)
        
        if api_endpoint:
            return fetch_from_api_endpoint(api_endpoint, city, province, country, user_lat, user_lon)
        else:
            return fetch_generic_311_data(city, province, country, user_lat, user_lon)
            
    except Exception as e:
        print(f"Error fetching 311 data for {city}: {e}")
        return []



def fetch_from_api_endpoint(endpoint: str, city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching from API endpoint: {endpoint}")
    
    try:
        response = requests.get(endpoint, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"API response: {data}")
        
        pois = []
        
        if isinstance(data, dict):
            if "service_requests" in data:
                for request in data["service_requests"][:5]:
                    if "lat" in request and "long" in request:
                        poi = {
                            "name": request.get("service_name", f"{city} Service Request"),
                            "lat": float(request["lat"]),
                            "lng": float(request["long"]),
                            "type": "311_service",
                            "summary": request.get("description", f"City service request in {city}"),
                            "source": "311_api",
                            "status": request.get("status", "unknown")
                        }
                        pois.append(poi)
            elif "service_definitions" in data:
                for service in data["service_definitions"][:5]:
                    poi = {
                        "name": service.get("service_name", f"{city} Service"),
                        "lat": user_lat + (0.001 * len(pois)),
                        "lng": user_lon + (0.001 * len(pois)),
                        "type": "311_service",
                        "summary": service.get("description", f"City service available in {city}"),
                        "source": "311_api",
                        "status": "available"
                    }
                    pois.append(poi)
        elif isinstance(data, list):
            for item in data[:5]:
                if "latitude" in item and "longitude" in item:
                    poi = {
                        "name": item.get("complaint_type", f"{city} Service Request"),
                        "lat": float(item["latitude"]),
                        "lng": float(item["longitude"]),
                        "type": "311_service",
                        "summary": item.get("descriptor", f"City service request in {city}"),
                        "source": "311_api",
                        "status": item.get("status", "unknown")
                    }
                    pois.append(poi)
        
        return pois
        
    except Exception as e:
        print(f"Error fetching from API endpoint: {e}")
        return []

def fetch_canada_311_data(city: str, province: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching Canadian 311 data for {city}, {province}")
    
    try:
        if city.lower() == "toronto" and province.lower() == "ontario":
            url = "https://secure.toronto.ca/open311/v2/services.json"
        elif city.lower() == "vancouver" and province.lower() == "british columbia":
            url = "https://opendata.vancouver.ca/api/v1/311-requests"
        elif city.lower() == "montreal" and province.lower() == "quebec":
            url = "https://donnees.montreal.ca/api/311-requests"
        else:
            return fetch_generic_canada_311_data(city, province, user_lat, user_lon)
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"Canadian 311 API response: {data}")
        
        pois = []
        if "service_definitions" in data:
            for service in data["service_definitions"][:5]:
                poi = {
                    "name": service.get("service_name", f"{city} Service"),
                    "lat": user_lat + (0.001 * len(pois)),
                    "lng": user_lon + (0.001 * len(pois)),
                    "type": "311_service",
                    "summary": service.get("description", f"City service available in {city}"),
                    "source": "311_api",
                    "status": "available"
                }
                pois.append(poi)
        
        return pois
        
    except Exception as e:
        print(f"Canadian 311 API error: {e}")
        return []

def fetch_usa_311_data(city: str, province: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching USA 311 data for {city}, {province}")
    
    try:
        if city.lower() == "new york" and province.lower() == "new york":
            url = "https://data.cityofnewyork.us/resource/v6wi-cqs5.json"
            params = {"$limit": 5}
        elif city.lower() == "san francisco" and province.lower() == "california":
            url = "https://open311.sfgov.org/dev/v2/services.json"
            params = {}
        elif city.lower() == "chicago" and province.lower() == "illinois":
            url = "https://data.cityofchicago.org/resource/v6wi-cqs5.json"
            params = {"$limit": 5}
        else:
            return fetch_generic_usa_311_data(city, province, user_lat, user_lon)
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"USA 311 API response: {data}")
        
        pois = []
        if isinstance(data, list):
            for item in data[:5]:
                if "latitude" in item and "longitude" in item:
                    poi = {
                        "name": item.get("complaint_type", f"{city} Service Request"),
                        "lat": float(item["latitude"]),
                        "lng": float(item["longitude"]),
                        "type": "311_service",
                        "summary": item.get("descriptor", f"City service request in {city}"),
                        "source": "311_api",
                        "status": item.get("status", "unknown")
                    }
                    pois.append(poi)
        
        return pois
        
    except Exception as e:
        print(f"USA 311 API error: {e}")
        return []

def fetch_generic_311_data(city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching generic 311 data for {city}, {province}, {country}")
    
    try:
        pois = []
        for i in range(3):
            poi = {
                "name": f"{city} Municipal Service {i+1}",
                "lat": user_lat + (0.001 * i),
                "lng": user_lon + (0.001 * i),
                "type": "311_service",
                "summary": f"Municipal service available in {city}, {province}",
                "source": "311_api",
                "status": "available"
            }
            pois.append(poi)
        
        return pois
        
    except Exception as e:
        print(f"Generic 311 API error: {e}")
        return []

def fetch_generic_canada_311_data(city: str, province: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching generic Canadian 311 data for {city}, {province}")
    
    try:
        pois = []
        for i in range(3):
            poi = {
                "name": f"{city} Municipal Service {i+1}",
                "lat": user_lat + (0.001 * i),
                "lng": user_lon + (0.001 * i),
                "type": "311_service",
                "summary": f"Canadian municipal service in {city}, {province}",
                "source": "311_api",
                "status": "available"
            }
            pois.append(poi)
        
        return pois
        
    except Exception as e:
        print(f"Generic Canadian 311 API error: {e}")
        return []

def fetch_generic_usa_311_data(city: str, province: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching generic USA 311 data for {city}, {province}")
    
    try:
        pois = []
        for i in range(3):
            poi = {
                "name": f"{city} Municipal Service {i+1}",
                "lat": user_lat + (0.001 * i),
                "lng": user_lon + (0.001 * i),
                "type": "311_service",
                "summary": f"USA municipal service in {city}, {province}",
                "source": "311_api",
                "status": "available"
            }
            pois.append(poi)
        
        return pois
        
    except Exception as e:
        print(f"Generic USA 311 API error: {e}")
        return []
