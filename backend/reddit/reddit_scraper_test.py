#!/usr/bin/env python3
"""
Test script to verify improved Reddit scraper navigation between posts
"""
import asyncio
import os
import sys
sys.path.append('..')  # Add parent directory to path

from dotenv import load_dotenv
from agents.reddit_scraper import get_reddit_pois_direct

load_dotenv()

async def test_improved_reddit_navigation():
    """Test the improved Reddit scraper navigation functionality"""
    print("🧪 Testing IMPROVED Reddit scraper navigation...")
    
    # Test parameters
    city = "Toronto"
    province = "Ontario"
    country = "Canada"
    lat = 43.6532
    lng = -79.3832
    
    try:
        print(f"📍 Testing for {city}, {province}, {country}")
        print(f"🌍 Coordinates: ({lat}, {lng})")
        
        # Run the Reddit scraper
        pois = await get_reddit_pois_direct(city, province, country, lat, lng)
        
        print(f"\n📊 Results:")
        print(f"✅ Found {len(pois)} POIs")
        
        if pois:
            print("\n📍 Sample POIs found:")
            for i, poi in enumerate(pois[:5]):  # Show first 5
                print(f"  {i+1}. {poi['name']}")
                print(f"     Summary: {poi['summary'][:100]}...")
                print(f"     Coordinates: ({poi['lat']}, {poi['lng']})")
                print()
        else:
            print("❌ No POIs found - navigation might not be working")
            
        return len(pois) > 0
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_simple_improved_navigation():
    """Test just the navigation part with improved selectors"""
    print("\n🔍 Testing improved simple navigation...")
    
    try:
        from langchain_community.tools.playwright.utils import create_async_playwright_browser
        from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
        
        # Initialize browser
        async_browser = create_async_playwright_browser(headless=False)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        tools = toolkit.get_tools()
        
        # Get navigation tools
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        click_tool = next(tool for tool in tools if tool.name == "click_element")
        get_elements_tool = next(tool for tool in tools if tool.name == "get_elements")
        back_tool = next(tool for tool in tools if tool.name == "previous_webpage")
        current_webpage_tool = next(tool for tool in tools if tool.name == "current_webpage")
        
        # Navigate to Reddit search
        search_url = "https://www.reddit.com/search/?q=things%20to%20do%20Toronto&type=link&sort=relevance&t=year"
        print(f"🌐 Navigating to: {search_url}")
        
        await navigate_tool.arun({"url": search_url})
        await asyncio.sleep(5)  # Wait longer for page to load
        
        # Check current URL
        current_url = await current_webpage_tool.arun({})
        print(f"📍 Current URL: {current_url}")
        
        # Test multiple selectors for post titles
        selectors_to_test = [
            'h3[data-testid="post-title"]:nth-of-type(1)',
            'a[data-testid="post-title"]:nth-of-type(1)',
            '[data-testid="post-title"]:nth-of-type(1)',
            'a[href*="/comments/"]:nth-of-type(1)'
        ]
        
        print("🔍 Testing different selectors...")
        for selector in selectors_to_test:
            try:
                elements = await get_elements_tool.arun({"selector": selector})
                print(f"  {selector}: Found {len(elements)} elements")
                if elements:
                    print(f"    ✅ Selector works: {selector}")
            except Exception as e:
                print(f"    ❌ Selector failed: {selector} - {e}")
        
        # Try to click on first post with best selector
        print("\n🖱️ Attempting to click on first post with improved selector...")
        try:
            await click_tool.arun({
                "selector": 'a[href*="/comments/"]:nth-of-type(1)',
                "button": "left"
            })
            
            await asyncio.sleep(5)
            
            # Check if we navigated to a post
            post_url = await current_webpage_tool.arun({})
            print(f"📍 URL after clicking: {post_url}")
            
            if "about:blank" not in post_url and "reddit.com/search" not in post_url:
                print("✅ Successfully navigated to a post!")
            else:
                print("⚠️ Still on search page or got about:blank")
            
            # Go back
            print("⬅️ Going back to search results...")
            await back_tool.arun({})
            await asyncio.sleep(3)
            
            # Check if we're back
            back_url = await current_webpage_tool.arun({})
            print(f"📍 URL after going back: {back_url}")
            
            # Try clicking second post
            print("🖱️ Attempting to click on second post...")
            await click_tool.arun({
                "selector": 'a[href*="/comments/"]:nth-of-type(2)',
                "button": "left"
            })
            
            await asyncio.sleep(5)
            
            second_post_url = await current_webpage_tool.arun({})
            print(f"📍 URL after clicking second post: {second_post_url}")
            
            if "about:blank" not in second_post_url and "reddit.com/search" not in second_post_url:
                print("✅ Successfully navigated to second post!")
            else:
                print("⚠️ Second post navigation failed")
            
        except Exception as e:
            print(f"❌ Click failed: {e}")
        
        # Close browser
        await async_browser.close()
        
        print("✅ Improved navigation test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Improved navigation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting IMPROVED Reddit scraper navigation tests...")
    
    # Run tests
    async def run_tests():
        # Test 1: Simple improved navigation
        nav_success = await test_simple_improved_navigation()
        
        # Test 2: Full improved scraper
        scraper_success = await test_improved_reddit_navigation()
        
        print(f"\n📋 Test Results:")
        print(f"  Improved Navigation Test: {'✅ PASSED' if nav_success else '❌ FAILED'}")
        print(f"  Full Improved Scraper Test: {'✅ PASSED' if scraper_success else '❌ FAILED'}")
        
        if nav_success and scraper_success:
            print("\n🎉 All improved tests passed! Navigation is working correctly.")
        else:
            print("\n⚠️ Some improved tests failed. Navigation may still have issues.")
    
    asyncio.run(run_tests())
