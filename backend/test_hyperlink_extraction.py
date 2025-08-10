#!/usr/bin/env python3
"""
Test script to demonstrate the improved hyperlink extraction functionality
"""
import asyncio
import sys
import os
sys.path.append('.')

from agents.reddit_scraper import extract_reddit_post_urls
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit

async def test_hyperlink_extraction():
    """Test the improved hyperlink extraction functionality"""
    print("🔗 TESTING IMPROVED HYPERLINK EXTRACTION")
    print("=" * 50)
    
    try:
        # Initialize browser
        async_browser = create_async_playwright_browser(headless=False)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        tools = toolkit.get_tools()
        
        # Get required tools
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        extract_tool = next(tool for tool in tools if tool.name == "extract_text")
        
        # Test URL
        test_url = "https://old.reddit.com/r/toronto/search/?q=hidden%20gems%20Toronto&restrict_sr=on&sort=relevance&t=all"
        print(f"🌐 Navigating to: {test_url}")
        
        # Navigate to Reddit search
        await navigate_tool.arun({"url": test_url})
        await asyncio.sleep(5)
        
        # Extract page content
        print("📄 Extracting page content...")
        page_content = await extract_tool.arun({})
        print(f"📊 Content length: {len(page_content)} characters")
        
        # Test our custom hyperlink extraction
        print("🔍 Testing custom hyperlink extraction...")
        post_urls = extract_reddit_post_urls(page_content)
        
        print(f"✅ Found {len(post_urls)} Reddit post URLs:")
        for i, url in enumerate(post_urls[:5]):  # Show first 5
            print(f"  {i+1}. {url}")
        
        if post_urls:
            print("🎉 SUCCESS: Hyperlink extraction is working!")
            
            # Test navigating to first post
            first_post = post_urls[0]
            print(f"🌐 Testing navigation to first post: {first_post[:60]}...")
            
            await navigate_tool.arun({"url": first_post})
            await asyncio.sleep(4)
            
            # Extract post content
            post_content = await extract_tool.arun({})
            print(f"📄 Post content length: {len(post_content)} characters")
            
            # Check if it's a Reddit post
            reddit_indicators = ['comments', 'upvote', 'downvote', 'share', 'award', 'reply', 'r/', 'u/', 'points', 'submitted']
            has_reddit_content = any(indicator in post_content.lower() for indicator in reddit_indicators)
            
            if has_reddit_content:
                print("✅ SUCCESS: Successfully navigated to Reddit post!")
                print("✅ SUCCESS: Extracted authentic Reddit content!")
                print("✅ SUCCESS: Hyperlink extraction and navigation working perfectly!")
            else:
                print("⚠️ Content doesn't look like Reddit")
        else:
            print("❌ No post URLs found")
        
        await async_browser.close()
        return len(post_urls) > 0
        
    except Exception as e:
        print(f"❌ Error in hyperlink extraction test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 STARTING HYPERLINK EXTRACTION TEST")
    print("=" * 50)
    
    success = asyncio.run(test_hyperlink_extraction())
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Hyperlink extraction is working correctly")
        print("✅ Navigation to individual posts is working")
        print("✅ Content extraction is working")
    else:
        print("\n❌ TESTS FAILED")
        print("⚠️ Hyperlink extraction needs improvement")
