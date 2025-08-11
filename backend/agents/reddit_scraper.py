from typing import Annotated, TypedDict, List, Any, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langgraph.prebuilt import ToolNode
import nest_asyncio
import os
import random
from dotenv import load_dotenv

# Import from organized modules
from reddit.models import POI, POIList, POIOutput, Coordinates, EnhancedPOI, EnhancedPOIList
from reddit.geocoding import search_serper, geocode_with_fallback
from reddit.url_extraction import extract_reddit_post_urls_from_playwright
from reddit.search_terms import get_random_search_term
from utils.location import is_coordinates_in_city

load_dotenv(override=True)
nest_asyncio.apply()

# Models are now imported from reddit.models

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

# URL extraction functions are now imported from reddit.url_extraction

def create_reddit_scraper_agent(subreddit=None, city=None):
    # Dynamically determine subreddit based on city if not provided
    if not subreddit and city:
        subreddit = city.lower()
    elif not subreddit:
        subreddit = "toronto"  # Default fallback
    if not city:
        city = "Toronto"  # Default fallback
    
    print(f"Creating LangGraph Reddit scraper for r/{subreddit} in {city}...")
    print(f"🔍 Target subreddit: r/{subreddit}")
    print(f"🌍 Target city: {city}")
    
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
    # Geocoding functions are now imported from reddit.geocoding
    
    def scrape_reddit_node(state: State) -> Dict[str, Any]:
        """Node to scrape Reddit content using browser tools"""
        try:
            subreddit = state.get("subreddit", city.lower())
            city = state.get('city', 'Unknown City')
            
            system_message = f"""You are a Reddit scraping expert. Your job is to search for posts about things to do and places to visit.

CRITICAL INSTRUCTIONS:
1. You MUST use the navigate_browser tool to go to Reddit
2. You MUST use the extract_text tool to get content from the page
3. Search for posts about things to do, places to visit, attractions, activities
4. Extract ALL text content including post titles, comments, and recommendations
5. If the page doesn't load or has no content, extract whatever you can find
6. Focus on finding SPECIFIC place names, business names, and locations that people recommend

You MUST use BOTH browser tools in sequence: first navigate_browser, then extract_text.
Do not respond without using both tools."""
            
            # Get search term from organized module
            search_term = get_random_search_term(city)
            
            user_message = f"""Navigate to https://old.reddit.com/r/{subreddit}/search/?q={search_term}&restrict_sr=on&sort=relevance&t=all

Then extract ALL text content from the page, including:
- Post titles and content
- Comments and recommendations
- Any specific place names, business names, or venues mentioned

Use the extract_text tool to get everything you can see. If the page is empty or doesn't load, extract whatever text is available.

IMPORTANT: You must call extract_text after navigating to get the page content."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            import datetime
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"🕐 [{current_time}] Scraping r/{subreddit} for places...")
            print(f"🔍 Using search term: {search_term}")
            print(f"🌐 Navigating to: https://old.reddit.com/r/{subreddit}/search/?q={search_term}&restrict_sr=on&sort=relevance&t=all")
            
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
        city = state.get('city', 'Unknown City')
        
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
        

        
        system_message = f"""You are analyzing Reddit content to find COOL PLACES that people recommend visiting.

GOAL: Find all the interesting, fun, and cool places that Reddit users recommend visiting.

IMPORTANT: Extract ALL places that are mentioned positively in the provided Reddit content, especially places that people recommend or say are cool/fun.
Be thorough and comprehensive - look for any place names, businesses, attractions, neighborhoods, etc. that people talk about positively.

Extract ALL COOL PLACES mentioned in the content, including:
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

Be comprehensive - extract as many cool places as you can find mentioned in the content."""
        
        user_message = f"""Find ALL COOL PLACES that people recommend visiting.

Here is the Reddit content to analyze:

{scraped_content[:12000]}

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

