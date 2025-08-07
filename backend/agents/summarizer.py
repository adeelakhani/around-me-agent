from typing import Annotated, TypedDict, List, Any, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
import os
import nest_asyncio

nest_asyncio.apply()

# Define structured output for POI data
class POIOutput(BaseModel):
    name: str = Field(description="Name of the point of interest")
    lat: float = Field(description="Latitude coordinate")
    lng: float = Field(description="Longitude coordinate")
    summary: str = Field(description="Summary of what's happening at this location")
    type: str = Field(description="Type of POI (reddit, event, restaurant, etc.)")
    radius: int = Field(description="Radius in kilometers")

# Define the State like in your notebook
class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    location_data: Dict
    reddit_data: List[Dict]
    weather_data: Dict
    events_data: List[Dict]
    news_data: List[Dict]
    summary: Optional[str]
    current_step: Optional[str]
    pois: Optional[List[Dict]]

def create_summarizer_agent(subreddit="toronto"):
    print(f"Creating LangGraph agent with Playwright tools for r/{subreddit}...")
    
    # Get Playwright tools like in the notebook
    async_browser = create_async_playwright_browser(headless=True)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    print(f"Got {len(tools)} Playwright tools: {[tool.name for tool in tools]}")
    
    # Initialize LLM with tools and structured output
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools(tools)
    llm_with_structured_output = llm.with_structured_output(POIOutput)
    
    def worker(state: State) -> Dict[str, Any]:
        current_step = state.get("current_step", "start")
        print(f"Worker node: Current step = {current_step}")
        
        if current_step == "start":
            # Step 1: Navigate to Reddit
            system_message = """You are a web scraping expert. Your first task is to navigate to Reddit.

IMPORTANT: After navigating, you MUST move to the next step. Do not navigate multiple times.
"""
            user_message = f"""Navigate to https://www.reddit.com/r/{subreddit}/ and then move to the next step.

After navigating, you will extract text from the page."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            print("Worker node: Step 1 - Navigating to Reddit...")
            response = llm_with_tools.invoke(messages)
            print(f"Worker node: Got response with {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0} tool calls")
            
            return {
                "messages": [response],
                "current_step": "navigate"
            }
            
        elif current_step == "navigate":
            # Step 2: Extract text from the page
            system_message = """You are a web scraping expert. Now extract text from the Reddit page.

IMPORTANT: After extracting text, you will search for coordinates of locations mentioned.
"""
            user_message = """Extract all text from the current Reddit page to find recent posts.

IMPORTANT: Extract EVERYTHING you can see, including:
- Post titles and content
- Usernames (look for links that contain '/user/' or start with 'u/')
- Subreddit names
- Any mentions of specific locations, restaurants, events, or activities
- Post timestamps and engagement info

Focus on the main post feed, not the sidebar. Capture the full context of what Redditors are talking about, including any specific place names or addresses mentioned.

After extracting, you will search for coordinates of any locations mentioned."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            print("Worker node: Step 2 - Extracting text...")
            response = llm_with_tools.invoke(messages)
            print(f"Worker node: Got response with {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0} tool calls")
            
            return {
                "messages": [response],
                "current_step": "extract"
            }
            
        elif current_step == "extract":
            # Step 3: Search for coordinates of locations mentioned
            system_message = """You are a web scraping expert. Now search for coordinates of locations mentioned in the Reddit posts.

IMPORTANT: Use the browser to search for exact coordinates of places mentioned. When you navigate to Google Maps, look for coordinates in the URL or business details.
"""
            user_message = """Based on the Reddit content you extracted, identify any specific locations mentioned (restaurants, venues, parks, etc.) and search for their exact coordinates.

For each location mentioned:
1. Navigate to Google Maps (maps.google.com)
2. Search for the EXACT location name + "Toronto, Ontario, Canada"
3. Look for the official business listing with the blue "Business" badge
4. Click on the business listing to get detailed information
5. Extract the exact latitude and longitude coordinates from the URL or business details
6. Verify the location is actually in Toronto, Ontario, Canada
7. Double-check that the coordinates match the actual business/venue mentioned

COORDINATE EXTRACTION METHODS:
- From Google Maps URL: Look for @lat,lng in the URL (e.g., @43.6532,-79.3832)
- From business details: Look for "Coordinates" or "Location" information
- From page source: Search for "latitude" and "longitude" in the page content

If Google Maps doesn't work, try:
- Google Earth (earth.google.com)
- Apple Maps (maps.apple.com)
- OpenStreetMap (openstreetmap.org)

IMPORTANT: Make sure you're getting coordinates for the exact place mentioned, not a similar name or nearby location. Look for official business listings with verified addresses."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            print("Worker node: Step 3 - Searching for coordinates...")
            response = llm_with_tools.invoke(messages)
            print(f"Worker node: Got response with {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0} tool calls")
            
            return {
                "messages": [response],
                "current_step": "create_poi"
            }
            
        else:
            # Step 4: Create one POI based on Reddit content and found coordinates
            system_message = """You are a web scraping expert and local insider. Now create ONE Point of Interest (POI) based on the Reddit posts and coordinates you found.

