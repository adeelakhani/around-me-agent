"""
Geocoding utilities for Reddit POI extraction
"""
import os
import requests
import re
from typing import Optional, Dict
from utils.location import is_coordinates_in_city
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
load_dotenv(override=True)

def search_serper(query: str) -> dict:
    """Search using Serper.dev API"""
    serper_key = os.getenv("SERPER_API_KEY")
    if not serper_key:
        print("⚠️ SERPER_API_KEY not found, using fallback coordinates")
        return {"organic": [], "knowledgeGraph": None}
        
    try:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": serper_key,
            "Content-Type": "application/json"
        }
        payload = {"q": query}
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Serper search error: {e}")
        return {"organic": [], "knowledgeGraph": None}

def geocode_with_fallback(poi_name: str, city: str, province: str, country: str) -> Optional[Dict[str, float]]:
    """Advanced geocoding: KnowledgeGraph → Site-specific Serper → HTML scraping → Google Places → OSM"""
    print(f"🗺️ ===== STARTING GEOCODING FOR: {poi_name} =====")
    print(f"📍 Target city: {city}, {province}, {country}")
    
    try:
        print(f"🔍 STEP 1: Checking Serper KnowledgeGraph for {poi_name}...")
        search_query = f'"{poi_name}" "{city}"'
        search_results = search_serper(search_query)
        
        if search_results.get("knowledgeGraph") and search_results["knowledgeGraph"].get("address"):
            address = search_results["knowledgeGraph"]["address"]
            print(f"✅ KnowledgeGraph found address: {address}")
            
            coords = geocode_address(address, city, province, country)
            if coords:
                return coords
        else:
            print("❌ No KnowledgeGraph address found")
            
    except Exception as e:
        print(f"❌ KnowledgeGraph search error: {e}")
    
    try:
        print(f"🔍 STEP 2: Using site-specific Serper searches...")
        site_queries = [
            f'"{poi_name}" "{city}" site:maps.google.com',
            f'"{poi_name}" "{city}" site:yellowpages.ca',
            f'"{poi_name}" "{city}" site:yelp.ca',
            f'"{poi_name}" "{city}" site:facebook.com',
            f'"{poi_name}" "{city}" site:google.com/maps',
            f'"{poi_name}" "{city}" site:opentable.ca'
        ]
        
        candidate_addresses = []
        
        for i, site_query in enumerate(site_queries):
            print(f"  🔎 Site search {i+1}: {site_query}")
            search_results = search_serper(site_query)
            
            if search_results.get("organic") and len(search_results["organic"]) > 0:
                print(f"✅ Site search {i+1} returned {len(search_results['organic'])} results")
                
                for result in search_results["organic"][:2]:
                    snippet = result.get("snippet", "")
                    title = result.get("title", "")
                    link = result.get("link", "")
                    
                    text = f"{title} {snippet}"
                    
                    import re
                    address_pattern = r"\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Lane|Ln|Way|Court|Ct|Crescent|Cres|Place|Pl|Terrace|Ter|Circle|Cir|Square|Sq|Parkway|Pkwy)"
                    addresses = re.findall(address_pattern, text, re.IGNORECASE)
                    
                    for addr in addresses:
                        if addr not in candidate_addresses:
                            candidate_addresses.append(addr)
                            print(f"    📍 Found candidate address: {addr}")
                
                if search_results["organic"]:
                    try:
                        import requests
                        from bs4 import BeautifulSoup
                        
                        page_url = search_results["organic"][0]["link"]
                        print(f"    🌐 Scraping: {page_url}")
                        
                        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                        response = requests.get(page_url, headers=headers, timeout=5)
                        
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            page_text = soup.get_text()
                            
                            html_addresses = re.findall(address_pattern, page_text, re.IGNORECASE)
                            
                            for addr in html_addresses[:3]:
                                if addr not in candidate_addresses:
                                    candidate_addresses.append(addr)
                                    print(f"    📍 Found HTML address: {addr}")
                                    
                    except Exception as e:
                        print(f"    ⚠️ HTML scraping failed: {e}")
            else:
                print(f"⚠️ Site search {i+1} returned no results")
        
        if candidate_addresses:
            print(f"🔍 STEP 3: Ranking {len(candidate_addresses)} candidate addresses...")
            
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini")
            
            ranking_prompt = f"""Rank these addresses by how likely they are to be the correct address for "{poi_name}" in {city}.

Business: {poi_name}
City: {city}, {province}, {country}

Candidate addresses:
{chr(10).join([f"{i+1}. {addr}" for i, addr in enumerate(candidate_addresses)])}

Return ONLY the number of the best address, or "NONE" if none seem correct.

Consider:
- Addresses that include the business name are more likely correct
- Addresses in {city} are more likely than other cities
- More complete addresses (with street type) are better
- Avoid generic addresses that could be anywhere

Example: If address #3 seems best, return "3"
Example: If none seem right, return "NONE"
"""
            
            ranking_response = llm.invoke([
                SystemMessage(content="You are an address ranking specialist. Return only a number (1, 2, 3, etc.) or 'NONE' if none seem correct."),
                HumanMessage(content=ranking_prompt)
            ])
            
            try:
                response_text = ranking_response.content.strip()
                print(f"    🤖 LLM response: '{response_text}'")
                
                if response_text.upper() == "NONE":
                    print("❌ LLM said none of the addresses seem correct")
                else:
                    best_index = int(response_text) - 1
                    if 0 <= best_index < len(candidate_addresses):
                        best_address = candidate_addresses[best_index]
                        print(f"✅ LLM selected best address: {best_address}")
                        
                        coords = geocode_address(best_address, city, province, country)
                        if coords:
                            return coords
                    else:
                        print(f"❌ LLM selected invalid address index: {best_index}")
            except ValueError as e:
                print(f"❌ LLM returned invalid response: '{ranking_response.content.strip()}' - {e}")
        else:
            print("❌ No candidate addresses found from site searches")
            
    except Exception as e:
        print(f"❌ Site-specific search error: {e}")
    
    try:
        print(f"🔍 STEP 4: Trying Google Places API with business name...")
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if google_api_key:
            search_strategies = [
                f'"{poi_name}" {city}',
                f'{poi_name} restaurant {city}',
                f'{poi_name} {city} address',
                f'{poi_name} {city} location'
            ]
            
            for i, search_input in enumerate(search_strategies):
                print(f"  🔎 Google Places search {i+1}: {search_input}")
                
                url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                params = {
                    "input": search_input,
                    "inputtype": "textquery",
                    "fields": "geometry/location,formatted_address,name,types,place_id",
                    "key": google_api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                result = response.json()
                
                print(f"    📊 Google Places response status: {result.get('status')}")
                
                if result.get("status") == "OK" and result.get("candidates"):
                    candidate = result["candidates"][0]
                    location = candidate["geometry"]["location"]
                    lat = location["lat"]
                    lng = location["lng"]
                    formatted_address = candidate.get("formatted_address", "N/A")
                    place_name = candidate.get("name", "N/A")
                    place_types = candidate.get("types", [])
                    place_id = candidate.get("place_id", "N/A")
                    
                    print(f"    📍 Google Places found: {place_name}")
                    print(f"    📍 Address: {formatted_address}")
                    print(f"    📍 Types: {place_types}")
                    print(f"    📍 Place ID: {place_id}")
                    print(f"    📍 Coordinates: ({lat}, {lng})")
                    
                    is_likely_correct = (
                        poi_name.lower() in place_name.lower() or 
                        place_name.lower() in poi_name.lower() or
                        any(business_type in place_types for business_type in ['restaurant', 'food', 'store', 'establishment'])
                    )
                    
                    if is_likely_correct:
                        if is_coordinates_in_city(lat, lng, city):
                            print(f"✅ Google Places found correct business within city bounds: ({lat}, {lng})")
                            return {"lat": lat, "lng": lng}
                        else:
                            print(f"⚠️ Google Places found correct business but outside city bounds: ({lat}, {lng})")
                            print(f"✅ Returning coordinates anyway since business name matches: ({lat}, {lng})")
                            return {"lat": lat, "lng": lng}
                    else:
                        print(f"⚠️ Google Places found different business: {place_name}")
                        continue
                else:
                    print(f"❌ Google Places search {i+1} failed: {result.get('status')} - {result.get('error_message', 'No error message')}")
                    continue
            
            print("❌ All Google Places search strategies failed")
        else:
            print("⚠️ GOOGLE_PLACES_API_KEY not found, skipping Google Places")
            
    except Exception as e:
        print(f"❌ Google Places geocoding error: {e}")
    
    try:
        print(f"🔍 STEP 5: Trying OpenStreetMap (Nominatim)...")
        search_query = f"{poi_name}, {city}, {province}, {country}"
        print(f"  🔎 OpenStreetMap search: {search_query}")
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": search_query,
            "format": "json",
            "limit": 3,
            "addressdetails": 1
        }
        headers = {"User-Agent": "AroundMeAgent/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        
        print(f"    📊 OpenStreetMap returned {len(results)} results")
        
        if results and len(results) > 0:
            for i, result in enumerate(results):
                lat = float(result["lat"])
                lon = float(result["lon"])
                display_name = result.get("display_name", "N/A")
                result_type = result.get("type", "N/A")
                
                print(f"    📍 Result {i+1}: {display_name}")
                print(f"    📍 Type: {result_type}")
                print(f"    📍 Coordinates: ({lat}, {lon})")
                
                if is_coordinates_in_city(lat, lon, city):
                    print(f"✅ OpenStreetMap result {i+1} within city bounds: ({lat}, {lon})")
                    return {"lat": lat, "lng": lon}
                else:
                    print(f"⚠️ OpenStreetMap result {i+1} outside city bounds: ({lat}, {lon})")
            
            print("❌ All OpenStreetMap results were outside city bounds")
        else:
            print("❌ OpenStreetMap returned no results")
            
    except Exception as e:
        print(f"❌ OpenStreetMap geocoding error: {e}")
    
    print(f"❌ ===== ALL GEOCODING METHODS FAILED FOR: {poi_name} =====")
    return None

def geocode_address(address: str, city: str, province: str, country: str) -> Optional[Dict[str, float]]:
    """Helper function to geocode a specific address"""
    print(f"    🗺️ Geocoding address: {address}")
    
    try:
        google_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if google_api_key:
            search_input = f"{address}, {city}"
            
            url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
            params = {
                "input": search_input,
                "inputtype": "textquery",
                "fields": "geometry/location",
                "key": google_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "OK" and result.get("candidates"):
                location = result["candidates"][0]["geometry"]["location"]
                lat = location["lat"]
                lng = location["lng"]
                
                if is_coordinates_in_city(lat, lng, city):
                    print(f"    ✅ Google Places geocoded: ({lat}, {lng})")
                    return {"lat": lat, "lng": lng}
                else:
                    print(f"    ⚠️ Google Places coordinates outside city bounds: ({lat}, {lng})")
    except Exception as e:
        print(f"    ❌ Google Places geocoding error: {e}")
    
    try:
        search_query = f"{address}, {city}, {province}, {country}"
        
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": search_query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        headers = {"User-Agent": "AroundMeAgent/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()
        
        if results and len(results) > 0:
            result = results[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            
            if is_coordinates_in_city(lat, lon, city):
                print(f"    ✅ OpenStreetMap geocoded: ({lat}, {lon})")
                return {"lat": lat, "lng": lon}
            else:
                print(f"    ⚠️ OpenStreetMap coordinates outside city bounds: ({lat}, {lon})")
    except Exception as e:
        print(f"    ❌ OpenStreetMap geocoding error: {e}")
    
    return None