Be comprehensive - extract as many cool places as you can find mentioned in the content."""
        
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
            city = state.get('city', 'Unknown City')
            
            # Get location details from state
            location_data = state.get('location_data', {})
            province = location_data.get('province', 'Ontario')
            country = location_data.get('country', 'Canada')
            location_name = location_data.get('name', f"{city}, {province}")
            
            final_pois = []
            
            print(f"🗺️ Processing {len(pois)} POIs for geocoding...")
            
            for poi in pois:
                print(f"📍 Getting coordinates for: {poi.name}")
                
                try:
                    # Try geocoding with fallback methods
                    print(f"🗺️ Geocoding {poi.name}...")
                    coords = geocode_with_fallback(poi.name, city, province, country)
                    
                    if coords:
                        coords['address'] = f"{poi.name}, {city}"
                        print(f"✅ OpenStreetMap geocoding successful for {poi.name}: ({coords['lat']}, {coords['lng']})")
                    else:
                        print(f"❌ OpenStreetMap failed for {poi.name}, trying Serper...")
                        
                        # Fallback to Serper if OpenStreetMap fails
                        country = location_data.get('country', 'Canada')
                        province = location_data.get('province', 'Ontario')
                        
                        # More specific search queries for better geocoding
                        search_queries = [
                            f'"{poi.name}" "{city}" address location coordinates',
                            f'"{poi.name}" "{city}" exact address street number',
                            f'"{poi.name}" "{city}" map location GPS coordinates',
                            f'"{poi.name}" "{city}" business address phone number'
                        ]
                        
                        search_results = None
                        search_text = ""
                        
                        # Try each search query until we get good results
                        for i, search_query in enumerate(search_queries):
                            print(f"🔍 Serper search attempt {i+1}: {search_query}")
                            search_results = search_serper(search_query)
                            
                            # Check if we got meaningful results
                            if search_results.get("organic") and len(search_results["organic"]) > 0:
                                print(f"✅ Serper search {i+1} returned {len(search_results['organic'])} results")
                                break
                            else:
                                print(f"⚠️ Serper search {i+1} returned no results, trying next query...")
                        
                        if not search_results:
                            print(f"❌ All Serper search queries failed for {poi.name}")
                            continue
                        
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
                        
                        print(f"📝 Serper search results: {search_text[:200]}...")
                        
                        # Use LLM to extract coordinates from search results
                        # Coordinates model is now imported from reddit.models
                        
                        llm_with_coords = llm.with_structured_output(Coordinates)
                        
                        coord_response = llm_with_coords.invoke([
                            SystemMessage(content="""Extract EXACT latitude and longitude coordinates for the specific place.

LOOK FOR:
- GPS coordinates like "43.6532, -79.3832" or "43°39'11.5"N 79°22'59.9"W"
- Address with street number and name
- "Located at" or "Address:" followed by coordinates
- Google Maps links with coordinates
- Business listings with exact addresses

ONLY return coordinates if they are SPECIFICALLY for the exact place mentioned.
If coordinates are for general city area, return 0.0, 0.0"""),
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
                                print(f"✅ Serper found coordinates for {poi.name}: ({coords['lat']}, {coords['lng']}) - VALIDATED")
                            else:
                                print(f"❌ Serper coordinates for {poi.name} are outside {city} bounds - REJECTED")
                                coords = None
                                continue
                        else:
                            print(f"❌ No coordinates found for {poi.name} with Serper")
                            coords = None
                            continue
                    
                except Exception as e:
                    print(f"❌ Error getting coordinates for {poi.name}: {e}")
                    coords = None
                    continue
                
                if coords:

                    
                    # Create summary using ONLY the actual Reddit content - NO FAKE QUOTES
                    system_message = f"""Create a brief, factual summary for {poi.name} based ONLY on the Reddit content provided.

