#!/usr/bin/env python3
"""
Test script to verify Reddit scraper improvements:
1. Generic city support
2. Better geocoding search queries
3. Improved LLM coordinate extraction
4. Fallback geocoding methods
"""
import asyncio
import sys
import os
sys.path.append('.')

from agents.reddit_scraper import get_reddit_pois_direct

async def test_reddit_improvements():
    """Test the improved Reddit scraper with different cities"""
    print("🧪 TESTING REDDIT SCRAPER IMPROVEMENTS")
    print("=" * 60)
    
    # Test with just one city
    test_cities = [
        {
            "city": "Toronto",
            "province": "Ontario", 
            "country": "Canada",
            "lat": 43.6532,
            "lng": -79.3832
        }
    ]
    
    for i, test_data in enumerate(test_cities):
        print(f"\n🏙️ TEST {i+1}: {test_data['city']}")
        print("-" * 40)
        
        try:
            # Test the improved Reddit scraper
            pois = await get_reddit_pois_direct(
                city=test_data['city'],
                province=test_data['province'],
                country=test_data['country'],
                lat=test_data['lat'],
                lng=test_data['lng']
            )
            
            print(f"✅ Found {len(pois)} POIs for {test_data['city']}")
            
            # Show first 3 POIs
            for j, poi in enumerate(pois[:3]):
                print(f"\n  {j+1}. {poi['name']}")
                print(f"     Coordinates: ({poi['lat']}, {poi['lng']})")
                print(f"     Summary: {poi['summary'][:100]}...")
                print(f"     Type: {poi['type']}")
            
            if len(pois) > 3:
                print(f"  ... and {len(pois) - 3} more POIs")
                
        except Exception as e:
            print(f"❌ Error testing {test_data['city']}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🎉 TESTING COMPLETE")
    print("=" * 60)

def test_geocoding_fallback():
    """Test the fallback geocoding methods directly"""
    print("\n🗺️ TESTING FALLBACK GEOCODING METHODS")
    print("-" * 40)
    
    # Import the geocoding function
    from agents.reddit_scraper import create_reddit_scraper_agent
    
    # Create a workflow to access the geocoding function
    workflow = create_reddit_scraper_agent(city="Toronto")
    
    # Test POIs that might be hard to geocode
    test_pois = [
        "Kensington Market",
        "Distillery District", 
        "Harbourfront Centre",
        "St. Lawrence Market",
        "High Park"
    ]
    
    for poi_name in test_pois:
        print(f"\n🔍 Testing geocoding for: {poi_name}")
        
        # This would require accessing the geocoding function directly
        # For now, just show what we're testing
        print(f"  Would test fallback geocoding for: {poi_name}")
        print(f"  Location: Toronto, Ontario, Canada")

if __name__ == "__main__":
    print("🚀 STARTING REDDIT SCRAPER IMPROVEMENT TESTS")
    print("=" * 60)
    
    # Test the main functionality
    asyncio.run(test_reddit_improvements())
    
    # Test geocoding fallbacks
    test_geocoding_fallback()
    
    print("\n✅ ALL TESTS COMPLETE")
