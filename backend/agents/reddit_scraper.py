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

nest_asyncio.apply()

# Define structured output for POI data
class POI(BaseModel):
    name: str = Field(description="Name of the point of interest")
    description: str = Field(description="Brief description of what makes this place special")
    category: str = Field(description="Category like 'museum', 'park', 'restaurant', 'attraction'")

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

def create_reddit_scraper_agent(subreddit="askTO"):
    print(f"Creating LangGraph Reddit scraper for r/{subreddit}...")
    
    # Initialize tools and LLM
    async_browser = create_async_playwright_browser(headless=True)
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

You MUST use the browser tools. Do not respond without using the tools first."""
            
            # Use different search terms to get variety
            search_terms = [
                f"things%20to%20do%20{city}",
                f"best%20places%20{city}",
                f"cool%20spots%20{city}",
                f"hidden%20gems%20{city}",
                f"must%20visit%20{city}",
                f"attractions%20{city}",
                f"restaurants%20{city}",
                f"activities%20{city}"
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

Use the extract_text tool to get everything you can see. If the page is empty or doesn't load, extract whatever text is available."""
            
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
        
        system_message = f"""You are an expert at identifying specific places mentioned in Reddit posts about things to do in {city}.

From the scraped Reddit content, extract specific, real places that people recommend visiting in {city}. 

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
- description: A brief description of what makes it special (based on Reddit mentions)
- category: The type of place (restaurant, museum, park, attraction, etc.)

Return 5-8 of the most specific places mentioned."""
        
        user_message = f"""Extract specific places from this Reddit content about {city}:\n\n{scraped_content[:3000]}"""
        
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
                    # Search using Serper.dev
                    search_query = f"{poi.name} {location_name} {country} coordinates latitude longitude"
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
                        SystemMessage(content="Extract the latitude and longitude coordinates from this search result text. Look for coordinate patterns like 43.1234, -79.1234 or similar formats. If no coordinates found, return 0.0 for both lat and lng."),
                        HumanMessage(content=search_text)
                    ])
                    
                    if coord_response.lat != 0.0 and coord_response.lng != 0.0:
                        coords = {
                            'lat': coord_response.lat,
                            'lng': coord_response.lng,
                            'address': f"{poi.name}, {city}"
                        }
                        print(f"✅ Found coordinates for {poi.name}: ({coords['lat']}, {coords['lng']})")
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
                    # Create engaging summary based on Reddit context with variety
                    summary_styles = [
                        f"""Create a cool, engaging summary about {poi.name} based on Reddit buzz.

Make it sound like insider knowledge from r/{subreddit}. Use phrases like:
- "Redditors are buzzing about..."
- "The r/{subreddit} community loves..."
- "Local Reddit users recommend..."
- "According to the {city} Reddit scene..."

Keep it under 150 characters and make it exciting! Focus on why this place is worth visiting.""",
                        
                        f"""You are a local {city} expert creating concise summaries of popular places.

Write in a casual, insider tone like you're sharing local secrets. Use phrases like:
- "This spot is a local favorite for..."
- "You'll find locals raving about..."
- "The {city} crowd swears by..."
- "Hidden gem alert: this place..."

Keep it under 150 characters and focus on what makes it unique.""",
                        
                        f"""You are creating short, punchy summaries for {city} hotspots.

Write like a friend giving you the inside scoop. Use phrases like:
- "This is where {city} locals go for..."
- "Skip the tourist traps, hit this spot for..."
- "The real {city} experience is at..."
- "Trust me, this place is worth the hype for..."

Keep it under 150 characters and be specific about what makes it special."""
                    ]
                    
                    import random
                    system_message = random.choice(summary_styles)
                    
                    user_message = f"""Location: {poi.name}
Category: {poi.category}
Description: {poi.description}
City: {city}
Subreddit: r/{subreddit}

Create an engaging 1-sentence summary about what makes this place special according to Reddit users."""
                    
                    try:
                        summary_messages = [
                            SystemMessage(content=system_message),
                            HumanMessage(content=user_message)
                        ]
                        
                        summary_response = llm.invoke(summary_messages)
                        summary = summary_response.content.strip()[:200]  # Limit length
                        
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
                        print(f"Created POI: {poi.name} at ({coords['lat']}, {coords['lng']})")
                        
                    except Exception as e:
                        print(f"Error creating POI summary for {poi.name}: {e}")
                        # Fallback summary
                        poi_output = POIOutput(
                            name=poi.name,
                            lat=coords['lat'],
                            lng=coords['lng'],
                            summary=f"Popular {poi.category} mentioned by r/{subreddit} community",
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
    # Create workflow
    workflow = create_reddit_scraper_agent("askTO")
    
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