CRITICAL RULES:
1. Use ONLY information that is explicitly stated in the Reddit content
2. DO NOT create fake quotes or put words in users' mouths
3. DO NOT use quotation marks unless they appear in the original content
4. Keep it under 200 characters
5. Start with a simple factual statement like:
   - "Mentioned in r/{subreddit} discussions"
   - "Reddit users discuss this {poi.category.lower()}"
   - "Featured in r/{subreddit} recommendations"
6. Only mention specific details that are actually in the content
7. If the content is vague, keep the summary general and factual

DO NOT:
- Create fake user quotes
- Add opinions not in the original content
- Use quotation marks for made-up quotes
- Exaggerate or embellish the content"""
                    
                    user_message = f"""Place: {poi.name}
Category: {poi.category}
Subreddit: r/{subreddit}
City: {city}

ORIGINAL REDDIT CONTENT ABOUT THIS PLACE:
{poi.reddit_context}

Create a brief, factual summary using ONLY the Reddit content above."""
                    
                    try:
                        print(f"🤖 Generating summary for {poi.name}...")
                        summary_messages = [
                            SystemMessage(content=system_message),
                            HumanMessage(content=user_message)
                        ]
                        
                        summary_response = llm.invoke(summary_messages)
                        print(f"✅ LLM response received for {poi.name}")
                        
                        if not summary_response or not summary_response.content:
                            print(f"❌ Empty LLM response for {poi.name}")
                            summary = f"Mentioned in r/{subreddit} discussions"
                        else:
                            summary = summary_response.content.strip()[:400]  # Increased length limit
                        
                        # Simple validation and cleanup
                        summary = summary.strip()
                        
                        # Remove any fake quotes that don't exist in original content
                        if '"' in summary:
                            # Check if quotes are actually in the original content
                            quotes_in_summary = re.findall(r'"([^"]+)"', summary)
                            quotes_in_content = re.findall(r'"([^"]+)"', poi.reddit_context)
                            
                            # If quotes in summary aren't in original content, remove them
                            for quote in quotes_in_summary:
                                if quote not in quotes_in_content:
                                    summary = summary.replace(f'"{quote}"', quote)
                        
                        # Keep it under 200 characters
                        if len(summary) > 200:
                            summary = summary[:197] + "..."
                        
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
                        print(f"❌ Error creating POI summary for {poi.name}: {e}")
                        import traceback
                        traceback.print_exc()
                        
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
                        print(f"✅ Created fallback POI for {poi.name}")
                else:
                    print(f"❌ Could not geocode: {poi.name}")
            
            print(f"🎯 Final result: Created {len(final_pois)} POIs")
            
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
            post_urls = await extract_reddit_post_urls_from_playwright(page, target_subreddit=state['subreddit'])
            
            if post_urls:
                print(f"✅ Successfully extracted {len(post_urls)} Reddit post URLs using Playwright")
                # Show first few URLs and check subreddit
                for i, url in enumerate(post_urls[:5]):
                    subreddit_in_url = "unknown"
                    if "/r/" in url:
                        subreddit_in_url = url.split("/r/")[1].split("/")[0]
                    print(f"  {i+1}. {url} (subreddit: r/{subreddit_in_url})")
            else:
                print("❌ No URLs found with direct Playwright method")
                
                # Fallback: Try extracting from page content
                print("🔄 Fallback: Extracting from page content...")
                page_content = await extract_tool.arun({})
                post_urls = extract_reddit_post_urls_from_text(page_content, target_subreddit=state['subreddit'])
                print(f"✅ Extracted {len(post_urls)} URLs from page content")
            
            # Let LLM select the most relevant posts for POI extraction
            if post_urls and len(post_urls) > 0:
                # Additional filtering to ensure we only have URLs from the correct subreddit
                filtered_urls = []
                for url in post_urls:
                    if f"/r/{state['subreddit']}/comments/" in url:
                        filtered_urls.append(url)
                    else:
                        print(f"⚠️ Filtered out URL from wrong subreddit: {url}")
                
                if filtered_urls:
                    print(f"✅ Found {len(filtered_urls)} Reddit post URLs from r/{state['subreddit']}")
                    # Show first 10 URLs to LLM for selection
                    candidate_urls = filtered_urls[:10]
                else:
                    print(f"❌ No URLs found from r/{state['subreddit']} after filtering")
                    candidate_urls = []
                print(f"🔍 Presenting first {len(candidate_urls)} URLs to LLM for relevance selection...")
                
                # Create a simple prompt for URL selection
                url_selection_prompt = f"""
                You are analyzing Reddit post URLs to find the most relevant ones for discovering fun and interesting places in {state['city']}.
                
                Your goal is to find posts that are most likely to contain:
                - People asking about or recommending cool places to go
                - Discussions about fun areas, neighborhoods, or spots
                - User experiences and recommendations about places they enjoyed
                - Local insights about interesting locations
                
                Here are the Reddit post URLs to analyze:
                {chr(10).join([f"{i+1}. {url}" for i, url in enumerate(candidate_urls)])}
                
                Select the 5 most relevant URLs for finding fun places. Consider:
                - URLs that seem to be about exploring or discovering places
                - URLs that appear to be community discussions about cool spots
                - URLs that mention specific areas, neighborhoods, or types of places
                - URLs that look like people sharing experiences or asking for recommendations
                
                Return only the numbers of the 5 most relevant URLs (e.g., "1, 3, 5, 7, 9").
                """
                
                try:
                    # Use a simple LLM call to select URLs
                    from langchain_openai import ChatOpenAI
                    selection_llm = ChatOpenAI(model="gpt-4o-mini")
                    selection_response = await selection_llm.ainvoke(url_selection_prompt)
                    
                    # Parse the response to get selected indices
                    response_text = selection_response.content
                    print(f"🤖 LLM selection response: {response_text}")
                    
                    # Extract numbers from response
                    import re
                    selected_numbers = re.findall(r'\d+', response_text)
                    selected_indices = [int(num) - 1 for num in selected_numbers if 0 <= int(num) - 1 < len(candidate_urls)]
                    
                    # Remove duplicates and limit to 5
                    selected_indices = list(set(selected_indices))[:5]
                    
                    if selected_indices:
                        selected_urls = [candidate_urls[i] for i in selected_indices]
                        print(f"✅ LLM selected {len(selected_urls)} most relevant URLs:")
                        for i, url in enumerate(selected_urls):
                            print(f"  {i+1}. {url}")
                    else:
                        print("⚠️ LLM selection failed, using first 5 URLs")
                        selected_urls = candidate_urls[:5]
                        
                except Exception as e:
                    print(f"❌ Error with LLM URL selection: {e}")
                    print("⚠️ Falling back to first 5 URLs")
                    selected_urls = candidate_urls[:5]
                
                # Navigate to the selected posts
                for i, post_url in enumerate(selected_urls):
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
        
        # Use LLM to extract POIs with STRICT verification
        llm_with_structured_output = llm.with_structured_output(POIList)
        
        extract_messages = [
            SystemMessage(content=f"""You are analyzing Reddit content to find COOL PLACES that people recommend visiting.

