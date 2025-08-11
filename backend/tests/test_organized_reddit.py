#!/usr/bin/env python3
"""
Test script for the organized Reddit scraper
"""
import asyncio
from agents.reddit_scraper import create_reddit_scraper_agent, get_reddit_pois_direct
from reddit.search_terms import get_search_terms, get_random_search_term
from reddit.geocoding import search_serper, geocode_with_fallback
from reddit.models import POI, POIList, POIOutput

def test_search_terms():
    """Test the search terms module"""
    print("🧪 Testing search terms module...")
    
    city = "Toronto"
    search_terms = get_search_terms(city)
    print(f"✅ Got {len(search_terms)} search terms for {city}")
    print(f"   First few: {search_terms[:3]}")
    
    random_term = get_random_search_term(city)
    print(f"✅ Random search term: {random_term}")
    
    return True

def test_geocoding():
    """Test the geocoding module"""
    print("\n🧪 Testing geocoding module...")
    
    # Test Serper search
    test_query = "CN Tower Toronto"
    print(f"🔍 Testing Serper search for: {test_query}")
    try:
        results = search_serper(test_query)
        print(f"✅ Serper returned {len(results.get('organic', []))} results")
    except Exception as e:
        print(f"❌ Serper test failed: {e}")
    
    # Test geocoding fallback
    print(f"🗺️ Testing geocoding fallback for: CN Tower")
    try:
        coords = geocode_with_fallback("CN Tower", "Toronto", "Ontario", "Canada")
        if coords:
            print(f"✅ Geocoding successful: ({coords['lat']}, {coords['lng']})")
        else:
            print("❌ Geocoding failed")
    except Exception as e:
        print(f"❌ Geocoding test failed: {e}")
    
    return True

def test_models():
    """Test the models module"""
    print("\n🧪 Testing models module...")
    
    # Test POI model
    poi = POI(
        name="Test Place",
        description="A test place",
        category="restaurant",
        reddit_context="Reddit users love this place"
    )
    print(f"✅ Created POI: {poi.name}")
    
    # Test POIOutput model
    poi_output = POIOutput(
        name="Test Place",
        lat=43.6532,
        lng=-79.3832,
        summary="A great test place",
        type="reddit",
        radius=20
    )
    print(f"✅ Created POIOutput: {poi_output.name}")
    
    return True

async def test_agent():
    """Test the Reddit scraper agent"""
    print("\n🧪 Testing Reddit scraper agent...")
    
    try:
        # Create agent
        workflow = create_reddit_scraper_agent(city="Toronto")
        print("✅ Created Reddit scraper agent")
        
        # Test initial state
        initial_state = {
            "subreddit": "toronto",
            "city": "Toronto",
            "location_data": {
                "city": "Toronto",
                "province": "Ontario", 
                "country": "Canada"
            },
            "current_step": "scrape_reddit",
            "messages": [],
            "reddit_data": [],
            "pois": [],
            "scraped_content": None,
            "extracted_pois": []
        }
        
        print("✅ Created initial state")
        return True
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing organized Reddit scraper modules...\n")
    
    # Test individual modules
    test_search_terms()
    test_geocoding()
    test_models()
    
    # Test agent (without running full workflow)
    asyncio.run(test_agent())
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()
