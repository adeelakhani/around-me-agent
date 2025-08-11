#!/usr/bin/env python3
"""
Debug script to test geocoding functionality
"""
import sys
import os
from dotenv import load_dotenv
sys.path.append('.')

# Load environment variables
load_dotenv(override=True)

def test_geocoding():
    """Test the geocoding methods directly"""
    print("🗺️ TESTING GEOCODING METHODS")
    print("=" * 50)
    
    # Test POIs
    test_pois = [
        "Kensington Market",
        "Distillery District", 
        "Harbourfront Centre",
        "St. Lawrence Market",
        "High Park"
    ]
    
    city = "Toronto"
    province = "Ontario"
    country = "Canada"
    
    for poi_name in test_pois:
        print(f"\n🔍 Testing geocoding for: {poi_name}")
        print("-" * 30)
        
        # Test OpenStreetMap directly
        try:
            import requests
            search_query = f"{poi_name}, {city}, {province}, {country}"
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": search_query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            }
            headers = {"User-Agent": "AroundMeAgent/1.0"}
            
            print(f"🔍 Searching: {search_query}")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            results = response.json()
            
            if results and len(results) > 0:
                result = results[0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                print(f"✅ OpenStreetMap found: ({lat}, {lon})")
                print(f"   Address: {result.get('display_name', 'N/A')}")
            else:
                print("❌ OpenStreetMap returned no results")
                
        except Exception as e:
            print(f"❌ OpenStreetMap error: {e}")
        
        # Test Serper search
        try:
            serper_key = os.getenv("SERPER_API_KEY")
            if serper_key:
                url = "https://google.serper.dev/search"
                headers = {
                    "X-API-KEY": serper_key,
                    "Content-Type": "application/json"
                }
                payload = {"q": f'"{poi_name}" "{city}" address location coordinates'}
                
                print(f"🔍 Serper search: {payload['q']}")
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                response.raise_for_status()
                search_results = response.json()
                
                if search_results.get("organic") and len(search_results["organic"]) > 0:
                    print(f"✅ Serper found {len(search_results['organic'])} results")
                    # Show first result
                    first_result = search_results["organic"][0]
                    print(f"   Title: {first_result.get('title', 'N/A')}")
                    print(f"   Snippet: {first_result.get('snippet', 'N/A')[:100]}...")
                else:
                    print("❌ Serper returned no results")
            else:
                print("⚠️ SERPER_API_KEY not found")
                
        except Exception as e:
            print(f"❌ Serper error: {e}")

if __name__ == "__main__":
    test_geocoding()