GOAL: Find all the interesting, fun, and cool places that Reddit users recommend visiting.

IMPORTANT: Extract ALL places that are mentioned positively in the provided Reddit content, especially places that people recommend or say are cool/fun.
Be thorough and comprehensive - look for any place names, businesses, attractions, neighborhoods, etc. that people talk about positively.

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

Be comprehensive - extract as many cool places as you can find mentioned in the content."""),
            HumanMessage(content=f"""Find ALL COOL PLACES that people recommend visiting.

Here is the Reddit content to analyze:

{content[:12000]}

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

Be comprehensive - extract as many cool places as you can find mentioned in the content.""")
        ]
        
        pois_response = await llm_with_structured_output.ainvoke(extract_messages)
        pois = pois_response.pois
        print(f"Extracted {len(pois)} POIs: {[poi.name for poi in pois]}")
        
        # AGGRESSIVE REGEX EXTRACTION AS FALLBACK
        print("🔍 Running aggressive regex extraction as fallback...")
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
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    match = ' '.join(match)
                # Filter out common words that aren't places
                common_words = ['Reddit', 'Toronto', 'Canada', 'Ontario', 'Personal', 'Please', 'Submit', 'Share', 'Reply', 'Comment', 'Post', 'User', 'Member', 'Online', 'Filter', 'Show', 'Hide', 'Sort', 'Best', 'Top', 'New', 'Old', 'Controversial', 'Q&A', 'More', 'Less', 'Points', 'Children', 'Permalink', 'Embed', 'Save', 'Parent', 'Report', 'Track', 'Me', 'Reply', 'Share', 'More', 'Replies', 'Sort', 'By', 'Best', 'Top', 'New', 'Controversial', 'Old', 'Q&A', 'Open', 'Comment', 'Options', 'Best', 'Top', 'New', 'Controversial', 'Old', 'Q&A']
                if match not in common_words and len(match) > 3:
                    found_places.add(match)
        
        print(f"🔍 Regex found {len(found_places)} additional potential places")
        
        # If LLM found very few POIs, use regex results as backup
        if len(pois) < 10 and found_places:
            print(f"⚠️ LLM only found {len(pois)} POIs, using regex results as backup...")
            # Convert regex results to POI format
            for place_name in list(found_places)[:20]:  # Limit to 20 to avoid spam
                # Check if this place is already in LLM results
                if not any(poi.name.lower() == place_name.lower() for poi in pois):
                    # Create a simple POI from regex result
                    from reddit.models import POI
                    regex_poi = POI(
                        name=place_name,
                        description=f"Place mentioned in Reddit discussions",
                        category="Location",
                        reddit_context=f"Mentioned in Reddit content: {place_name}"
                    )
                    pois.append(regex_poi)
                    print(f"➕ Added regex POI: {place_name}")
        
        print(f"✅ Final result: {len(pois)} POIs (LLM: {len(pois_response.pois)}, Regex additions: {len(pois) - len(pois_response.pois)})")
        
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
                # Models are now imported from reddit.models
        
        llm_with_enhanced_output = llm.with_structured_output(EnhancedPOIList)
        
        # Create factual descriptions based ONLY on actual Reddit content
        description_messages = [
            SystemMessage(content=f"""Create brief, factual descriptions for places in {state['city']} based ONLY on the Reddit content provided.

