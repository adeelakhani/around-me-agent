"""
Clean Reddit scraper agent - only contains agentic work
"""
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

def create_reddit_scraper_agent(subreddit=None, city=None):
    """Create a LangGraph Reddit scraper agent"""
    # Dynamically determine subreddit based on city if not provided
    if not subreddit and city:
        subreddit = city.lower()
    elif not subreddit:
        subreddit = "toronto"  # Default fallback
    if not city:
        city = "Toronto"  # Default fallback
    
    print(f"Creating LangGraph Reddit scraper for r/{subreddit} in {city}...")
    
    # Initialize tools and LLM
    async_browser = create_async_playwright_browser(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    print(f"Got {len(tools)} Playwright tools: {[tool.name for tool in tools]}")
    
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools(tools)
    llm_with_structured_output = llm.with_structured_output(POIList)
    llm_with_poi_output = llm.with_structured_output(POIOutput)
    
    def scrape_reddit_node(state: State) -> Dict[str, Any]:
        """Node to scrape Reddit content using browser tools"""
        try:
            subreddit = state.get("subreddit", "askTO")
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
            
            user_message = f"""Navigate to https://www.reddit.com/r/{subreddit}/search/?q={search_term}&restrict_sr=on&sort=relevance&t=all

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
        
        system_message = f"""You are analyzing Reddit content to find COOL PLACES in {state['city']}.

GOAL: Find all the interesting, fun, and cool places that Reddit users recommend visiting in {state['city']}.

CRITICAL RULES:
1. Extract EVERY place name mentioned in the Reddit content that people recommend or talk about positively
2. Focus on places that Reddit users say are cool, fun, interesting, or worth visiting
3. Look for places that people recommend to others
4. Include both specific business names AND general area names that people mention positively
5. Look for places in post titles, comments, and any other text

EXTRACT ALL COOL PLACES mentioned in the content, including:
- Any business names that people recommend
- Any venue names that people say are fun
- Any location names that people mention positively
- Any area names that people recommend visiting
- Any building names that people say are interesting
- Any street names that seem like important destinations
- Any landmark names that people recommend
- Any other place names that people talk about positively

DO NOT extract:
- Generic terms like "the mall" or "a park" (unless they're part of a specific name)
- Vague references like "that place" or "the spot"
- Places that people mention negatively

For each place found, provide:
- name: The exact name as mentioned in Reddit
- description: Brief category (e.g., "Restaurant", "Park", "Museum", "Neighborhood")
- category: Type of place
- reddit_context: The exact Reddit text that mentions this place

Be extremely thorough - extract as many cool places as you can find mentioned in the content."""
        
        user_message = f"""Find ALL COOL PLACES in {city} that Reddit users recommend visiting:\n\n{scraped_content[:12000]}"""
        
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
            
            for poi in pois:
                print(f"Getting coordinates for: {poi.name}")
                
                try:
                    # Try OpenStreetMap first (it's working well and free)
                    print(f"🗺️ Trying OpenStreetMap geocoding for {poi.name}...")
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
                        summary_messages = [
                            SystemMessage(content=system_message),
                            HumanMessage(content=user_message)
                        ]
                        
                        summary_response = llm.invoke(summary_messages)
                        summary = summary_response.content.strip()[:400]  # Increased length limit
                        
                        # Validate that the summary is factual and doesn't contain fake quotes
                        import re
                        if '"' in summary and not any(quote in poi.reddit_context for quote in re.findall(r'"([^"]+)"', summary)):
                            # Remove fake quotes and make it factual
                            summary = re.sub(r'"[^"]*"', '', summary).strip()
                            summary = f"Mentioned in r/{subreddit} discussions. {poi.reddit_context[:150]}..."
                            summary = summary[:200]
                        
                        # If summary is too generic, make it more factual
                        generic_phrases = ['great', 'good', 'nice', 'popular', 'famous', 'well-known']
                        if any(phrase in summary.lower() for phrase in generic_phrases) and len(poi.reddit_context) > 50:
                            # Extract actual words from the content
                            content_words = poi.reddit_context.lower().split()
                            factual_words = [word for word in content_words if word in ['hidden', 'gem', 'underrated', 'best', 'favorite', 'love', 'amazing', 'incredible']]
                            if factual_words:
                                factual_word = factual_words[0]
                                summary = f"Reddit users mention this {poi.category.lower()} as {factual_word}. {poi.reddit_context[:100]}..."
                            else:
                                summary = f"Featured in r/{subreddit} discussions. {poi.reddit_context[:100]}..."
                            summary = summary[:200]
                        
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

# Usage example
def main():
    """Example usage with any city"""
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
