"""
311 Service Module

Handles fetching and processing data from municipal 311 APIs.
Converts 311 data into POI format for integration with the main app.
"""

import requests
import os
import zipfile
import io
import csv
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import time
from utils.location import get_location_details
from agents.municipal_api_discovery import discover_municipal_api_endpoint

load_dotenv(override=True)

def interpret_311_location_with_llm(service_data: Dict[str, Any], city: str, province: str, country: str) -> Optional[Tuple[float, float]]:
    """
    Use LLM to interpret location information from 311 data and generate coordinates.
    
    Args:
        service_data: Dictionary containing 311 service request data
        city: City name
        province: Province/state name
        country: Country name
        
    Returns:
        Tuple of (latitude, longitude) if successful, None otherwise
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
        
        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4o-mini")
        
        # Extract location information from the service data
        postal_code = service_data.get('postal_code', '')
        intersection1 = service_data.get('intersection1', '')
        intersection2 = service_data.get('intersection2', '')
        ward = service_data.get('ward', '')
        service_type = service_data.get('service_type', '')
        
        # Build location description
        location_parts = []
        if ward:
            location_parts.append(f"Ward: {ward}")
        if postal_code:
            location_parts.append(f"Postal Code: {postal_code}")
        if intersection1 and intersection2:
            location_parts.append(f"Intersection: {intersection1} & {intersection2}")
        elif intersection1:
            location_parts.append(f"Street: {intersection1}")
        
        location_description = ', '.join(location_parts) if location_parts else "General area"
        
        # Create prompt for LLM
        system_prompt = """You are a location interpretation specialist for municipal 311 service requests. 
Your task is to analyze location information from 311 data and provide approximate coordinates.

Given the location information, you should:
1. Use your knowledge of the city's geography and postal code areas
2. Consider the ward boundaries and typical locations for different service types
3. Provide realistic coordinates within the city limits
4. If you can't determine a specific location, provide coordinates for the general area

Return ONLY the coordinates in the format: "latitude,longitude" (e.g., "43.6548,-79.3883")
If you cannot determine coordinates, return "UNKNOWN"."""

        user_prompt = f"""Analyze this 311 service request location and provide approximate coordinates:

City: {city}, {province}, {country}
Service Type: {service_type}
Location Information: {location_description}

Based on this information, what would be the approximate latitude and longitude coordinates for this location?

