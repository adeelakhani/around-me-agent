#!/usr/bin/env python3
"""
Debug script to examine Playwright elements and see why href extraction isn't working
"""
import asyncio
import sys
import os
sys.path.append('.')

from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
import json

async def debug_elements():
    """Debug what Playwright elements actually contain"""
    print("🔍 DEBUGGING PLAYWRIGHT ELEMENTS")
    print("=" * 50)
    
    try:
        # Initialize browser
        async_browser = create_async_playwright_browser(headless=False)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        tools = toolkit.get_tools()
        
        # Get required tools
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        get_elements_tool = next(tool for tool in tools if tool.name == "get_elements")
        
        # Test URL
        test_url = "https://old.reddit.com/r/toronto/search/?q=hidden%20gems%20Toronto&restrict_sr=on&sort=relevance&t=all"
        print(f"🌐 Navigating to: {test_url}")
        
        # Navigate to Reddit search
        await navigate_tool.arun({"url": test_url})
        await asyncio.sleep(5)
        
        # Try different selectors
        selectors = [
            "div.thing .title a[href*='/comments/']",
            "a[href*='/comments/']",
            ".title a[href*='/comments/']",
            "[data-testid='post-container'] a[href*='/comments/']",
        ]
        
        for selector in selectors:
            print(f"\n🔍 Testing selector: {selector}")
            print("-" * 40)
            
            try:
                elements = await get_elements_tool.arun({"selector": selector})
                print(f"✅ Found {len(elements)} elements")
                
                if elements and len(elements) > 0:
                    # Show first few elements
                    for i, element in enumerate(elements[:3]):
                        print(f"\nElement {i+1}:")
                        print(f"  Type: {type(element)}")
                        print(f"  Content: {element}")
                        
                        if isinstance(element, dict):
                            print(f"  Keys: {list(element.keys())}")
                            if 'href' in element:
                                print(f"  href: {element['href']}")
                            if 'text' in element:
                                print(f"  text: {element['text'][:100]}...")
                        elif isinstance(element, str):
                            print(f"  String length: {len(element)}")
                            print(f"  First 100 chars: {element[:100]}")
                        else:
                            print(f"  String representation: {str(element)[:200]}")
                else:
                    print("❌ No elements found")
                    
            except Exception as e:
                print(f"❌ Error with selector {selector}: {e}")
        
        await async_browser.close()
        
    except Exception as e:
        print(f"❌ Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 STARTING ELEMENTS DEBUG")
    print("=" * 50)
    
    asyncio.run(debug_elements())
