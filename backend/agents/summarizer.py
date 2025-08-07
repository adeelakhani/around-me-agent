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

def create_summarizer_agent():
    print("Creating LangGraph agent with Playwright tools...")
    
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
            user_message = """Navigate to https://www.reddit.com/r/toronto/ and then move to the next step.

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

IMPORTANT: After extracting text, you will analyze it and create a POI. Do not navigate again.
"""
            user_message = """Extract all text from the current Reddit page to find recent posts.

Look for post titles, usernames, and post content. Focus on the main post feed, not the sidebar."""
            
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
            
        else:
            # Step 3: Create one POI based on Reddit content
            system_message = """You are a web scraping expert. Now create ONE Point of Interest (POI) based on the Reddit posts you found.

IMPORTANT: Create only ONE POI with coordinates near downtown Toronto (around 43.65, -79.38).
"""
            user_message = """Based on the extracted text from Reddit, create ONE Point of Interest (POI) around Toronto.

The POI should have:
- A name based on what you found (restaurant, event, community spot)
- Coordinates near downtown Toronto (around 43.65, -79.38)
- A summary about what's happening at this location
- Type should be "reddit"
- Radius should be 20

Make it exciting and specific - like a local friend telling you about a particular spot in the city."""
            
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
            print("Summarize node: No POIs found, creating fallback")
            # Create fallback POIs
            fallback_pois = [
                {
                    "name": "Reddit - Downtown Toronto",
                    "lat": 43.6532,
                    "lng": -79.3832,
                    "summary": "Local Reddit community discussions about downtown events and restaurants",
                    "type": "reddit",
                    "radius": 20
                },
                {
                    "name": "Reddit - Local Community",
                    "lat": 43.6632,
                    "lng": -79.3932,
                    "summary": "Community posts about neighborhood events and local businesses",
                    "type": "reddit",
                    "radius": 20
                },
                {
                    "name": "Reddit - City Events",
                    "lat": 43.6432,
                    "lng": -79.3732,
                    "summary": "Recent posts about upcoming city events and cultural activities",
                    "type": "reddit",
                    "radius": 20
                },
                {
                    "name": "Reddit - Neighborhood",
                    "lat": 43.6732,
                    "lng": -79.3632,
                    "summary": "Local neighborhood discussions and community updates",
                    "type": "reddit",
                    "radius": 20
                }
            ]
            return {
                "pois": fallback_pois
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