#!/usr/bin/env python3
"""
Debug script to examine the actual content structure from Reddit
"""
import asyncio
import sys
import os
sys.path.append('.')

from agents.reddit_scraper import extract_reddit_post_urls
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
import re

async def debug_reddit_content():
    """Debug the actual content structure from Reddit"""
    print("🔍 DEBUGGING REDDIT CONTENT STRUCTURE")
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
        
        # Show first 2000 characters to see the structure
        print("\n🔍 FIRST 2000 CHARACTERS:")
        print("-" * 30)
        print(page_content[:2000])
        print("-" * 30)
        
        # Look for any URLs in the content
        print("\n🔍 LOOKING FOR ANY URLS IN CONTENT:")
        print("-" * 30)
        
        # Simple URL patterns
        url_patterns = [
            r'https?://[^\s<>"]+',
            r'/[^\s<>"]*comments/[^\s<>"]*',
            r'href="[^"]*"',
            r'<a[^>]*href="[^"]*"[^>]*>',
        ]
        
        for i, pattern in enumerate(url_patterns):
            matches = re.findall(pattern, page_content)
            print(f"Pattern {i+1}: '{pattern}' - Found {len(matches)} matches")
            for j, match in enumerate(matches[:3]):  # Show first 3
                print(f"  {j+1}. {match}")
        
        # Look for Reddit-specific patterns
        print("\n🔍 LOOKING FOR REDDIT-SPECIFIC PATTERNS:")
        print("-" * 30)
        
        reddit_patterns = [
            r'reddit\.com',
            r'/r/toronto',
            r'comments',
            r'upvote',
            r'downvote',
            r'points',
            r'submitted',
        ]
        
        for pattern in reddit_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            print(f"'{pattern}': {len(matches)} matches")
        
        # Test our custom function
        print("\n🔍 TESTING CUSTOM EXTRACTION FUNCTION:")
        print("-" * 30)
        post_urls = extract_reddit_post_urls(page_content)
        print(f"Custom function found {len(post_urls)} URLs")
        
        # Try with BeautifulSoup directly
        print("\n🔍 TESTING BEAUTIFULSOUP DIRECTLY:")
        print("-" * 30)
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(page_content, 'html.parser')
        links = soup.find_all('a', href=True)
        print(f"BeautifulSoup found {len(links)} links total")
        
        reddit_links = []
        for link in links:
            href = link.get('href', '')
            if '/comments/' in href:
                reddit_links.append(href)
                print(f"  Found Reddit link: {href}")
        
        print(f"BeautifulSoup found {len(reddit_links)} Reddit comment links")
        
        await async_browser.close()
        
    except Exception as e:
        print(f"❌ Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 STARTING CONTENT DEBUG")
    print("=" * 50)
    
    asyncio.run(debug_reddit_content())
