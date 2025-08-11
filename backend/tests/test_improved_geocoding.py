#!/usr/bin/env python3
"""
Test script for improved geocoding function
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reddit.geocoding import geocode_with_fallback

def test_geocoding():
    """Test the improved geocoding function with various POIs"""
    
    # Test cases - mix of easy and hard cases
    test_cases = [
        {
            "name": "Chung Moi",
            "city": "Toronto",
            "province": "Ontario", 
            "country": "Canada",
            "expected_area": "Scarborough"  # Should be in Scarborough, not downtown
        },
        {
            "name": "Pizza Pizza",
            "city": "Toronto",
            "province": "Ontario",
            "country": "Canada",
            "expected_area": "Toronto"  # Should be somewhere in Toronto
        },
        {
            "name": "Tim Hortons",
            "city": "Toronto", 
            "province": "Ontario",
            "country": "Canada",
            "expected_area": "Toronto"  # Should be somewhere in Toronto
        },
        {
            "name": "McDonald's",
            "city": "Toronto",
            "province": "Ontario", 
            "country": "Canada",
            "expected_area": "Toronto"  # Should be somewhere in Toronto
        },
        {
            "name": "I Miss You Man",
            "city": "Toronto",
            "province": "Ontario",
            "country": "Canada",
            "expected_area": "Toronto"  # Should be somewhere in Toronto
        },
        {
            "name": "I Miss You MAN",
            "city": "Toronto",
            "province": "Ontario",
            "country": "Canada",
            "expected_area": "Ossington"  # Should be on Ossington Avenue
        }
    ]
    
    print("🧪 ===== TESTING IMPROVED GEOCODING FUNCTION =====")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🔍 Test {i}: {test_case['name']} in {test_case['city']}")
        print(f"   Expected area: {test_case['expected_area']}")
        print("-" * 60)
        
        try:
            coords = geocode_with_fallback(
                test_case['name'],
                test_case['city'], 
                test_case['province'],
                test_case['country']
            )
            
            if coords:
                print(f"✅ SUCCESS: Found coordinates ({coords['lat']}, {coords['lng']})")
                
                # Basic validation - coordinates should be reasonable for Toronto
                if test_case['city'] == 'Toronto':
                    if 43.5 <= coords['lat'] <= 43.9 and -79.7 <= coords['lng'] <= -79.1:
                        print(f"✅ Coordinates are within reasonable Toronto bounds")
                    else:
                        print(f"⚠️ Coordinates seem outside Toronto bounds")
            else:
                print(f"❌ FAILED: No coordinates found")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print()
        print("=" * 80)
        print()

if __name__ == "__main__":
    test_geocoding()