Return ONLY the coordinates in format "latitude,longitude" or "UNKNOWN" if you cannot determine."""

        # Get LLM response
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        response_text = response.content.strip()
        print(f"🤖 LLM location interpretation: {response_text}")
        
        # Parse coordinates
        if response_text.upper() != "UNKNOWN":
            try:
                # Handle different response formats
                if ',' in response_text:
                    coords = response_text.split(',')
                    if len(coords) == 2:
                        lat = float(coords[0].strip())
                        lng = float(coords[1].strip())
                        
                        # Validate coordinates are reasonable for the city
                        if is_valid_coordinates_for_city(lat, lng, city, province, country):
                            print(f"✅ LLM generated coordinates: {lat}, {lng}")
                            return (lat, lng)
                        else:
                            print(f"❌ LLM coordinates outside reasonable range for {city}")
                            return None
            except ValueError as e:
                print(f"❌ Error parsing LLM coordinates: {e}")
                return None
        
        print(f"❌ LLM could not determine coordinates for this location")
        return None
        
    except Exception as e:
        print(f"❌ Error in LLM location interpretation: {e}")
        return None

def is_valid_coordinates_for_city(lat: float, lng: float, city: str, province: str, country: str) -> bool:
    """
    Validate if coordinates are within reasonable range for the city.
    
    Args:
        lat: Latitude
        lng: Longitude
        city: City name
        province: Province/state name
        country: Country name
        
    Returns:
        True if coordinates are reasonable for the city
    """
    # Define reasonable coordinate ranges for major cities
    city_bounds = {
        ("toronto", "ontario", "canada"): {
            "lat_min": 43.5, "lat_max": 43.9,
            "lng_min": -79.7, "lng_max": -79.1
        },
        ("vancouver", "british columbia", "canada"): {
            "lat_min": 49.1, "lat_max": 49.4,
            "lng_min": -123.3, "lng_max": -122.8
        },
        ("montreal", "quebec", "canada"): {
            "lat_min": 45.4, "lat_max": 45.7,
            "lng_min": -74.0, "lng_max": -73.4
        },
        ("new york", "new york", "usa"): {
            "lat_min": 40.4, "lat_max": 40.9,
            "lng_min": -74.3, "lng_max": -73.6
        },
        ("los angeles", "california", "usa"): {
            "lat_min": 33.6, "lat_max": 34.4,
            "lng_min": -118.7, "lng_max": -118.1
        }
    }
    
    city_key = (city.lower(), province.lower(), country.lower())
    
    if city_key in city_bounds:
        bounds = city_bounds[city_key]
        return (bounds["lat_min"] <= lat <= bounds["lat_max"] and 
                bounds["lng_min"] <= lng <= bounds["lng_max"])
    
    # For unknown cities, use a very broad range
    return -90 <= lat <= 90 and -180 <= lng <= 180

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
            print(f"No 311 API found for {city}, {province}, {country}")
            return []
            
    except Exception as e:
        print(f"Error fetching 311 data for {city}: {e}")
        return []



def fetch_from_api_endpoint(endpoint: str, city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    print(f"Fetching from API endpoint: {endpoint}")
    
    # Handle mock endpoints
    if endpoint.startswith("mock://"):
        print(f"Using mock 311 data for {city}")
        return fetch_mock_311_data(city, province, country, user_lat, user_lon)
    
    try:
        response = requests.get(endpoint, timeout=30)  # Increased timeout for large files
        response.raise_for_status()
        
        # Check if it's a ZIP file
        if endpoint.endswith('.zip') or 'application/zip' in response.headers.get('Content-Type', ''):
            print("Detected ZIP file, extracting CSV data...")
            return extract_zip_data(response.content, city, province, country, user_lat, user_lon)
        
        # Try to parse as JSON
        try:
            data = response.json()
            return parse_json_311_data(data, city, province, country, user_lat, user_lon)
        except:
            # If not JSON, try to parse as CSV
            print("Trying to parse as CSV...")
            return parse_csv_311_data(response.text, city, province, country, user_lat, user_lon)
        
    except Exception as e:
        print(f"Error fetching from API endpoint: {e}")
        # API failed
        print("API failed, no 311 data available")
        return []

def extract_zip_data(zip_content: bytes, city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    """Extract CSV data from ZIP file."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            # Look for CSV files in the ZIP
            csv_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
            
            if not csv_files:
                print("No CSV files found in ZIP")
                return []
            
            # Use the first CSV file
            csv_filename = csv_files[0]
            print(f"Extracting data from {csv_filename}")
            
            with zip_file.open(csv_filename) as csv_file:
                csv_content_bytes = csv_file.read()
                
                # Try different encodings
                encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                csv_content = None
                
                for encoding in encodings:
                    try:
                        csv_content = csv_content_bytes.decode(encoding)
                        print(f"Successfully decoded with {encoding} encoding")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if csv_content is None:
                    print("Failed to decode CSV with any encoding")
                    return []
                
                return parse_csv_311_data(csv_content, city, province, country, user_lat, user_lon)
                
    except Exception as e:
        print(f"Error extracting ZIP data: {e}")
        return []

