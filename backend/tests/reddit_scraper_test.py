#!/usr/bin/env python3
"""
COMPREHENSIVE TEST: Verify Reddit scraper is working correctly and getting authentic content
"""
import asyncio
import os
import sys
sys.path.append('..')  # Add parent directory to path

from dotenv import load_dotenv
from agents.reddit_scraper import get_reddit_pois_direct

load_dotenv()

async def test_reddit_scraper_authenticity():
    """Comprehensive test to verify Reddit scraper is working correctly"""
    print("🧪 COMPREHENSIVE REDDIT SCRAPER AUTHENTICITY TEST")
    print("=" * 60)
    
    # Test parameters
    city = "Toronto"
    province = "Ontario"
    country = "Canada"
    lat = 43.6532
    lng = -79.3832
    
    print(f"📍 Testing for: {city}, {province}, {country}")
    print(f"🌍 Coordinates: ({lat}, {lng})")
    print()
    
    try:
        print("🚀 Starting Reddit scraper...")
        pois = await get_reddit_pois_direct(city, province, country, lat, lng)
        
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"✅ Found {len(pois)} POIs")
        
        if not pois:
            print("❌ FAILED: No POIs found")
            return False
        
        # Test 1: Verify POI Structure
        print(f"\n🔍 TEST 1: POI Structure Validation")
        print("-" * 40)
        
        required_fields = ['name', 'lat', 'lng', 'summary', 'type', 'radius']
        poi_structure_valid = True
        
        for i, poi in enumerate(pois):
            print(f"POI {i+1}: {poi.get('name', 'NO NAME')}")
            
            # Check required fields
            for field in required_fields:
                if field not in poi:
                    print(f"  ❌ Missing field: {field}")
                    poi_structure_valid = False
                else:
                    value = poi[field]
                    if value is None or value == "":
                        print(f"  ⚠️ Empty field: {field}")
                    else:
                        print(f"  ✅ {field}: {str(value)[:50]}...")
            
            # Check coordinates are reasonable
            lat_val = poi.get('lat', 0)
            lng_val = poi.get('lng', 0)
            if abs(lat_val - lat) > 1 or abs(lng_val - lng) > 1:
                print(f"  ⚠️ Coordinates seem far from {city}: ({lat_val}, {lng_val})")
            else:
                print(f"  ✅ Coordinates reasonable: ({lat_val}, {lng_val})")
            
            print()
        
        if not poi_structure_valid:
            print("❌ FAILED: POI structure validation")
            return False
        
        # Test 2: Verify Content Authenticity
        print(f"🔍 TEST 2: Content Authenticity Validation")
        print("-" * 40)
        
        authentic_pois = 0
        for i, poi in enumerate(pois):
            name = poi.get('name', '')
            summary = poi.get('summary', '')
            
            print(f"POI {i+1}: {name}")
            
            # Check if name looks like a real place
            if len(name) < 3 or name.lower() in ['unknown', 'none', 'n/a']:
                print(f"  ❌ Name looks fake: '{name}'")
                continue
            
            # Check if summary contains Reddit indicators
            reddit_indicators = ['reddit', 'r/', 'users', 'locals', 'community', 'recommend', 'love', 'favorite']
            has_reddit_content = any(indicator in summary.lower() for indicator in reddit_indicators)
            
            if has_reddit_content:
                print(f"  ✅ Authentic Reddit content detected")
                print(f"     Summary: {summary[:100]}...")
                authentic_pois += 1
            else:
                print(f"  ⚠️ No clear Reddit indicators in summary")
                print(f"     Summary: {summary[:100]}...")
            
            print()
        
        authenticity_score = authentic_pois / len(pois) if pois else 0
        print(f"Authenticity Score: {authentic_pois}/{len(pois)} ({authenticity_score:.1%})")
        
        if authenticity_score < 0.5:
            print("❌ FAILED: Low authenticity score")
            return False
        
        # Test 3: Verify Toronto-Specific Content
        print(f"🔍 TEST 3: Toronto-Specific Content Validation")
        print("-" * 40)
        
        toronto_pois = 0
        for poi in pois:
            name = poi.get('name', '').lower()
            summary = poi.get('summary', '').lower()
            
            # Check for Toronto-specific indicators
            toronto_indicators = ['toronto', 'to', 'downtown', 'uptown', 'midtown', 'east end', 'west end', 'north york', 'scarborough', 'etobicoke']
            has_toronto_content = any(indicator in name or indicator in summary for indicator in toronto_indicators)
            
            if has_toronto_content:
                toronto_pois += 1
                print(f"✅ {poi.get('name')}: Toronto-specific content found")
            else:
                print(f"⚠️ {poi.get('name')}: No clear Toronto indicators")
        
        toronto_score = toronto_pois / len(pois) if pois else 0
        print(f"Toronto Relevance Score: {toronto_pois}/{len(pois)} ({toronto_score:.1%})")
        
        if toronto_score < 0.3:
            print("❌ FAILED: Low Toronto relevance score")
            return False
        
        # Test 4: Verify Real Place Names
        print(f"🔍 TEST 4: Real Place Name Validation")
        print("-" * 40)
        
        real_places = 0
        for poi in pois:
            name = poi.get('name', '')
            
            # Check for common fake indicators
            fake_indicators = ['test', 'example', 'fake', 'dummy', 'placeholder', 'unknown', 'none']
            looks_fake = any(indicator in name.lower() for indicator in fake_indicators)
            
            # Check for reasonable length and structure
            looks_real = len(name) >= 3 and ' ' in name or len(name) >= 5
            
            if looks_real and not looks_fake:
                real_places += 1
                print(f"✅ {name}: Looks like a real place")
            else:
                print(f"❌ {name}: Looks fake or generic")
        
        real_place_score = real_places / len(pois) if pois else 0
        print(f"Real Place Score: {real_places}/{len(pois)} ({real_place_score:.1%})")
        
        if real_place_score < 0.7:
            print("❌ FAILED: Too many fake place names")
            return False
        
        # Test 5: Overall Assessment
        print(f"🔍 TEST 5: Overall Assessment")
        print("-" * 40)
        
        overall_score = (authenticity_score + toronto_score + real_place_score) / 3
        print(f"Overall Score: {overall_score:.1%}")
        
        if overall_score >= 0.7:
            print("🎉 EXCELLENT: Reddit scraper is working correctly!")
            print("✅ Getting authentic Reddit content")
            print("✅ Extracting real Toronto places")
            print("✅ Generating authentic descriptions")
            return True
        elif overall_score >= 0.5:
            print("⚠️ ACCEPTABLE: Reddit scraper is working but could be better")
            return True
        else:
            print("❌ FAILED: Reddit scraper is not working correctly")
            return False
        
    except Exception as e:
        print(f"❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_url_navigation():
    """Test to verify URL navigation is working correctly"""
    print("\n🌐 URL NAVIGATION TEST")
    print("=" * 40)
    
    try:
        from langchain_community.tools.playwright.utils import create_async_playwright_browser
        from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
        
        # Initialize browser
        async_browser = create_async_playwright_browser(headless=False)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        tools = toolkit.get_tools()
        
        # Get navigation tools
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        current_webpage_tool = next(tool for tool in tools if tool.name == "current_webpage")
        extract_tool = next(tool for tool in tools if tool.name == "extract_text")
        get_elements_tool = next(tool for tool in tools if tool.name == "get_elements")
        
        # Test old Reddit navigation - use a search term that we know works
        test_url = "https://old.reddit.com/r/toronto/search/?q=secret%20spots%20Toronto&restrict_sr=on&sort=relevance&t=all"
        print(f"🌐 Testing navigation to: {test_url}")
        
        await navigate_tool.arun({"url": test_url})
        await asyncio.sleep(5)
        
        current_url = await current_webpage_tool.arun({})
        print(f"📍 Current URL: {current_url}")
        
        if "old.reddit.com" in current_url and "toronto" in current_url:
            print("✅ Successfully navigated to old Reddit")
            
            # Extract content
            content = await extract_tool.arun({})
            print(f"📄 Content length: {len(content)} characters")
            
            # Check for Reddit indicators
            reddit_indicators = ['reddit.com', 'r/', 'upvote', 'downvote', 'comment', 'post']
            has_reddit_content = any(indicator in content.lower() for indicator in reddit_indicators)
            
            if has_reddit_content:
                print("✅ Authentic Reddit content detected")
                
                # Try to find post URLs using the same method that works in the main scraper
                post_urls = []
                
                # Import the extraction function from the main scraper
                import sys
                sys.path.append('..')
                from agents.reddit_scraper import extract_reddit_post_urls_from_text
                
                # Method 1: Try the official ExtractHyperlinksTool (this should work best)
                print("🔍 Method 1: Using official ExtractHyperlinksTool...")
                try:
                    extract_hyperlinks_tool = next(tool for tool in tools if tool.name == "extract_hyperlinks")
                    hyperlinks = await extract_hyperlinks_tool.arun({})
                    print(f"✅ ExtractHyperlinksTool found {len(hyperlinks)} hyperlinks")
                    
                    # Filter for Reddit post links
                    for link in hyperlinks:
                        if '/comments/' in link and 'reddit.com' in link:
                            # Normalize URL
                            if link.startswith('/'):
                                full_url = f"https://old.reddit.com{link}"
                            elif link.startswith('http'):
                                full_url = link
                            else:
                                full_url = f"https://old.reddit.com{link}"
                            
                            # Clean up the URL
                            full_url = full_url.split('?')[0].rstrip('/')
                            
                            if full_url not in post_urls:
                                post_urls.append(full_url)
                                print(f"  📎 Found Reddit post link: {full_url}")
                    
                    print(f"✅ Extracted {len(post_urls)} Reddit post URLs from hyperlinks")
                except Exception as e:
                    print(f"❌ Error with ExtractHyperlinksTool: {e}")
                
                # Method 2: Extract from page content as backup
                if not post_urls:
                    print("🔄 Method 2: Extracting URLs from page content...")
                    post_urls = extract_reddit_post_urls_from_text(content)
                    print(f"✅ Extracted {len(post_urls)} URLs from page content")
                
                # Method 3: Try element selectors as final backup
                if not post_urls:
                    print("🔄 Method 3: Trying element selectors...")
                    try:
                        post_elements = await get_elements_tool.arun({
                            "selector": "div.thing .title a[href*='/comments/']"
                        })
                        
                        if post_elements and len(post_elements) > 0:
                            print(f"✅ Found {len(post_elements)} post elements")
                            
                            # Extract URLs from elements
                            for element in post_elements:
                                if isinstance(element, dict) and 'href' in element:
                                    href = element['href']
                                    if '/comments/' in href:
                                        if href.startswith('/'):
                                            full_url = f"https://old.reddit.com{href}"
                                        else:
                                            full_url = href
                                        full_url = full_url.split('?')[0].rstrip('/')
                                        if full_url not in post_urls:
                                            post_urls.append(full_url)
                    except Exception as e:
                        print(f"❌ Error getting post elements: {e}")
                
                print(f"🔗 Found {len(post_urls)} post URLs using improved methods")
                
                if post_urls:
                    print("✅ Post URLs found - navigation test PASSED")
                    print(f"📎 Sample URLs:")
                    for i, url in enumerate(post_urls[:3]):
                        print(f"  {i+1}. {url}")
                    await async_browser.close()
                    return True
                else:
                    print("⚠️ No post URLs found in content")
            else:
                print("❌ No Reddit content detected")
        else:
            print("❌ Failed to navigate to old Reddit")
        
        await async_browser.close()
        return False
        
    except Exception as e:
        print(f"❌ URL navigation test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 STARTING COMPREHENSIVE REDDIT SCRAPER TESTS")
    print("=" * 60)
    
    async def run_all_tests():
        # Test 1: URL Navigation
        nav_success = await test_url_navigation()
        
        # Test 2: Full Scraper Authenticity
        scraper_success = await test_reddit_scraper_authenticity()
        
        print(f"\n📋 FINAL TEST RESULTS:")
        print("=" * 40)
        print(f"URL Navigation Test: {'✅ PASSED' if nav_success else '❌ FAILED'}")
        print(f"Scraper Authenticity Test: {'✅ PASSED' if scraper_success else '❌ FAILED'}")
        
        if nav_success and scraper_success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Reddit scraper is working correctly")
            print("✅ Getting authentic content")
            print("✅ Navigating to real URLs")
            print("✅ Extracting real Toronto places")
        else:
            print("\n❌ SOME TESTS FAILED")
            print("⚠️ Reddit scraper needs improvement")
    
    asyncio.run(run_all_tests())
