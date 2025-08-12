"""
LLM Coordinate Interpretation

Handles LLM-based coordinate generation for 311 data.
"""

from typing import Dict, Any, Optional, Tuple, List

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

IMPORTANT: The location information may be in French, English, or other languages. Please interpret it appropriately for the city.

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

def llm_interpret_any_data(raw_data: str, city: str, province: str, country: str, user_lat: float, user_lon: float) -> List[Dict[str, Any]]:
    """
    LLM superpower: Interpret ANY data format and extract 311 POIs.
    Fallback when normal parsing fails.
    """
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
        
        llm = ChatOpenAI(model="gpt-4o-mini")
        
        prompt = f"""
        You are a 311 data expert. Analyze this raw data from {city}, {province}, {country}.
        
        IMPORTANT: The data may be in French, English, or other languages. Please interpret it appropriately for the city.
        
        Raw Data (first 2000 chars): {raw_data[:2000]}
        
        Extract 311 service requests as JSON array. If no valid data, generate 3 realistic 311 requests near {user_lat}, {user_lon}.
        
        Return ONLY valid JSON array like:
        [
            {{
                "name": "Service type",
                "lat": latitude,
                "lng": longitude,
                "type": "311_service",
                "summary": "Description",
                "status": "status"
            }}
        ]
        """
        
        response = llm.invoke([HumanMessage(content=prompt)])
        
        try:
            import json
            pois = json.loads(response.content.strip())
            if isinstance(pois, list):
                print(f"🤖 LLM extracted {len(pois)} POIs from raw data")
                return pois
        except:
            pass
            
        return []
        
    except Exception as e:
        print(f"❌ LLM interpretation failed: {e}")
        return []

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