CRITICAL REQUIREMENTS:
- Create only ONE POI using the EXACT coordinates you found for a real location in Toronto, Ontario, Canada
- The location MUST be specifically mentioned in the Reddit posts
- Use the coordinates you found from your search, not approximate ones
- This POI must be UNIQUE and different from any other POIs
- If no specific real location with coordinates was found, don't create a POI

When you extract text, look for:
- Post titles and content mentioning specific places
- Usernames (they usually start with u/ or appear as links)
- Subreddit names
- Specific mentions of restaurants, venues, parks, events, or activities in Toronto

Use this information to create an engaging POI that sounds like insider knowledge from the Reddit community."""
            user_message = f"""Based on the extracted text from r/{subreddit} and the coordinates you found, create ONE Point of Interest (POI) in {state.get('location_data', {}).get('city', 'Toronto')}, {state.get('location_data', {}).get('province', 'Ontario')}, {state.get('location_data', {}).get('country', 'Canada')}.

CRITICAL REQUIREMENTS:
- The POI MUST be a real, specific location mentioned in the Reddit posts
- Use the EXACT coordinates you found from your search (not approximate ones)
- The location MUST be in {state.get('location_data', {}).get('city', 'Toronto')}, {state.get('location_data', {}).get('province', 'Ontario')}, {state.get('location_data', {}).get('country', 'Canada')}
- This POI must be UNIQUE and different from any other POIs created
- If you didn't find coordinates for a real location, don't create a POI
- DO NOT make up coordinates - only use the ones you found from your search
- VERIFY that the coordinates point to the actual business/venue mentioned, not a residential address or similar location
- Before creating the POI, double-check that the coordinates match the actual place name mentioned
- VALIDATE coordinates: lat should be between 43.5-44.0, lng should be between -79.5 to -79.0 for Toronto

The POI should have:
- A name based on the actual place mentioned (restaurant, venue, park, etc.)
- EXACT coordinates for the real location in {state.get('location_data', {}).get('city', 'Toronto')} (use the coordinates you found)
- A summary about what's happening at this specific location
- Type should be "reddit"
- Radius should be 20

IMPORTANT: Make the summary sound super cool and engaging! Include usernames if you see them in the text. Write it like a local insider telling you about the hottest spots. Use phrases like:
- "According to u/[username], this place is..."
- "The r/{subreddit} community is buzzing about..."
- "Local Redditors are raving about..."
- "This is where the cool kids hang out, says u/[username]"

Focus on specific, real locations mentioned in the posts - restaurants, venues, parks, events, etc. that are actually in {state.get('location_data', {}).get('city', 'Toronto')}."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            print("Worker node: Step 3 - Creating ONE POI...")
            response = llm_with_structured_output.invoke(messages)
            print(f"Worker node: Created POI: {response}")
            
            # Convert Pydantic model to dictionary
            poi_dict = response.model_dump()
            
            return {
                "messages": [HumanMessage(content=f"Created POI: {poi_dict['name']}")],
                "current_step": "complete",
                "pois": [poi_dict]
            }
    
    def tools_condition(state: State) -> str:
        last_message = state["messages"][-1]
        has_tools = hasattr(last_message, "tool_calls") and last_message.tool_calls
        current_step = state.get("current_step", "start")
        print(f"Tools condition: Has tools = {has_tools}, Current step = {current_step}")
        
        if has_tools:
            return "tools"
        else:
            return "summarize"
    
    def summarize(state: State) -> Dict[str, Any]:
        print("Summarize node: Creating final POIs...")
        # Get the POI from the worker
        pois = state.get("pois", [])
        if pois:
            print(f"Summarize node: Returning {len(pois)} POIs")
            return {
                "pois": pois
            }
        else:
            print("Summarize node: No POIs found")
            return {
                "pois": []
            }
    
    # Create graph with State
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("worker", worker)
    workflow.add_node("tools", ToolNode(tools=tools))
    workflow.add_node("summarize", summarize)
    
    # Add edges
    workflow.add_conditional_edges("worker", tools_condition, {
        "tools": "tools",
        "summarize": "summarize"
    })
    workflow.add_edge("tools", "worker")
    workflow.add_edge("summarize", END)
    workflow.set_entry_point("worker")
    
    print("Compiling LangGraph workflow...")
    return workflow.compile() 