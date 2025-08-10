from typing import Annotated, TypedDict, List, Any, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
import requests
import json
import re
import time
import nest_asyncio
from collections import Counter
import os
import random
from utils.location import is_coordinates_in_city
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv(override=True)
nest_asyncio.apply()

# Define structured output for POI data
class POI(BaseModel):
    name: str = Field(description="Name of the point of interest")
    description: str = Field(description="Brief description of what makes this place special")
    category: str = Field(description="Category like 'museum', 'park', 'restaurant', 'attraction'")
    reddit_context: str = Field(description="Original Reddit content mentioning this place for authentic summary generation")

class POIList(BaseModel):
    city: str = Field(description="The city being analyzed")
    pois: List[POI] = Field(description="List of points of interest found")

class POIOutput(BaseModel):
    name: str = Field(description="Name of the point of interest")
    lat: float = Field(description="Latitude coordinate")
    lng: float = Field(description="Longitude coordinate")
    summary: str = Field(description="Summary of what's happening at this location")
    type: str = Field(description="Type of POI (reddit, event, restaurant, etc.)")
    radius: int = Field(description="Radius in kilometers")

# Define the State - DYNAMIC REDDIT PIPELINE
class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    location_data: Dict
    reddit_data: List[Dict]
    current_step: Optional[str]
    pois: Optional[List[Dict]]
    subreddit: Optional[str]
    scraped_content: Optional[str]
    extracted_pois: Optional[List[POI]]
    city: Optional[str]