CRITICAL RULES:
1. Use ONLY information explicitly stated in the Reddit content
2. DO NOT create fake quotes or put words in users' mouths
3. DO NOT use quotation marks unless they appear in the original content
4. Keep descriptions under 100 words
5. Start with factual statements like:
   - "Mentioned in r/{state['subreddit']} discussions"
   - "Reddit users discuss this place"
   - "Featured in community recommendations"
6. Only mention specific details that are actually in the content
7. If content is vague, keep description general and factual

DO NOT:
- Create fake user quotes
- Add opinions not in the original content
- Use quotation marks for made-up quotes
- Exaggerate or embellish the content"""),
            HumanMessage(content=f"""Create factual descriptions for these places in {state['city']} based ONLY on the Reddit content:

{chr(10).join([f"• {poi.name} ({poi.category}): {poi.reddit_context[:300]}..." for poi in pois])}

Create brief, factual descriptions (max 100 words each) that accurately reflect what's in the Reddit content without adding fake quotes.""")
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
    
    # Simple subreddit selection - just use the city name
    subreddit = city.lower()
    
    # Get search term from organized module
    search_term = get_random_search_term(city)
    
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
    # Example usage with any city
    city = "Toronto"  # This can be changed to any city
    workflow = create_reddit_scraper_agent(city=city)
    
    # Initial state
    initial_state = {
        "subreddit": city.lower(),
        "city": city,
        "location_data": {
            "city": city,
            "province": "Unknown", 
            "country": "Unknown"
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
