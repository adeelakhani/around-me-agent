from typing import Annotated, TypedDict, List, Any, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os

# Define the State like in your notebook
class State(TypedDict):
    messages: Annotated[List[Any], add_messages]
    location_data: Dict
    reddit_data: List[Dict]
    weather_data: Dict
    events_data: List[Dict]
    news_data: List[Dict]
    summary: Optional[str]

def create_summarizer_agent():
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    def summarize_location_data(state: State) -> Dict[str, Any]:
        # Get specific location data
        location_data = state.get("location_data", {})
        location_name = location_data.get("name", "Unknown Location")
        location_type = location_data.get("type", "unknown")
        specific_data = location_data.get("data", {})
        lat = location_data.get("lat", 0)
        lon = location_data.get("lon", 0)
        
        # Create summary based on the type of data
        if location_type == "weather":
            temp = specific_data.get("main", {}).get("temp", "N/A")
            description = specific_data.get("weather", [{}])[0].get("description", "N/A")
            humidity = specific_data.get("main", {}).get("humidity", "N/A")
            
            summary = f"🌤️ Current Weather: {temp}°C, {description}\n"
            summary += f"💧 Humidity: {humidity}%\n"
            summary += f"📍 Location: {location_name}"
            
        elif location_type == "event":
            event_name = specific_data.get("name", {}).get("text", "Unknown Event")
            start_time = specific_data.get("start", {}).get("local", "Unknown Time")
            venue = specific_data.get("venue", {}).get("name", "Unknown Venue")
            
            summary = f"🎉 Event: {event_name}\n"
            summary += f"⏰ Time: {start_time}\n"
            summary += f"📍 Venue: {venue}\n"
            summary += f"📍 Location: {location_name}"
            
        elif location_type == "news":
            title = specific_data.get("title", "Unknown News")
            description = specific_data.get("description", "No description available")
            published = specific_data.get("publishedAt", "Unknown date")
            
            summary = f"📰 News: {title}\n"
            summary += f"📝 {description[:100]}...\n"
            summary += f"📅 Published: {published[:10]}\n"
            summary += f"📍 Location: {location_name}"
            
        elif location_type == "reddit":
            title = specific_data.get("title", "Unknown Post")
            source = specific_data.get("source", "Unknown Subreddit")
            
            summary = f"💬 Reddit: {title}\n"
            summary += f"📱 From: {source}\n"
            summary += f"📍 Location: {location_name}"
            
        else:
            summary = f"📍 Location: {location_name}\n"
            summary += f"📍 Coordinates: {lat}, {lon}"
        
        messages = [
            SystemMessage(content=f"You are a local data summarizer. Create an exciting, actionable summary for this specific location. Make it feel like a local friend telling you what's happening here."),
            HumanMessage(content=f"Create a summary for {location_name} ({location_type}): {summary}")
        ]
        
        response = llm.invoke(messages)
        
        # Return updated state with messages and summary
        return {
            "messages": [response],
            "summary": response.content
        }
    
    # Create graph with State
    workflow = StateGraph(State)
    workflow.add_node("summarize", summarize_location_data)
    workflow.set_entry_point("summarize")
    workflow.add_edge("summarize", END)
    
    return workflow.compile() 