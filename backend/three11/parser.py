"""
311 Data Parser

Handles parsing of 311 data from different formats.
"""

import csv
import json
import io
from typing import List, Dict, Any, Optional, Tuple
from .llm_coordinates import interpret_311_location_with_llm, llm_interpret_any_data

def parse_csv_data(csv_content: str, city: str, province: str, country: str, max_pois: int = 25):
    """Parse CSV data from 311 service requests."""
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        pois = []
        
        # Convert to list to get total count and sample from different parts
        all_rows = list(csv_reader)
        total_rows = len(all_rows)
        
        if total_rows == 0:
            return []
        
        # For 311 data, we want the most recent information
        # Start from the end of the dataset and work backwards
        sample_indices = []
        if total_rows <= max_pois:
            # If dataset is small, take all rows (most recent first)
            sample_indices = list(range(total_rows - 1, -1, -1))  # Reverse order
        else:
            # Take the most recent rows from the end of the dataset
            start_idx = total_rows - 1
            end_idx = max(0, total_rows - max_pois)
            sample_indices = list(range(start_idx, end_idx, -1))  # Reverse order
        
        for i, row_idx in enumerate(sample_indices):
            if i >= max_pois:  # Limit to max_pois POIs
                break
                
            row = all_rows[row_idx]
                
            # Extract location data - try different possible column names
            lat = None
            lng = None
            
            # Try to find latitude/longitude columns (English and French)
            for lat_col in ['latitude', 'lat', 'y', 'y_coordinate', 'loc_lat', 'latitud', 'latitude_']:
                if lat_col in row and row[lat_col]:
                    try:
                        lat = float(row[lat_col])
                        break
                    except:
                        pass
            
            for lng_col in ['longitude', 'lng', 'long', 'x', 'x_coordinate', 'loc_long', 'longitud', 'longitude_']:
                if lng_col in row and row[lng_col]:
                    try:
                        lng = float(row[lng_col])
                        break
                    except:
                        pass
            
                        # If no coordinates found, try to use LLM to interpret location information
            if lat is None or lng is None:
                # Extract location information for LLM interpretation (English and French)
                postal_code = row.get('First 3 Chars of Postal Code', row.get('lin_code_postal', ''))
                intersection1 = row.get('Intersection Street 1', row.get('rue_intersection1', row.get('rue', '')))
                intersection2 = row.get('Intersection Street 2', row.get('rue_intersection2', ''))
                ward = row.get('Ward', row.get('arrondissement', ''))
                service_type = row.get('Service Request Type', row.get('nature', row.get('acti_nom', '')))
                
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
                    # Skip this POI if we can't determine real coordinates
                    print(f"⚠️ LLM couldn't determine coordinates, skipping this POI")
                    continue
            
            # Extract service request information with better field mapping (English and French)
            service_type = row.get('Service Request Type', row.get('original_service_request_type', row.get('nature', row.get('acti_nom', 'Service Request'))))
            status = row.get('Status', row.get('service_request_status', row.get('dernier_statut', 'Unknown')))
            
            # Extract date information - try common date field names
            creation_date = None
            date_fields = ['Creation Date', 'created_date', 'date_created', 'created', 'date', 'timestamp', 'created_at']
            for date_field in date_fields:
                if date_field in row and row[date_field]:
                    creation_date = row[date_field]
                    break
            
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
                "section": row.get('Section', ''),
                "creation_date": creation_date
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

def parse_json_data(data: Any, city: str, province: str, country: str, max_pois: int = 25):
    """Parse JSON data from 311 service requests."""
    pois = []
    
    if isinstance(data, dict):
        if "service_requests" in data:
            for request in data["service_requests"][:max_pois]:
                if "lat" in request and "long" in request:
                    # Extract date information for JSON data
                    creation_date = None
                    for date_field in ['created_date', 'date_created', 'created', 'date', 'timestamp', 'created_at', 'creation_date']:
                        if date_field in request and request[date_field]:
                            creation_date = request[date_field]
                            break
                    
                    poi = {
                        "name": request.get("service_name", f"{city} Service Request"),
                        "lat": float(request["lat"]),
                        "lng": float(request["long"]),
                        "type": "311_service",
                        "summary": request.get("description", f"City service request in {city}"),
                        "source": "311_api",
                        "status": request.get("status", "unknown"),
                        "creation_date": creation_date
                    }
                    pois.append(poi)
        elif "service_definitions" in data:
            # Skip service definitions without real coordinates
            print("⚠️ Service definitions found but no real coordinates available, skipping")
            pass
    elif isinstance(data, list):
        for item in data[:max_pois]:
            if "latitude" in item and "longitude" in item:
                # Extract date information for list data
                creation_date = None
                for date_field in ['created_date', 'date_created', 'created', 'date', 'timestamp', 'created_at', 'creation_date']:
                    if date_field in item and item[date_field]:
                        creation_date = item[date_field]
                        break
                
                poi = {
                    "name": item.get("complaint_type", f"{city} Service Request"),
                    "lat": float(item["latitude"]),
                    "lng": float(item["longitude"]),
                    "type": "311_service",
                    "summary": item.get("descriptor", f"City service request in {city}"),
                    "source": "311_api",
                    "status": item.get("status", "unknown"),
                    "creation_date": creation_date
                }
                pois.append(poi)
    
    return pois

def parse_data_into_pois(raw_data: str, city: str, province: str, country: str, max_pois: int, user_lat: float = 0, user_lon: float = 0) -> List[Dict[str, Any]]:
    """
    Parse raw data into POIs.
    
    This function tries different parsing approaches:
    1. Try to parse as JSON
    2. If that fails, try to parse as CSV
    3. If that fails, use LLM superpower
    4. Return the parsed POIs
    """
    
    # Try to parse as JSON first
    try:
        json_data = json.loads(raw_data)
        pois = parse_json_data(json_data, city, province, country, max_pois)
        if pois:
            return pois
    except json.JSONDecodeError:
        pass
    
    # If JSON parsing failed, try CSV
    pois = parse_csv_data(raw_data, city, province, country, max_pois)
    if pois:
        return pois
    
    # If all parsing failed, use LLM superpower
    print("🦸‍♂️ Using LLM superpower to interpret raw data...")
    pois = llm_interpret_any_data(raw_data, city, province, country, user_lat, user_lon)
    return pois