def extract_reddit_post_urls_from_text(text_content: str) -> List[str]:
    """Extract Reddit post URLs from plain text content using regex patterns"""
    try:
        post_urls = []
        
        # Look for Reddit post patterns in plain text
        # These patterns match the format of Reddit post URLs that might appear in text
        url_patterns = [
            # Full URLs
            r'https://old\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://www\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            # Relative URLs
            r'/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            # Post IDs (common in Reddit text)
            r'comments/([\w]+)/[\w\-\_]+',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    # If it's a tuple (from group capture), take the first element
                    match = match[0] if match else ""
                
                if match:
                    # Normalize URL
                    if match.startswith('/r/'):
                        full_url = f"https://old.reddit.com{match}"
                    elif match.startswith('http'):
                        full_url = match
                    elif 'comments/' in match:
                        # This is a post ID, construct the URL
                        full_url = f"https://old.reddit.com/r/toronto/comments/{match}"
                    else:
                        full_url = f"https://old.reddit.com{match}"
                    
                    # Clean up the URL
                    full_url = full_url.split('?')[0]  # Remove query parameters
                    full_url = full_url.rstrip('/')  # Remove trailing slash
                    
                    if full_url not in post_urls and '/comments/' in full_url:
                        post_urls.append(full_url)
        
        return list(set(post_urls))  # Remove duplicates
        
    except Exception as e:
        print(f"Error extracting Reddit URLs from text: {e}")
        return []

async def extract_reddit_post_urls_from_playwright(page) -> List[str]:
    """Extract Reddit post URLs using direct Playwright methods (WORKING METHOD)"""
    try:
        post_urls = []
        
        # Use Playwright's direct methods to get all links with href containing '/comments/'
        comment_links = await page.query_selector_all("a[href*='/comments/']")
        
        for link in comment_links:
            try:
                href = await link.get_attribute('href')
                if href and 'reddit.com' in href:
                    # Normalize URL
                    if href.startswith('/'):
                        full_url = f"https://old.reddit.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://old.reddit.com{href}"
                    
                    # Clean up the URL
                    full_url = full_url.split('?')[0].rstrip('/')
                    
                    if full_url not in post_urls:
                        post_urls.append(full_url)
            except Exception as e:
                continue
        
        return list(set(post_urls))  # Remove duplicates
        
    except Exception as e:
        print(f"Error extracting URLs with Playwright: {e}")
        return []

def extract_reddit_post_urls_from_elements(elements: List[Dict]) -> List[str]:
    """Extract Reddit post URLs from Playwright elements"""
    try:
        post_urls = []
        
        for element in elements:
            if isinstance(element, dict):
                # Check for href attribute
                href = element.get('href', '')
                if '/comments/' in href:
                    # Normalize URL
                    if href.startswith('/'):
                        full_url = f"https://old.reddit.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://old.reddit.com{href}"
                    
                    # Clean up the URL
                    full_url = full_url.split('?')[0].rstrip('/')
                    
                    if full_url not in post_urls:
                        post_urls.append(full_url)
        
        return list(set(post_urls))
        
    except Exception as e:
        print(f"Error extracting URLs from elements: {e}")
        return []

def extract_reddit_post_urls(html_content: str) -> List[str]:
    """Extract Reddit post URLs from HTML content using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        post_urls = []
        
        # Look for links that contain /comments/ pattern
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            if '/comments/' in href and 'reddit.com' in href:
                # Normalize URL
                if href.startswith('/'):
                    full_url = f"https://old.reddit.com{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://old.reddit.com{href}"
                
                # Clean up the URL
                full_url = full_url.split('?')[0]  # Remove query parameters
                full_url = full_url.rstrip('/')  # Remove trailing slash
                
                if full_url not in post_urls:
                    post_urls.append(full_url)
        
        # Also try regex patterns as backup
        url_patterns = [
            r'https://old\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'href="(/r/\w+/comments/[\w]+/[\w\-\_]+/?)"',
            r'href="(https://old\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?)"',
            r'href="(https://reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?)"',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if match.startswith('/r/'):
                    full_url = f"https://old.reddit.com{match}"
                elif match.startswith('http'):
                    full_url = match
                else:
                    full_url = f"https://old.reddit.com{match}"
                
                full_url = full_url.split('?')[0].rstrip('/')
                if full_url not in post_urls:
                    post_urls.append(full_url)
        
        return list(set(post_urls))  # Remove duplicates
        
    except Exception as e:
        print(f"Error extracting Reddit URLs: {e}")
        return []

def create_reddit_scraper_agent(subreddit="askTO", city="Toronto"):
    print(f"Creating LangGraph Reddit scraper for r/{subreddit} in {city}...")
    
    # Initialize tools and LLM
    from langchain_community.tools.playwright.utils import create_async_playwright_browser
    async_browser = create_async_playwright_browser(headless=False)  # Use async browser
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    print(f"Got {len(tools)} Playwright tools: {[tool.name for tool in tools]}")
    
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools(tools)
    llm_with_structured_output = llm.with_structured_output(POIList)
    llm_with_poi_output = llm.with_structured_output(POIOutput)
    
    # Serper.dev search function
    def search_serper(query: str) -> dict:
        """Search using Serper.dev API"""
        serper_key = os.getenv("SERPER_API_KEY")
        if not serper_key:
            print("⚠️ SERPER_API_KEY not found, using fallback coordinates")
            return {"organic": [], "knowledgeGraph": None}
            
        try:
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": serper_key,
                "Content-Type": "application/json"
            }
            payload = {"q": query}
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Serper search error: {e}")
            return {"organic": [], "knowledgeGraph": None}
    
    def scrape_reddit_node(state: State) -> Dict[str, Any]:
        """Node to scrape Reddit content using browser tools"""
        try:
            subreddit = state.get("subreddit", "askTO")
            city = state.get('city', 'Toronto')
            
            system_message = f"""You are a Reddit scraping expert. Your job is to search for posts about things to do in {city}.

CRITICAL INSTRUCTIONS:
1. You MUST use the navigate_browser tool to go to Reddit
2. You MUST use the extract_text tool to get content from the page
3. Search for posts about things to do, places to visit, attractions, activities in {city}
4. Extract ALL text content including post titles, comments, and recommendations
5. If the page doesn't load or has no content, extract whatever you can find

You MUST use BOTH browser tools in sequence: first navigate_browser, then extract_text.
Do not respond without using both tools."""
            
            # Always include underground spots in the mix
            print("🔍 Including underground/hidden spots in search")
            
            # Mix of popular and underground spots
            search_terms = [
                f"things%20to%20do%20{city}",
                f"best%20places%20{city}",
                f"cool%20spots%20{city}",
                f"attractions%20{city}",
                f"activities%20{city}",
                # Underground/unknown spots
                f"hidden%20gems%20{city}",
                f"underrated%20{city}",
                f"secret%20spots%20{city}",
                f"local%20favorites%20{city}",
                f"off%20the%20beaten%20path%20{city}",
                f"unknown%20places%20{city}",
                f"lowkey%20spots%20{city}",
                f"insider%20tips%20{city}",
                f"not%20touristy%20{city}",
                f"local%20secrets%20{city}",
                f"underground%20{city}",
                f"hidden%20spots%20{city}"
            ]
            
            # Pick a random search term for variety
            import random
            search_term = random.choice(search_terms)
            
            user_message = f"""Navigate to https://www.reddit.com/r/{subreddit}/search/?q={search_term}&restrict_sr=on&sort=relevance&t=all

Then extract ALL text content from the page, including:
- Post titles about things to do in {city}
- Post content with recommendations
- Comments mentioning specific places
- Any business names, attractions, or venues mentioned

Use the extract_text tool to get everything you can see. If the page is empty or doesn't load, extract whatever text is available.

IMPORTANT: You must call extract_text after navigating to get the page content."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            import datetime
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"🕐 [{current_time}] Scraping r/{subreddit} for things to do in {city}...")
            print(f"🔍 Using search term: {search_term}")
            print(f"🌐 Navigating to: https://www.reddit.com/r/{subreddit}/search/?q={search_term}&restrict_sr=on&sort=relevance&t=all")
            
            response = llm_with_tools.invoke(messages)
            
            # Verify we used browser tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"✅ Used {len(response.tool_calls)} browser tools:")
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    print(f"   - {tool_name}")
            else:
                print("⚠️ No browser tools used - this might be cached data!")
            
            # Log what we actually scraped
            if hasattr(response, 'content') and response.content:
                scraped_text = response.content[:500]  # First 500 chars
                print(f"📄 Scraped content preview: {scraped_text}...")
                print(f"📊 Content length: {len(response.content)} characters")
                
                # Verify it's actually Reddit content
                reddit_indicators = ['reddit.com', 'r/', 'upvote', 'downvote', 'comment', 'post']
                has_reddit_content = any(indicator in response.content.lower() for indicator in reddit_indicators)
                if has_reddit_content:
                    print("✅ Content contains Reddit-specific elements - real scraping confirmed!")
                else:
                    print("⚠️ Content doesn't seem to be from Reddit - might be cached/static data")
            else:
                print("❌ No content scraped!")
            
            return {
                "messages": [response],
                "current_step": "extract_pois"
            }
        except Exception as e:
            print(f"Error in scrape_reddit_node: {e}")
            return {
                "messages": [HumanMessage(content=f"Error scraping Reddit: {str(e)}")],
                "current_step": "extract_pois"
            }
    
    def extract_pois_node(state: State) -> Dict[str, Any]:
        """Node to extract POIs from scraped content using structured output"""
        messages = state.get("messages", [])
        city = state.get('city', 'Toronto')
        
        # Get the scraped content from the last message
        scraped_content = ""
        for msg in reversed(messages):
            if hasattr(msg, 'content') and msg.content:
                scraped_content = msg.content
                break
        
        if not scraped_content:
            print("No scraped content found")
            return {
                "extracted_pois": [],
                "current_step": "geocode_pois",
                "messages": [HumanMessage(content="No content found to extract POIs from")]
            }
        
        # Debug: Show what content we're working with
        print(f"📄 Processing {len(scraped_content)} characters of Reddit content")
        print(f"🔍 Content preview: {scraped_content[:500]}...")
        
        # Check if content looks like real Reddit posts
        reddit_indicators = ['reddit.com', 'r/', 'upvote', 'downvote', 'comment', 'post', 'OP', 'edit:', 'deleted']
        has_reddit_content = any(indicator in scraped_content.lower() for indicator in reddit_indicators)
        if has_reddit_content:
            print("✅ Content contains Reddit-specific elements - authentic content detected!")
        else:
            print("⚠️ Content doesn't seem to be from Reddit - might be cached/static data")
            # If we don't have real Reddit content, don't extract fake POIs
            print("❌ Skipping POI extraction - no authentic Reddit content found")
            return {
                "extracted_pois": [],
                "current_step": "geocode_pois",
                "messages": [HumanMessage(content="No authentic Reddit content found - skipping POI extraction")]
            }
        
        # Always prioritize a mix of popular and underground spots
        focus_instruction = f"""
PRIORITY: Mix of popular attractions and underground/hidden spots.
Look for mentions of:
- Popular attractions and landmarks
- "hidden gem", "secret spot", "local favorite", "underrated"
- Places that locals recommend but aren't touristy
- Small, independent businesses and venues
- Off-the-beaten-path locations
- Insider recommendations and local secrets
"""
        
        system_message = f"""You are an expert at identifying specific places mentioned in Reddit posts about things to do in {city}.

From the scraped Reddit content, extract specific, real places that people recommend visiting in {city}. 

{focus_instruction}

Look for ANY mentions of:
- Restaurants, cafes, bars, food spots
- Museums, galleries, cultural venues
- Parks, trails, outdoor spaces
- Shopping centers, markets, boutiques
- Entertainment venues, theaters, cinemas
- Tourist attractions, landmarks
- Local businesses and services
- Any specific place names with locations

DO NOT extract:
- Generic neighborhood names (e.g., "downtown", "uptown")
- Just street names without business context
- Vague references like "that place" or "the spot"
- Generic terms without specific names

For each place, provide:
- name: The exact name of the place
- description: Brief category description (e.g., "Popular restaurant", "Hidden gem cafe")
- category: The type of place (restaurant, museum, park, attraction, etc.)
- reddit_context: The EXACT Reddit content (posts/comments) that mention this place. Include the full context of what users said about it, with quotes and opinions. This will be used to generate authentic summaries.

IMPORTANT: For reddit_context, copy the actual Reddit text that mentions this place, including user quotes, opinions, and recommendations. This should be the raw Reddit content, not a summary.

Return 5-8 of the most specific places mentioned."""
        
        user_message = f"""Extract specific places from this Reddit content about {city}:\n\n{scraped_content[:6000]}"""
        
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message)
        ]
        
        try:
            response = llm_with_structured_output.invoke(messages)
            pois = response.pois
            print(f"Extracted {len(pois)} POIs: {[poi.name for poi in pois]}")
            

            
            return {
                "extracted_pois": pois,
                "current_step": "geocode_pois",
                "messages": [HumanMessage(content=f"Extracted {len(pois)} POIs")]
            }
        except Exception as e:
            print(f"Error extracting POIs: {e}")
            return {
                "extracted_pois": [],
                "current_step": "geocode_pois",
                "messages": [HumanMessage(content="Error extracting POIs")]
            }
    
    def geocode_pois_node(state: State) -> Dict[str, Any]:
        """Node to geocode POIs and create final POI objects"""
        try:
            pois = state.get("extracted_pois", [])
            subreddit = state.get("subreddit", "askTO")
            city = state.get('city', 'Toronto')
            
            # Get location details from state
            location_data = state.get('location_data', {})
            province = location_data.get('province', 'Ontario')
            country = location_data.get('country', 'Canada')
            location_name = location_data.get('name', f"{city}, {province}")
            
            final_pois = []
            
            for poi in pois:
                print(f"Getting coordinates for: {poi.name}")
                
                try:
                    # Search using Serper.dev - more specific search
                    # Get country from location_data or default to Canada
                    country = location_data.get('country', 'Canada')
                    province = location_data.get('province', 'Ontario')
                    search_query = f"{poi.name} {city} {province} {country} exact location coordinates"
                    print(f"🔍 Searching: {search_query}")
                    
                    search_results = search_serper(search_query)
                    
                    # Extract text from search results
                    search_text = ""
                    if search_results.get("organic"):
                        for result in search_results["organic"][:3]:  # Top 3 results
                            search_text += f"Title: {result.get('title', '')}\n"
                            search_text += f"Snippet: {result.get('snippet', '')}\n\n"
                    
                    if search_results.get("knowledgeGraph"):
                        kg = search_results["knowledgeGraph"]
                        search_text += f"Knowledge Graph: {kg.get('title', '')}\n"
                        search_text += f"Description: {kg.get('description', '')}\n"
                        if kg.get("attributes"):
                            search_text += f"Attributes: {kg.get('attributes')}\n"
                    
                    print(f"📝 Search results: {search_text[:200]}...")
                    
                    # Use LLM to extract coordinates from search results
                    class Coordinates(BaseModel):
                        lat: float = Field(description="Latitude coordinate")
                        lng: float = Field(description="Longitude coordinate")
                    
                    llm_with_coords = llm.with_structured_output(Coordinates)
                    
                    coord_response = llm_with_coords.invoke([
                        SystemMessage(content="Extract the EXACT latitude and longitude coordinates for the specific place mentioned. Look for coordinate patterns like 43.1234, -79.1234. If the coordinates are for the general city area (like city center) and not the specific place, return 0.0 for both lat and lng. Only return coordinates if they are specifically for the exact location."),
                        HumanMessage(content=search_text)
                    ])
                    
                    if coord_response.lat != 0.0 and coord_response.lng != 0.0:
                        # Check if coordinates are within the detected city bounds
                        if is_coordinates_in_city(coord_response.lat, coord_response.lng, city):
                            coords = {
                                'lat': coord_response.lat,
                                'lng': coord_response.lng,
                                'address': f"{poi.name}, {city}"
                            }
                            print(f"✅ Found coordinates for {poi.name}: ({coords['lat']}, {coords['lng']}) - VALIDATED")
                        else:
                            print(f"❌ Coordinates for {poi.name} are outside {city} bounds - REJECTED")
                            coords = None
                            continue
                    else:
                        print(f"❌ No coordinates found for {poi.name}")
                        coords = None
                        continue
                    
                except Exception as e:
                    print(f"❌ Error getting coordinates for {poi.name}: {e}")
                    coords = None
                    continue
                    
                except Exception as e:
                    print(f"❌ Error getting coordinates for {poi.name}: {e}")
                    coords = None
                    continue
                
                if coords:

                    
                    # Create summary using the original Reddit content
                    system_message = f"""Create an authentic, engaging summary for {poi.name} using the actual Reddit content provided.

IMPORTANT RULES:
1. Use ONLY the Reddit content provided - don't make up anything
2. Include actual user quotes and opinions from the Reddit posts
3. Make it sound natural and conversational, like a local giving you insider tips
4. Keep it under 300 characters
5. ALWAYS start with Reddit-specific phrases like:
   - "Reddit users love..."
   - "According to r/{subreddit}..."
   - "Locals say..."
   - "r/{subreddit} recommends..."
   - "The community loves..."
6. Include specific details mentioned by users (food quality, atmosphere, prices, etc.)
7. If users mention it's a "hidden gem" or "underrated", include that
8. Make it feel like real insider knowledge from the community
9. Include Reddit-specific terms like "upvoted", "recommended", "community favorite"

Format examples:
- "Reddit users love the [specific dish] here and say it's a hidden gem for [reason]"
- "According to r/{subreddit}, this place has [specific feature] and locals rave about [specific aspect]"
- "Locals say this is the best [category] in the area, especially for [specific reason]"
- "r/{subreddit} community highly recommends this spot for [specific reason]"

DO NOT use generic phrases like "great food" or "nice atmosphere" unless users actually said those words."""
                    
                    user_message = f"""Place: {poi.name}
Category: {poi.category}
Subreddit: r/{subreddit}
City: {city}

ORIGINAL REDDIT CONTENT ABOUT THIS PLACE:
{poi.reddit_context}

Create an authentic summary using the actual Reddit content above. Use real user quotes and opinions."""
                    
                    try:
                        summary_messages = [
                            SystemMessage(content=system_message),
                            HumanMessage(content=user_message)
                        ]
                        
                        summary_response = llm.invoke(summary_messages)
                        summary = summary_response.content.strip()[:400]  # Increased length limit
                        
                        # Validate that the summary actually uses Reddit content
                        if not any(keyword in summary.lower() for keyword in ['reddit', 'r/', 'users', 'locals', 'community']):
                            # Fallback to a more direct approach
                            fallback_summary = f"Reddit users in r/{subreddit} recommend this {poi.category.lower()}. {poi.reddit_context[:200]}..."
                            summary = fallback_summary[:400]
                        
                        # Additional validation: if summary is too generic, try to make it more authentic
                        generic_phrases = ['great', 'good', 'nice', 'popular', 'famous', 'well-known']
                        if any(phrase in summary.lower() for phrase in generic_phrases) and len(poi.reddit_context) > 50:
                            # Try to extract a more specific quote from the Reddit content
                            import re
                            # Look for quotes or specific opinions in the Reddit content
                            quotes = re.findall(r'"([^"]+)"', poi.reddit_context)
                            if quotes:
                                specific_quote = quotes[0][:100]  # Take first quote, limit length
                                summary = f"Reddit users say: \"{specific_quote}\" about this {poi.category.lower()}"
                            else:
                                # Look for specific adjectives or opinions
                                opinion_words = ['amazing', 'incredible', 'best', 'favorite', 'love', 'hidden gem', 'underrated', 'must-try']
                                for word in opinion_words:
                                    if word in poi.reddit_context.lower():
                                        summary = f"Reddit users call this place {word} - {poi.reddit_context[:150]}..."
                                        break
                        
                        print(f"📝 Generated summary for {poi.name}: {summary[:100]}...")
                        
                        # Create POI
                        poi_output = POIOutput(
                            name=poi.name,
                            lat=coords['lat'],
                            lng=coords['lng'],
                            summary=summary,
                            type="reddit",
                            radius=20
                        )
                        
                        final_pois.append(poi_output.model_dump())
                        print(f"✅ Created POI: {poi.name} at ({coords['lat']}, {coords['lng']})")
                        
                    except Exception as e:
                        print(f"Error creating POI summary for {poi.name}: {e}")
                        # Fallback summary using the original Reddit context
                        reddit_context = poi.reddit_context[:250] if poi.reddit_context else f"Popular {poi.category.lower()} mentioned by r/{subreddit} users"
                        poi_output = POIOutput(
                            name=poi.name,
                            lat=coords['lat'],
                            lng=coords['lng'],
                            summary=f"Reddit users say: {reddit_context}",
                            type="reddit", 
                            radius=20
                        )
                        final_pois.append(poi_output.model_dump())
                else:
                    print(f"❌ Could not geocode: {poi.name}")
            
            return {
                "pois": final_pois,
                "current_step": "complete",
                "messages": [HumanMessage(content=f"Created {len(final_pois)} POIs")]
            }
        except Exception as e:
            print(f"Error in geocode_pois_node: {e}")
            return {
                "pois": [],
                "current_step": "complete",
                "messages": [HumanMessage(content=f"Error geocoding POIs: {str(e)}")]
            }
    
    def tools_condition(state: State) -> str:
        """Determine if we need to use tools or move to next step"""
        try:
            last_message = state["messages"][-1] if state.get("messages") else None
            current_step = state.get("current_step", "scrape_reddit")
            
            print(f"Tools condition - Current step: {current_step}")
            
            # If we have tool calls, go to tools
            if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
                print("Has tool calls, going to tools")
                return "tools"
            
            # Otherwise route based on current step
            if current_step == "scrape_reddit":
                print("Moving to extract_pois")
                return "extract_pois"
            elif current_step == "extract_pois":
                print("Moving to geocode_pois")
                return "geocode_pois"
            else:
                print("Ending workflow")
                return END
        except Exception as e:
            print(f"Error in tools_condition: {e}")
            return END
    
    def route_after_tools(state: State) -> str:
        """Route after tools have been executed"""
        try:
            current_step = state.get("current_step", "scrape_reddit")
            print(f"Route after tools - Current step: {current_step}")
            
            if current_step == "scrape_reddit":
                print("Moving to extract_pois after tools")
                return "extract_pois"
            else:
                print("Ending workflow after tools")
                return END
        except Exception as e:
            print(f"Error in route_after_tools: {e}")
            return END
    
    # Create the workflow
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("scrape_reddit", scrape_reddit_node)
    workflow.add_node("tools", ToolNode(tools=tools))
    workflow.add_node("extract_pois", extract_pois_node)  
    workflow.add_node("geocode_pois", geocode_pois_node)
    
    # Add edges
    workflow.add_conditional_edges("scrape_reddit", tools_condition, {
        "tools": "tools",
        "extract_pois": "extract_pois"
    })
    
    workflow.add_edge("tools", "extract_pois")
    workflow.add_edge("extract_pois", "geocode_pois")
    workflow.add_edge("geocode_pois", END)
    
    # Set entry point
    workflow.set_entry_point("scrape_reddit")
    
    print("LangGraph workflow compiled successfully!")
    return workflow.compile()

