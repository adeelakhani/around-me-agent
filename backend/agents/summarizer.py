from typing import Annotated, TypedDict, List, Any, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langgraph.prebuilt import ToolNode
import os
import nest_asyncio

nest_asyncio.apply()

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

def create_summarizer_agent():
    print("Creating LangGraph agent with Playwright tools...")
    
    # Get Playwright tools like in the notebook
    async_browser = create_async_playwright_browser(headless=True)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    print(f"Got {len(tools)} Playwright tools: {[tool.name for tool in tools]}")
    
    # Initialize LLM with tools
    llm = ChatOpenAI(model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools(tools)
    
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

IMPORTANT: After extracting text, you will analyze it and create a summary. Do not navigate again.
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
            # Step 3: Create summary
            system_message = """You are a web scraping expert. Now create a summary of the Reddit posts you found.

IMPORTANT: This is the final step. Create a summary and stop.
"""
            user_message = """Based on the extracted text from Reddit, create an exciting summary of recent local posts.

Focus on posts about Toronto events, restaurants, community discussions, and local news.
Make it sound like a local friend telling you what's happening in the area."""
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            print("Worker node: Step 3 - Creating summary...")
            response = llm_with_tools.invoke(messages)
            print(f"Worker node: Got response with {len(response.tool_calls) if hasattr(response, 'tool_calls') else 0} tool calls")
            
            return {
                "messages": [response],
                "current_step": "complete"
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
        print("Summarize node: Creating final summary...")
        # Get the final response from the worker
        last_message = state["messages"][-1]
        summary = last_message.content or "No summary available"
        print(f"Summarize node: Final summary = {summary[:200]}...")
        
        return {
            "summary": summary
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