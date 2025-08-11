#!/usr/bin/env python3
"""
Debug script to examine what the hidden gems search actually returns
and verify if POIs are being extracted from actual Reddit content
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

async def debug_poi_extraction():
    """Debug POI extraction to verify if LLM is hallucinating"""
    print("🔍 DEBUGGING POI EXTRACTION - VERIFYING REDDIT CONTENT")
    print("=" * 60)
    
    try:
        # Initialize browser
        async_browser = create_async_playwright_browser(headless=False)
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        tools = toolkit.get_tools()
        
        # Get required tools
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        extract_tool = next(tool for tool in tools if tool.name == "extract_text")
        
        # Test URL - generic search for any city
        city = "Vancouver"  # Change this to test different cities
        subreddit = city.lower()
        test_url = f"https://old.reddit.com/r/{subreddit}/search/?q=hidden%20gems&restrict_sr=on&sort=relevance&t=all"
        print(f"🌐 Testing with city: {city}")
        print(f"🌐 Navigating to: {test_url}")
        
        # Navigate to Reddit search
        await navigate_tool.arun({"url": test_url})
        await asyncio.sleep(5)
        
        # Get the page object for direct Playwright access
        page = None
        if async_browser.contexts:
            context = async_browser.contexts[0]
            if context.pages:
                page = context.pages[0]
        
        if not page:
            print("❌ No page available")
            return
        
        print(f"📄 Page title: {await page.title()}")
        print(f"📄 Current URL: {page.url}")
        
        # Extract initial search results
        print("\n🔍 EXTRACTING INITIAL SEARCH RESULTS:")
        print("-" * 40)
        initial_content = await extract_tool.arun({})
        print(f"📄 Initial content length: {len(initial_content)} characters")
        
        # Show first 3000 characters to see what we're working with
        print("\n🔍 FIRST 3000 CHARACTERS OF SEARCH RESULTS:")
        print("-" * 40)
        print(initial_content[:3000])
        print("-" * 40)
        
        # Extract Reddit post URLs using our working method
        print("\n🔍 EXTRACTING REDDIT POST URLS:")
        print("-" * 40)
        
        # Import our working extraction function
        from agents.reddit_scraper import extract_reddit_post_urls_from_playwright
        post_urls = await extract_reddit_post_urls_from_playwright(page)
        
        print(f"✅ Found {len(post_urls)} Reddit post URLs")
        
        # Navigate to first 3 posts and extract their content
        detailed_content = []
        for i, post_url in enumerate(post_urls[:3]):
            try:
                print(f"\n🌐 Navigating to post {i+1}: {post_url[:60]}...")
                
                # Navigate to the post
                await navigate_tool.arun({"url": post_url})
                await asyncio.sleep(4)
                
                # Check if we successfully navigated
                new_url = page.url
                print(f"  📍 Actually navigated to: {new_url}")
                
                if "/comments/" in new_url:
                    print(f"  ✅ Successfully navigated to post page!")
                    
                    # Extract the full post content
                    print(f"  📄 Extracting content from post {i+1}...")
                    post_content = await extract_tool.arun({})
                    
                    if post_content and len(post_content) > 500:
                        print(f"  ✅ Extracted {len(post_content)} characters from post {i+1}")
                        
                        # Show first 2000 characters of this post
                        print(f"\n🔍 POST {i+1} CONTENT (first 2000 chars):")
                        print("-" * 30)
                        print(post_content[:2000])
                        print("-" * 30)
                        
                        detailed_content.append(f"=== POST {i+1} CONTENT ===\n{post_content}\n")
                    else:
                        print(f"  ⚠️ Post {i+1} had insufficient content")
                else:
                    print(f"  ❌ Failed to navigate to post page")
                
                # Go back to search results for next iteration
                print(f"  🔙 Going back to search results...")
                await navigate_tool.arun({"url": test_url})
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"❌ Error navigating to post {i+1}: {e}")
                continue
        
        # Combine all content
        if detailed_content:
            all_content = initial_content + "\n\n=== DETAILED POST CONTENT ===\n" + "\n".join(detailed_content)
            print(f"\n✅ Total content extracted: {len(all_content)} characters from {len(detailed_content)} posts")
        else:
            print("❌ No detailed content extracted from posts")
            all_content = initial_content
        
        # Now let's test what the LLM would extract from this content
        print("\n🔍 TESTING LLM POI EXTRACTION:")
        print("-" * 40)
        
        # Import the LLM and POI extraction logic
        from langchain_openai import ChatOpenAI
        from pydantic import BaseModel, Field
        from typing import List
        
        class POI(BaseModel):
            name: str = Field(description="Name of the point of interest")
            description: str = Field(description="Brief description of what makes this place special")
            category: str = Field(description="Category like 'museum', 'park', 'restaurant', 'attraction'")
            reddit_context: str = Field(description="Original Reddit content mentioning this place for authentic summary generation")

        class POIList(BaseModel):
            city: str = Field(description="The city being analyzed")
            pois: List[POI] = Field(description="List of points of interest found")
        
        # Create LLM
        llm = ChatOpenAI(model="gpt-4o-mini")
        llm_with_structured_output = llm.with_structured_output(POIList)
        
        # Test extraction with MORE AGGRESSIVE prompt
        extraction_prompt = f"""
        You are analyzing Reddit content to find COOL PLACES that people recommend visiting.

        GOAL: Find all the interesting, fun, and cool places that Reddit users recommend visiting.

        IMPORTANT: Extract ALL places that are mentioned positively in the provided Reddit content, especially places that people recommend or say are cool/fun.
        Be thorough and comprehensive - look for any place names, businesses, attractions, neighborhoods, etc. that people talk about positively.

        Here is the Reddit content to analyze:

        {all_content[:12000]}  # Increased to 12000 chars to get more content

        Extract ALL COOL PLACES mentioned in this content, including:
        - Restaurants, cafes, bars, food spots that people recommend
        - Museums, galleries, cultural venues that people say are interesting
        - Parks, trails, outdoor spaces that people recommend
        - Shopping centers, markets, boutiques that people mention positively
        - Entertainment venues, theaters, cinemas that people recommend
        - Tourist attractions, landmarks that people say are worth visiting
        - Local businesses and services that people recommend
        - Neighborhoods, districts, areas that people mention positively
        - Any specific place names with locations that people talk about positively

        For each place, provide:
        1. The exact name as mentioned
        2. A brief description based on what's said about it
        3. The category
        4. The specific Reddit context where it's mentioned

        Be comprehensive - extract as many cool places as you can find mentioned in the content.
        """
        
        try:
            print("🤖 Testing LLM extraction with aggressive prompt...")
            result = await llm_with_structured_output.ainvoke(extraction_prompt)
            
            print(f"✅ LLM extracted {len(result.pois)} POIs:")
            for i, poi in enumerate(result.pois):
                print(f"\n{i+1}. {poi.name}")
                print(f"   Category: {poi.category}")
                print(f"   Description: {poi.description}")
                print(f"   Reddit Context: {poi.reddit_context[:200]}...")
                
                # Check if this POI name appears in the actual content
                if poi.name.lower() in all_content.lower():
                    print(f"   ✅ VERIFIED: '{poi.name}' found in Reddit content")
                else:
                    print(f"   ❌ HALLUCINATION: '{poi.name}' NOT found in Reddit content!")
                    
        except Exception as e:
            print(f"❌ Error with LLM extraction: {e}")
            import traceback
            traceback.print_exc()
        
        # NEW: More aggressive extraction using regex patterns
        print("\n🔍 AGGRESSIVE REGEX EXTRACTION:")
        print("-" * 40)
        
        import re
        
        # Look for capitalized place names (likely proper nouns)
        capitalized_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Two word capitalized names
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # Three word capitalized names
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # Four word capitalized names
        ]
        
        # Look for specific place indicators
        place_indicators = [
            r'\b[A-Z][a-z]+ (Street|Avenue|Road|Boulevard|Drive|Lane|Place|Court|Terrace|Crescent)\b',
            r'\b[A-Z][a-z]+ (Park|Museum|Gallery|Theater|Theatre|Cinema|Restaurant|Cafe|Bar|Pub|Club)\b',
            r'\b[A-Z][a-z]+ (Market|Mall|Centre|Center|Plaza|Square|Building|Tower|Bridge|Station)\b',
            r'\b[A-Z][a-z]+ (Island|Beach|Trail|Path|Garden|Zoo|Aquarium|Stadium|Arena|Hall)\b',
        ]
        
        # Look for neighborhood patterns
        neighborhood_patterns = [
            r'\b[A-Z][a-z]+ (Village|Town|District|Area|Neighborhood|Neighbourhood|Quarter|Zone)\b',
            r'\b[A-Z][a-z]+ (East|West|North|South|Central|Downtown|Uptown|Midtown)\b',
        ]
        
        all_patterns = capitalized_patterns + place_indicators + neighborhood_patterns
        
        found_places = set()
        for pattern in all_patterns:
            matches = re.findall(pattern, all_content)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                # Filter out common words that aren't places
                common_words = ['Reddit', 'Toronto', 'Canada', 'Ontario', 'Personal', 'Please', 'Submit', 'Share', 'Reply', 'Comment', 'Post', 'User', 'Member', 'Online', 'Filter', 'Show', 'Hide', 'Sort', 'Best', 'Top', 'New', 'Old', 'Controversial', 'Q&A', 'More', 'Less', 'Points', 'Children', 'Permalink', 'Embed', 'Save', 'Parent', 'Report', 'Track', 'Me', 'Reply', 'Share', 'More', 'Replies', 'Sort', 'By', 'Best', 'Top', 'New', 'Controversial', 'Old', 'Q&A', 'Open', 'Comment', 'Options', 'Best', 'Top', 'New', 'Controversial', 'Old', 'Q&A', 'Hyper', 'Mill', 'Cat', 'Delicious', 'Nimble', 'Knees', 'YYZ', 'Tor', 'Crock', 'Pot', 'Seal', 'Sprungy', 'Fuji', 'Enthusiast', 'Ca', 'Jok', 'Kir', 'Black', 'Beats', 'Blue', 'Air', 'Dyson', 'Hepa', 'Filter', 'Bedroom', 'Entryway', 'Living', 'Space', 'Porch', 'Air', 'Filter', 'Neighbor', 'Stink', 'Cologne', 'Pigpen', 'Peanuts', 'Friend', 'Air', 'Freshener', 'CR', 'Box', 'CADR', 'Square', 'Feet', 'Single', 'Room', 'Condo', 'Small', 'Space', 'Air', 'Purifier', 'Respiratory', 'Issue', 'Covid', 'Acid', 'Reflux', 'Throat', 'Irritation', 'AQI', 'Scratchiness', 'Coughing', 'Fresh', 'Air', 'Filter', 'Car', 'Throat', 'Complains', 'Blue', 'Air', 'Dyson', 'Hepa', 'Filter', 'Bedroom', 'Entryway', 'Living', 'Space', 'Porch', 'Air', 'Filter', 'Neighbor', 'Stink', 'Cologne', 'Pigpen', 'Peanuts', 'Friend', 'Air', 'Freshener', 'CR', 'Box', 'CADR', 'Square', 'Feet', 'Single', 'Room', 'Condo', 'Small', 'Space', 'Air', 'Purifier', 'Respiratory', 'Issue', 'Covid', 'Acid', 'Reflux', 'Throat', 'Irritation', 'AQI', 'Scratchiness', 'Coughing', 'Fresh', 'Air', 'Filter', 'Car', 'Throat', 'Complains']
                if match not in common_words and len(match) > 3:
                    found_places.add(match)
        
        # Look for any place names mentioned in the content using generic patterns
        specific_places = []
        
        for place in specific_places:
            if place.lower() in all_content.lower():
                found_places.add(place)
        
        print(f"✅ Found {len(found_places)} potential places using aggressive regex:")
        for i, place in enumerate(sorted(found_places)[:20]):  # Show first 20
            print(f"  {i+1}. {place}")
        
        if len(found_places) > 20:
            print(f"  ... and {len(found_places) - 20} more places")
        
        # Also search for common POI names in the content
        print("\n🔍 SEARCHING FOR COMMON POI NAMES IN CONTENT:")
        print("-" * 40)
        
        # Look for any place names in the content
        common_pois = []
        
        found_pois = []
        for poi_name in common_pois:
            if poi_name.lower() in all_content.lower():
                found_pois.append(poi_name)
                print(f"✅ '{poi_name}' found in content")
                # Show context
                start_idx = all_content.lower().find(poi_name.lower())
                context = all_content[max(0, start_idx-50):start_idx+len(poi_name)+50]
                print(f"   Context: ...{context}...")
            else:
                print(f"❌ '{poi_name}' NOT found in content")
        
        print(f"\n📊 SUMMARY: Found {len(found_pois)} POIs in content: {found_pois}")
        
        # Search for any place names with patterns
        print("\n🔍 SEARCHING FOR PLACE NAME PATTERNS:")
        print("-" * 40)
        
        import re
        
        # Look for patterns that might indicate place names
        patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Two word capitalized names
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # Three word capitalized names
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',  # Four word capitalized names
        ]
        
        potential_places = []
        for pattern in patterns:
            matches = re.findall(pattern, all_content)
            for match in matches:
                # Filter out common non-place words
                if not any(word.lower() in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'been', 'they', 'were', 'said', 'will', 'would', 'could', 'should'] for word in match.split()):
                    potential_places.append(match)
        
        # Show unique potential places
        unique_places = list(set(potential_places))
        print(f"Found {len(unique_places)} potential place names:")
        for i, place in enumerate(unique_places[:20]):  # Show first 20
            print(f"  {i+1}. {place}")
        
        if len(unique_places) > 20:
            print(f"  ... and {len(unique_places) - 20} more")
        
        # SIMPLE EXTRACTION TEST - JUST FIND PLACES
        print("\n🔍 SIMPLE EXTRACTION TEST - JUST FIND PLACES:")
        print("-" * 40)
        
        simple_extraction_prompt = f"""
        Find ALL place names mentioned in this Reddit content about Toronto.
        
        Just list the place names. Don't worry about descriptions or categories.
        Look for:
        - Restaurant names
        - Bar names  
        - Neighborhood names
        - Street names
        - Building names
        - Park names
        - Any other place names
        
        Content: {all_content[:10000]}
        
        Return a simple list of place names found in the content.
        """
        
        try:
            simple_response = await llm.ainvoke(simple_extraction_prompt)
            print("🤖 Simple extraction response:")
            print(simple_response.content)
        except Exception as e:
            print(f"❌ Error with simple extraction: {e}")
        
        # MANUAL SEARCH FOR SPECIFIC PLACES
        print("\n🔍 MANUAL SEARCH FOR GENERIC PLACE PATTERNS:")
        print("-" * 40)
        
        specific_places = []
        
        found_specific = []
        for place in specific_places:
            if place.lower() in all_content.lower():
                found_specific.append(place)
                print(f"✅ '{place}' found in content")
                # Show context
                start_idx = all_content.lower().find(place.lower())
                context = all_content[max(0, start_idx-100):start_idx+len(place)+100]
                print(f"   Context: ...{context}...")
            else:
                print(f"❌ '{place}' NOT found in content")
        
        print(f"\n📊 FOUND {len(found_specific)} SPECIFIC PLACES: {found_specific}")
        
        # SEARCH FOR ANY CAPITALIZED WORDS THAT MIGHT BE PLACES
        print("\n🔍 SEARCHING FOR CAPITALIZED PLACE NAMES:")
        print("-" * 40)
        
        import re
        
        # Find all capitalized words that might be place names
        capitalized_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        capitalized_matches = re.findall(capitalized_pattern, all_content)
        
        # Filter out common non-place words
        non_place_words = {
            'the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'been', 
            'they', 'were', 'said', 'will', 'would', 'could', 'should', 'what',
            'when', 'where', 'why', 'how', 'who', 'which', 'there', 'here',
            'about', 'after', 'before', 'during', 'since', 'until', 'while',
            'because', 'although', 'unless', 'whether', 'though', 'even',
            'just', 'only', 'even', 'still', 'already', 'never', 'always',
            'often', 'sometimes', 'usually', 'rarely', 'seldom', 'hardly',
            'almost', 'nearly', 'quite', 'very', 'really', 'extremely',
            'absolutely', 'completely', 'totally', 'entirely', 'wholly',
            'partly', 'mostly', 'mainly', 'primarily', 'especially',
            'particularly', 'specifically', 'exactly', 'precisely',
            'definitely', 'certainly', 'surely', 'obviously', 'clearly',
            'apparently', 'evidently', 'seemingly', 'supposedly', 'allegedly'
        }
        
        potential_places = []
        for match in capitalized_matches:
            words = match.split()
            # Skip if any word is in the non-place list
            if not any(word.lower() in non_place_words for word in words):
                potential_places.append(match)
        
        # Count occurrences and show most common
        from collections import Counter
        place_counts = Counter(potential_places)
        
        print(f"Found {len(place_counts)} unique potential place names:")
        for place, count in place_counts.most_common(20):
            print(f"  {place} ({count} times)")
        
        if len(place_counts) > 20:
            print(f"  ... and {len(place_counts) - 20} more")
        
        await async_browser.close()
        
    except Exception as e:
        print(f"❌ Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 STARTING POI EXTRACTION DEBUG")
    print("=" * 60)
    
    asyncio.run(debug_poi_extraction())