def parse_csv_311_data(csv_content: str, city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    """Parse CSV data from 311 service requests."""
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        pois = []
        
        for i, row in enumerate(csv_reader):
            if i >= 25:  # Limit to 25 POIs
                break
                
            # Extract location data - try different possible column names
            lat = None
            lng = None
            
            # Try to find latitude/longitude columns
            for lat_col in ['latitude', 'lat', 'y', 'y_coordinate']:
                if lat_col in row and row[lat_col]:
                    try:
                        lat = float(row[lat_col])
                        break
                    except:
                        pass
            
            for lng_col in ['longitude', 'lng', 'long', 'x', 'x_coordinate']:
                if lng_col in row and row[lng_col]:
                    try:
                        lng = float(row[lng_col])
                        break
                    except:
                        pass
            
            # If no coordinates found, try to use LLM to interpret location information
            if lat is None or lng is None:
                # Extract location information for LLM interpretation
                postal_code = row.get('First 3 Chars of Postal Code', '')
                intersection1 = row.get('Intersection Street 1', '')
                intersection2 = row.get('Intersection Street 2', '')
                ward = row.get('Ward', '')
                service_type = row.get('Service Request Type', '')
                
                # Prepare service data for LLM interpretation
                service_data = {
                    'postal_code': postal_code,
                    'intersection1': intersection1,
                    'intersection2': intersection2,
                    'ward': ward,
                    'service_type': service_type
                }
                
                # Try to get coordinates from LLM interpretation
                llm_coords = interpret_311_location_with_llm(service_data, city, province, country)
                if llm_coords:
                    lat, lng = llm_coords
                    print(f"✅ Using LLM-generated coordinates: {lat}, {lng}")
                else:
                    # Fallback to user location with small offset
                    print(f"⚠️ LLM couldn't determine coordinates, using fallback location")
                    lat = user_lat + (0.001 * i)
                    lng = user_lon + (0.001 * i)
            
            # Extract service request information with better field mapping
            service_type = row.get('Service Request Type', row.get('original_service_request_type', 'Service Request'))
            status = row.get('Status', row.get('service_request_status', 'Unknown'))
            
            # Build location description
            location_parts = []
            if row.get('Ward'):
                location_parts.append(row['Ward'])
            if row.get('First 3 Chars of Postal Code'):
                location_parts.append(f"Postal Code: {row['First 3 Chars of Postal Code']}")
            if row.get('Intersection Street 1') and row.get('Intersection Street 2'):
                location_parts.append(f"{row['Intersection Street 1']} & {row['Intersection Street 2']}")
            elif row.get('Intersection Street 1'):
                location_parts.append(row['Intersection Street 1'])
            
            location = ', '.join(location_parts) if location_parts else f'{city}, {province}'
            
            # Build a more detailed summary
            summary_parts = [f"{service_type}"]
            if row.get('Division'):
                summary_parts.append(f"Division: {row['Division']}")
            if row.get('Section'):
                summary_parts.append(f"Section: {row['Section']}")
            summary_parts.append(f"Status: {status}")
            if location_parts:
                summary_parts.append(f"Location: {location}")
            
            summary = '. '.join(summary_parts)
            
            poi = {
                "name": f"{city} {service_type}",
                "lat": lat,
                "lng": lng,
                "type": "311_service",
                "summary": summary,
                "source": "311_csv",
                "status": status,
                "ward": row.get('Ward', ''),
                "postal_code": row.get('First 3 Chars of Postal Code', ''),
                "division": row.get('Division', ''),
                "section": row.get('Section', '')
            }
            pois.append(poi)
        
        if pois:
            print(f"Successfully parsed {len(pois)} 311 service requests from CSV")
            return pois
        else:
            print("No valid 311 data found in CSV")
            return []
            
    except Exception as e:
        print(f"Error parsing CSV data: {e}")
        return []

def parse_json_311_data(data: Any, city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    """Parse JSON data from 311 service requests."""
    pois = []
    
    if isinstance(data, dict):
        if "service_requests" in data:
            for request in data["service_requests"][:25]:
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
            for service in data["service_definitions"][:25]:
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
        for item in data[:25]:
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
            print(f"No Canadian 311 data available for {city}, {province}")
            return []
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"Canadian 311 API response: {data}")
        
        pois = []
        if "service_definitions" in data:
            for service in data["service_definitions"][:25]:
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
            params = {"$limit": 25}
        elif city.lower() == "san francisco" and province.lower() == "california":
            url = "https://open311.sfgov.org/dev/v2/services.json"
            params = {}
        elif city.lower() == "chicago" and province.lower() == "illinois":
            url = "https://data.cityofchicago.org/resource/v6wi-cqs5.json"
            params = {"$limit": 25}
        else:
            print(f"No USA 311 data available for {city}, {province}")
            return []
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"USA 311 API response: {data}")
        
        pois = []
        if isinstance(data, list):
            for item in data[:25]:
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


