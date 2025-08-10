#!/usr/bin/env python3
"""
Debug script to examine what the hidden gems search actually returns
"""
import asyncio
import sys
import os
sys.path.append('.')

from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
import re
from bs4 import BeautifulSoup
import nest_asyncio

# Apply nest_asyncio to handle event loop issues
nest_asyncio.apply()

async def debug_hidden_gems():
    """Debug what the hidden gems search actually returns"""
    print("🔍 DEBUGGING HIDDEN GEMS SEARCH")
    print("=" * 50)
    
    try:
        # Initialize browser
        async_browser = create_async_playwright_browser(headless=False)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        tools = toolkit.get_tools()
        
        # Get required tools
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        extract_tool = next(tool for tool in tools if tool.name == "extract_text")
        extract_hyperlinks_tool = next(tool for tool in tools if tool.name == "extract_hyperlinks")
        get_elements_tool = next(tool for tool in tools if tool.name == "get_elements")
        
        # Test URL - hidden gems
        test_url = "https://old.reddit.com/r/toronto/search/?q=hidden%20gems%20Toronto&restrict_sr=on&sort=relevance&t=all"
        print(f"🌐 Navigating to: {test_url}")
        
        # Navigate to Reddit search
        await navigate_tool.arun({"url": test_url})
        await asyncio.sleep(5)
        
        # Get the page object for more detailed inspection
        # The browser object has contexts, and each context has pages
        page = None
        if async_browser.contexts:
            context = async_browser.contexts[0]
            if context.pages:
                page = context.pages[0]
        
        if page:
            print(f"📄 Page title: {await page.title()}")
            print(f"📄 Current URL: {page.url}")
        else:
            print("❌ No page found in browser context")
        
        # Extract content
        content = await extract_tool.arun({})
        print(f"📄 Content length: {len(content)} characters")
        
        # Show first 2000 characters to see what we're working with
        print("\n🔍 FIRST 2000 CHARACTERS:")
        print("-" * 30)
        print(content[:2000])
        print("-" * 30)
        
        # Get the actual HTML for detailed analysis
        print("\n🔍 GETTING ACTUAL HTML:")
        print("-" * 30)
        if page:
            html_content = await page.content()
            print(f"📄 HTML length: {len(html_content)} characters")
            
            # Parse with BeautifulSoup for better analysis
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for Reddit post links in the HTML
            print("\n🔍 BEAUTIFULSOUP ANALYSIS:")
            print("-" * 30)
            
            # Find all links
            all_links = soup.find_all('a', href=True)
            print(f"📎 Total links found: {len(all_links)}")
            
            # Filter for Reddit post links
            reddit_post_links = []
            for link in all_links:
                href = link.get('href', '')
                if '/comments/' in href and 'reddit.com' in href:
                    reddit_post_links.append({
                        'href': href,
                        'text': link.get_text(strip=True)[:100],
                        'class': link.get('class', []),
                        'id': link.get('id', ''),
                    })
            
            print(f"🔗 Reddit post links found: {len(reddit_post_links)}")
            for i, link_info in enumerate(reddit_post_links[:5]):
                print(f"  {i+1}. {link_info['href']}")
                print(f"     Text: {link_info['text']}")
                print(f"     Class: {link_info['class']}")
                print(f"     ID: {link_info['id']}")
            
            # Look for specific Reddit post containers
            print("\n🔍 LOOKING FOR REDDIT POST CONTAINERS:")
            print("-" * 30)
            
            # Common Reddit post selectors
            post_selectors = [
                "div.thing",
                "[data-testid='post-container']",
                ".Post",
                ".entry",
                ".link",
                "div[data-subreddit]",
                ".search-result",
            ]
            
            for selector in post_selectors:
                elements = soup.select(selector)
                print(f"✅ Selector '{selector}': Found {len(elements)} elements")
                
                if elements:
                    for i, element in enumerate(elements[:2]):
                        print(f"  Element {i+1}:")
                        print(f"    Classes: {element.get('class', [])}")
                        print(f"    ID: {element.get('id', '')}")
                        
                        # Look for links within this element
                        links_in_element = element.find_all('a', href=True)
                        print(f"    Links in element: {len(links_in_element)}")
                        
                        for j, link in enumerate(links_in_element[:3]):
                            href = link.get('href', '')
                            print(f"      Link {j+1}: {href}")
                            if '/comments/' in href:
                                print(f"        *** REDDIT POST LINK FOUND ***")
        else:
            print("❌ Cannot analyze HTML - no page available")
        
        # Try the official ExtractHyperlinksTool
        print("\n🔍 TRYING OFFICIAL EXTRACT_HYPERLINKS TOOL:")
        print("-" * 30)
        try:
            hyperlinks = await extract_hyperlinks_tool.arun({})
            print(f"✅ ExtractHyperlinksTool found {len(hyperlinks)} hyperlinks")
            
            # Show first 10 hyperlinks
            print("📎 First 10 hyperlinks:")
            for i, link in enumerate(hyperlinks[:10]):
                print(f"  {i+1}. {link}")
            
            # Filter for Reddit post links
            reddit_links = [link for link in hyperlinks if '/comments/' in link and 'reddit.com' in link]
            print(f"🔗 Found {len(reddit_links)} Reddit post links:")
            for i, link in enumerate(reddit_links[:5]):
                print(f"  {i+1}. {link}")
                
        except Exception as e:
            print(f"❌ Error with ExtractHyperlinksTool: {e}")
            import traceback
            traceback.print_exc()
        
        # Try different selectors with get_elements_tool
        print("\n🔍 TRYING DIFFERENT SELECTORS WITH GET_ELEMENTS:")
        print("-" * 30)
        
        selectors = [
            "div.thing .title a[href*='/comments/']",
            "a[href*='/comments/']",
            ".title a[href*='/comments/']",
            "[data-testid='post-container'] a[href*='/comments/']",
            "a[href*='reddit.com']",
            "a[href*='/r/toronto']",
            "div.thing a",  # All links in Reddit post containers
            ".search-result a",  # Search result links
        ]
        
        for selector in selectors:
            try:
                elements = await get_elements_tool.arun({"selector": selector})
                print(f"✅ Selector '{selector}': Found {len(elements)} elements")
                
                if elements and len(elements) > 0:
                    # Show first few elements
                    for i, element in enumerate(elements[:3]):
                        print(f"  Element {i+1}: {element}")
                        
                        if isinstance(element, dict):
                            print(f"    Keys: {list(element.keys())}")
                            if 'href' in element:
                                print(f"    href: {element['href']}")
                            if 'text' in element:
                                print(f"    text: {element['text'][:100]}...")
                        elif isinstance(element, str):
                            print(f"    String: {element[:100]}...")
                            
            except Exception as e:
                print(f"❌ Selector '{selector}' failed: {e}")
        
        # CUSTOM EXTRACTION METHOD
        print("\n🔍 CUSTOM EXTRACTION METHOD:")
        print("-" * 30)
        
        if page:
            # Use Playwright's built-in methods to get links
            try:
                # Get all links with href containing '/comments/'
                comment_links = await page.query_selector_all("a[href*='/comments/']")
                print(f"✅ Playwright found {len(comment_links)} comment links")
                
                reddit_urls = []
                for i, link in enumerate(comment_links[:10]):
                    try:
                        href = await link.get_attribute('href')
                        text = await link.text_content()
                        if href and 'reddit.com' in href:
                            reddit_urls.append({
                                'href': href,
                                'text': text.strip()[:100] if text else '',
                                'index': i
                            })
                            print(f"  {i+1}. {href}")
                            print(f"     Text: {text.strip()[:100] if text else ''}")
                    except Exception as e:
                        print(f"    Error getting link {i}: {e}")
                
                print(f"🔗 Total Reddit URLs found: {len(reddit_urls)}")
                
                # Also try getting all links and filtering
                all_links = await page.query_selector_all("a[href]")
                print(f"✅ Total links on page: {len(all_links)}")
                
                all_reddit_urls = []
                for i, link in enumerate(all_links):
                    try:
                        href = await link.get_attribute('href')
                        if href and 'reddit.com' in href and '/comments/' in href:
                            text = await link.text_content()
                            all_reddit_urls.append({
                                'href': href,
                                'text': text.strip()[:100] if text else '',
                                'index': i
                            })
                    except Exception as e:
                        continue
                
                print(f"🔗 All Reddit comment URLs found: {len(all_reddit_urls)}")
                for i, url_info in enumerate(all_reddit_urls[:5]):
                    print(f"  {i+1}. {url_info['href']}")
                    print(f"     Text: {url_info['text']}")
                
            except Exception as e:
                print(f"❌ Error with custom extraction: {e}")
                import traceback
                traceback.print_exc()
        
        # Look for any URLs in the content
        print("\n🔍 LOOKING FOR URLS IN CONTENT:")
        print("-" * 30)
        
        # Simple patterns
        patterns = [
            r'https?://[^\s<>"]+',
            r'/[^\s<>"]*comments/[^\s<>"]*',
            r'reddit\.com',
            r'/r/toronto',
            r'comments',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            print(f"Pattern '{pattern}': Found {len(matches)} matches")
            if matches:
                for i, match in enumerate(matches[:3]):
                    print(f"  {i+1}. {match}")
        
        # Check if we're on the right page
        print("\n🔍 PAGE VERIFICATION:")
        print("-" * 30)
        if page:
            print(f"Current URL: {page.url}")
            print(f"Page title: {await page.title()}")
            
            # Check for common Reddit elements
            reddit_elements = [
                "div.thing",
                ".search-result",
                "[data-testid='post-container']",
                ".Post",
            ]
            
            for element_selector in reddit_elements:
                try:
                    elements = await page.query_selector_all(element_selector)
                    print(f"✅ {element_selector}: {len(elements)} elements found")
                except Exception as e:
                    print(f"❌ {element_selector}: Error - {e}")
        else:
            print("❌ Cannot verify page - no page available")
        
        await async_browser.close()
        
    except Exception as e:
        print(f"❌ Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 STARTING HIDDEN GEMS DEBUG")
    print("=" * 50)
    
    asyncio.run(debug_hidden_gems())