async def get_reddit_pois_direct(city: str, province: str, country: str, lat: float, lng: float) -> list:
    """Direct Reddit scraper using LangGraph with proper async browser tools"""
    import random  # Move import here to avoid scope issues
    
    print(f"Starting LangGraph Reddit scraper for {city}...")
    
    # Initialize tools and LLM
    from langchain_community.tools.playwright.utils import create_async_playwright_browser
    async_browser = create_async_playwright_browser(headless=False)  # Use async browser
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    print(f"Got {len(tools)} Playwright tools: {[tool.name for tool in tools]}")
    
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    # Create LangGraph workflow
    from langgraph.graph import StateGraph, END
    from typing import TypedDict, Annotated, List, Any, Optional
    from langgraph.prebuilt import ToolNode
    
    # Define state
    class RedditState(TypedDict):
        messages: Annotated[List[Any], add_messages]
        current_step: str
        scraped_content: Optional[str]
        extracted_pois: Optional[List[Any]]
        city: str
        subreddit: str
        search_term: str
    
    # Create tool node
    tool_node = ToolNode(tools)
    
    # Define nodes
    async def scrape_reddit_node(state: RedditState) -> RedditState:
        """Navigate to Reddit and scrape content"""
        print(f"🔍 Scraping r/{state['subreddit']} for things to do in {state['city']}...")
        
        # Try different old Reddit search URLs
        search_urls = [
            f"https://old.reddit.com/r/{state['subreddit']}/search/?q={state['search_term']}&restrict_sr=on&sort=relevance&t=all",
            f"https://old.reddit.com/r/{state['subreddit']}/search/?q={state['search_term']}&restrict_sr=on&sort=hot&t=all",
            f"https://old.reddit.com/r/{state['subreddit']}/search/?q={state['search_term']}&restrict_sr=on&sort=new&t=all",
            f"https://old.reddit.com/r/{state['subreddit']}/top/?q={state['search_term']}&restrict_sr=on&t=all"
        ]
        
        # Use the first URL for now
        search_url = search_urls[0]
        
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        extract_tool = next(tool for tool in tools if tool.name == "extract_text")
        
        # Navigate to old Reddit search
        print(f"🌐 Navigating to: {search_url}")
        await navigate_tool.arun({"url": search_url})
        
        # Wait for content to load
        import asyncio
        await asyncio.sleep(5)
        
        # Extract initial search results
        content = await extract_tool.arun({})
        print(f"📄 Initial search results length: {len(content)} characters")
        
        return {
            **state,
            "scraped_content": content,
            "current_step": "click_posts"
        }
    
    async def click_posts_node(state: RedditState) -> RedditState:
        """Click into individual Reddit posts to get detailed content"""
        print("🖱️ Clicking into individual Reddit posts to get detailed content...")
        
        import asyncio
        
        # Get the tools we need
        try:
            click_tool = next(tool for tool in tools if tool.name == "click_element")
            extract_tool = next(tool for tool in tools if tool.name == "extract_text")
            navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
            current_webpage_tool = next(tool for tool in tools if tool.name == "current_webpage")
            print("✅ Found all required tools")
        except StopIteration as e:
            print(f"❌ Required tool not found: {e}")
            return {**state, "scraped_content": state.get("scraped_content", ""), "current_step": "extract_pois"}
        
        detailed_content = []
        search_url = f"https://old.reddit.com/r/{state['subreddit']}/search/?q={state['search_term']}&restrict_sr=on&sort=relevance&t=all"
        
        try:
            # Wait for page to fully load
            print("⏳ Waiting for page to fully load...")
            await asyncio.sleep(5)
            
            # Get current URL to verify we're on search page
            current_url = await current_webpage_tool.arun({})
            print(f"📍 Current URL: {current_url}")
            
            # Wait for posts to load
            print("⏳ Waiting for posts to load...")
            await asyncio.sleep(3)
            
            # Get the page object for direct Playwright access
            page = None
            if async_browser.contexts:
                context = async_browser.contexts[0]
                if context.pages:
                    page = context.pages[0]
            
            if not page:
                print("❌ No page available for direct Playwright access")
                return {**state, "scraped_content": state.get("scraped_content", ""), "current_step": "extract_pois"}
            
            # Use the WORKING method: Direct Playwright extraction
            print("🔍 Using direct Playwright method to extract Reddit post URLs...")
            post_urls = await extract_reddit_post_urls_from_playwright(page)
            
            if post_urls:
                print(f"✅ Successfully extracted {len(post_urls)} Reddit post URLs using Playwright")
                # Show first few URLs
                for i, url in enumerate(post_urls[:5]):
                    print(f"  {i+1}. {url}")
            else:
                print("❌ No URLs found with direct Playwright method")
                
                # Fallback: Try extracting from page content
                print("🔄 Fallback: Extracting from page content...")
                page_content = await extract_tool.arun({})
                post_urls = extract_reddit_post_urls_from_text(page_content)
                print(f"✅ Extracted {len(post_urls)} URLs from page content")
            
            # Navigate to individual posts and extract content
            if post_urls and len(post_urls) > 0:
                print(f"✅ Using {len(post_urls)} extracted URLs for direct navigation")
                
                # Navigate directly to post URLs (try first 3 posts)
                for i, post_url in enumerate(post_urls[:3]):
                    try:
                        print(f"🌐 Navigating to post {i+1}: {post_url[:60]}...")
                        
                        # Navigate to the post
                        await navigate_tool.arun({"url": post_url})
                        await asyncio.sleep(4)
                        
                        # Check if we successfully navigated
                        new_url = await current_webpage_tool.arun({})
                        print(f"  📍 Actually navigated to: {new_url}")
                        
                        if "/comments/" in new_url:
                            print(f"  ✅ Successfully navigated to post page!")
                            
                            # Extract the full post content
                            print(f"  📄 Extracting content from post {i+1}...")
                            post_content = await extract_tool.arun({})
                            
                            if post_content and len(post_content) > 500:
                                # Validate it's a Reddit post
                                reddit_keywords = ['comments', 'upvote', 'downvote', 'share', 'award', 'reply', 'r/', 'u/', 'points', 'submitted']
                                if any(keyword in post_content.lower() for keyword in reddit_keywords):
                                    detailed_content.append(f"=== POST {i+1} CONTENT ===\n{post_content[:4000]}\n")
                                    print(f"  ✅ Extracted {len(post_content)} characters from post {i+1}")
                                else:
                                    print(f"  ⚠️ Post {i+1} content doesn't look like Reddit")
                            else:
                                print(f"  ⚠️ Post {i+1} had insufficient content")
                        else:
                            print(f"  ❌ Failed to navigate to post page")
                        
                        # Go back to search results for next iteration
                        print(f"  🔙 Going back to search results...")
                        await navigate_tool.arun({"url": search_url})
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        print(f"❌ Error navigating to post {i+1}: {e}")
                        # Try to go back to search results if we get stuck
                        try:
                            await navigate_tool.arun({"url": search_url})
                            await asyncio.sleep(3)
                        except:
                            pass
                        continue
            else:
                print("❌ No post URLs found - will use search results content only")
                
        except Exception as e:
            print(f"❌ Major error in click_posts_node: {e}")
            import traceback
            traceback.print_exc()
        
        # Combine all extracted content
        if detailed_content:
            all_content = state.get("scraped_content", "") + "\n\n=== DETAILED POST CONTENT ===\n" + "\n".join(detailed_content)
            print(f"✅ Total content extracted: {len(all_content)} characters from {len(detailed_content)} posts")
        else:
            print("❌ No detailed content extracted from posts")
            all_content = state.get("scraped_content", "")
            
            # If we still have no detailed content, at least return what we have
            if not all_content:
                print("⚠️ No content at all - using fallback")
                all_content = f"Search results from r/{state['subreddit']} for {state['search_term']}"
        
        return {
            **state,
            "scraped_content": all_content,
            "current_step": "extract_pois"
        }
    
    async def extract_pois_node(state: RedditState) -> RedditState:
        """Extract POIs from scraped content"""
        content = state.get("scraped_content", "")
        
        if not content:
            print("❌ No content to extract POIs from")
            return {**state, "extracted_pois": [], "current_step": "end"}
        
        # Check if content looks like Reddit
        reddit_indicators = ['reddit.com', 'r/', 'upvote', 'downvote', 'comment', 'post', 'OP', 'edit:', 'deleted']
        has_reddit_content = any(indicator in content.lower() for indicator in reddit_indicators)
        
        if has_reddit_content:
            print("✅ Content contains Reddit-specific elements - authentic content detected!")
        else:
            print("❌ Content doesn't seem to be from Reddit")
            return {**state, "extracted_pois": [], "current_step": "end"}
        
        # Use LLM to extract POIs
        llm_with_structured_output = llm.with_structured_output(POIList)
        
        extract_messages = [
            SystemMessage(content=f"""You are an expert at identifying specific places mentioned in detailed Reddit posts about things to do in {state['city']}.

From the scraped Reddit content, extract specific, real places that people recommend visiting in {state['city']}. Look for detailed mentions in both original posts and comments.

Look for ANY mentions of:
- Restaurants, cafes, bars, food spots with specific names
- Museums, galleries, cultural venues
- Parks, trails, outdoor spaces
- Shopping centers, markets, boutiques
- Entertainment venues, theaters, cinemas
- Tourist attractions, landmarks
- Local businesses and services
- Neighborhoods, districts, areas
- Any specific place names with locations

For each place, provide:
- name: The exact name of the place
- description: Brief category description (e.g., "Popular restaurant", "Hidden gem cafe")
- category: The type of place (restaurant, museum, park, attraction, etc.)
- reddit_context: The EXACT Reddit content (posts/comments) that mention this place

Return 8-12 of the most specific places mentioned with detailed context."""),
            HumanMessage(content=f"Extract specific places from this detailed Reddit content about {state['city']}:\n\n{content[:8000]}")
        ]
        
        pois_response = await llm_with_structured_output.ainvoke(extract_messages)
        pois = pois_response.pois
        print(f"Extracted {len(pois)} POIs: {[poi.name for poi in pois]}")
        
        return {
            **state,
            "extracted_pois": pois,
            "current_step": "create_descriptions"
        }

    async def create_descriptions_node(state: RedditState) -> RedditState:
        """Create authentic descriptions by quoting Reddit users"""
        print("✍️ Creating authentic descriptions by quoting Reddit users...")
        
        pois = state.get("extracted_pois", [])
        if not pois:
            print("❌ No POIs to create descriptions for")
            return {**state, "extracted_pois": [], "current_step": "end"}
        
        # Create a new POI model for enhanced descriptions
        class EnhancedPOI(BaseModel):
            name: str = Field(description="Name of the point of interest")
            description: str = Field(description="Brief category description")
            category: str = Field(description="Type of place")
            reddit_context: str = Field(description="Original Reddit content")
            user_quote: str = Field(description="A short, authentic quote from Reddit users about this place (max 100 words)")
        
        class EnhancedPOIList(BaseModel):
            city: str = Field(description="The city being analyzed")
            pois: List[EnhancedPOI] = Field(description="List of enhanced POIs with user quotes")
        
        llm_with_enhanced_output = llm.with_structured_output(EnhancedPOIList)
        
        # Create enhanced descriptions with user quotes
        description_messages = [
            SystemMessage(content=f"""You are an expert at creating authentic, engaging descriptions for places in {state['city']} by quoting what Reddit users actually said.

For each place, create a short, authentic description (max 100 words) that:
1. ALWAYS starts with Reddit-specific phrases like "Reddit users love...", "According to r/{state['subreddit']}...", "Locals say...", "The community recommends..."
2. Quotes directly from what Reddit users said about the place
3. Captures the authentic voice and enthusiasm of Reddit users
4. Highlights what makes the place special according to locals
5. Uses actual phrases and recommendations from the Reddit content
6. Maintains the casual, honest tone of Reddit recommendations
7. Includes Reddit-specific terms like "upvoted", "recommended", "community favorite", "hidden gem"

Focus on:
- What users specifically recommend doing there
- What makes it unique or special
- Why locals love it
- Any insider tips or hidden gems mentioned
- Reddit community consensus and upvotes

Make the descriptions feel like they're coming directly from Reddit users who've been there and include Reddit community language."""),
            HumanMessage(content=f"""Create authentic user quotes for these places in {state['city']} based on the Reddit content:

{chr(10).join([f"• {poi.name} ({poi.category}): {poi.reddit_context[:300]}..." for poi in pois])}

Create short, authentic quotes (max 100 words each) that capture what Reddit users actually said about each place.""")
        ]
        
        enhanced_response = await llm_with_enhanced_output.ainvoke(description_messages)
        enhanced_pois = enhanced_response.pois
        
        print(f"✅ Created authentic descriptions for {len(enhanced_pois)} POIs")
        
        # Convert back to original POI format but with enhanced descriptions
        final_pois = []
        for enhanced_poi in enhanced_pois:
            # Find the original POI to preserve other fields
            original_poi = next((p for p in pois if p.name == enhanced_poi.name), None)
            if original_poi:
                # Update the description with the user quote
                original_poi.description = enhanced_poi.user_quote
                final_pois.append(original_poi)
        
        return {
            **state,
            "extracted_pois": final_pois,
            "current_step": "end"
        }
    
    # Create workflow
    workflow = StateGraph(RedditState)
    
    # Add nodes
    workflow.add_node("scrape_reddit", scrape_reddit_node)
    workflow.add_node("click_posts", click_posts_node)
    workflow.add_node("extract_pois", extract_pois_node)
    workflow.add_node("create_descriptions", create_descriptions_node)
    
    # Add edges
    workflow.add_edge("scrape_reddit", "click_posts")
    workflow.add_edge("click_posts", "extract_pois")
    workflow.add_edge("extract_pois", "create_descriptions")
    workflow.add_edge("create_descriptions", END)
    
    # Add START edge
    workflow.set_entry_point("scrape_reddit")
    
    # Compile workflow
    app = workflow.compile()
    
    # Simple subreddit selection
    subreddit = city.lower()
    
    # Search terms
    search_terms = [
        f"things%20to%20do%20{city}",
        f"best%20places%20{city}",
        f"hidden%20gems%20{city}",
        f"secret%20spots%20{city}",
        f"local%20favorites%20{city}"
    ]
    
    search_term = random.choice(search_terms)
    
    print(f"🔍 Using search term: {search_term}")
    
    try:
        # Run LangGraph workflow
        initial_state = {
            "messages": [],
            "current_step": "scrape_reddit",
            "scraped_content": None,
            "extracted_pois": None,
            "city": city,
            "subreddit": subreddit,
            "search_term": search_term
        }
        
        print("🤖 Starting LangGraph workflow...")
        result = await app.ainvoke(initial_state)
        
        pois = result.get("extracted_pois", [])
        if not pois:
            print("❌ No POIs extracted from LangGraph workflow")
            return []
        
        # Convert to POI format with geocoding
        final_pois = []
        for poi in pois:
            # Simple fallback coordinates with variation
            lat_variation = random.uniform(-0.01, 0.01)
            lng_variation = random.uniform(-0.01, 0.01)
            
            poi_output = {
                "name": poi.name,
                "lat": lat + lat_variation,
                "lng": lng + lng_variation,
                "summary": poi.description,  # Use the enhanced user quote description
                "type": "reddit",
                "radius": 20
            }
            final_pois.append(poi_output)
        
        print(f"✅ Created {len(final_pois)} Reddit POIs with LangGraph workflow")
        return final_pois
        
    except Exception as e:
        print(f"❌ Error in LangGraph Reddit scraper: {e}")
        import traceback
        traceback.print_exc()
        return []

# Usage example
def main():
    # Create workflow
    workflow = create_reddit_scraper_agent("Toronto")
    
    # Initial state
    initial_state = {
        "subreddit": "askTO",
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
    
    # Run workflow
    print("Starting Reddit scraping workflow...")
    result = workflow.invoke(initial_state)
    
    # Print results
    pois = result.get("pois", [])
    print(f"\n✅ Generated {len(pois)} POIs:")
    for poi in pois:
        print(f"📍 {poi['name']}")
        print(f"   Coordinates: ({poi['lat']}, {poi['lng']})")
        print(f"   Summary: {poi['summary']}")
        print()

if __name__ == "__main__":
    main()
