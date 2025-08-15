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

from reddit.models import POI, POIList
from reddit.geocoding import geocode_with_fallback
from reddit.url_extraction import extract_reddit_post_urls_from_playwright, extract_reddit_post_urls_from_text
from reddit.search_terms import get_random_search_term

load_dotenv(override=True)
nest_asyncio.apply()

async def get_reddit_pois_direct(city: str, province: str, country: str, lat: float, lng: float) -> list:
    """Direct Reddit scraper using LangGraph with proper async browser tools"""
    import random
    
    print(f"Starting LangGraph Reddit scraper for {city}...")
    
    from langchain_community.tools.playwright.utils import create_async_playwright_browser
    async_browser = create_async_playwright_browser(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()
    print(f"Got {len(tools)} Playwright tools: {[tool.name for tool in tools]}")
    
    llm = ChatOpenAI(model="gpt-4o-mini")
    
    from langgraph.graph import StateGraph, END
    from typing import TypedDict, Annotated, List, Any, Optional
    from langgraph.prebuilt import ToolNode
    
    class RedditState(TypedDict):
        messages: Annotated[List[Any], add_messages]
        current_step: str
        scraped_content: Optional[str]
        extracted_pois: Optional[List[Any]]
        city: str
        subreddit: str
        search_term: str
    
    tool_node = ToolNode(tools)
    
    async def scrape_reddit_node(state: RedditState) -> RedditState:
        """Navigate to Reddit and scrape content"""
        print(f"🔍 Scraping r/{state['subreddit']} for things to do in {state['city']}...")
        
        search_urls = [
            f"https://old.reddit.com/r/{state['subreddit']}/search/?q={state['search_term']}&restrict_sr=on&sort=relevance&t=all",
            f"https://old.reddit.com/r/{state['subreddit']}/search/?q={state['search_term']}&restrict_sr=on&sort=hot&t=all",
            f"https://old.reddit.com/r/{state['subreddit']}/search/?q={state['search_term']}&restrict_sr=on&sort=new&t=all",
            f"https://old.reddit.com/r/{state['subreddit']}/top/?q={state['search_term']}&restrict_sr=on&t=all"
        ]
        
        search_url = search_urls[0]
        
        navigate_tool = next(tool for tool in tools if tool.name == "navigate_browser")
        extract_tool = next(tool for tool in tools if tool.name == "extract_text")
        
        print(f"🌐 Navigating to: {search_url}")
        await navigate_tool.arun({"url": search_url})
        
        import asyncio
        await asyncio.sleep(5)
        
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
            print("⏳ Waiting for page to fully load...")
            await asyncio.sleep(5)
            
            current_url = await current_webpage_tool.arun({})
            print(f"📍 Current URL: {current_url}")
            
            print("⏳ Waiting for posts to load...")
            await asyncio.sleep(3)
            
            page = None
            if async_browser.contexts:
                context = async_browser.contexts[0]
                if context.pages:
                    page = context.pages[0]
            
            if not page:
                print("❌ No page available for direct Playwright access")
                return {**state, "scraped_content": state.get("scraped_content", ""), "current_step": "extract_pois"}
            
            print("🔍 Using direct Playwright method to extract Reddit post URLs...")
            post_urls = await extract_reddit_post_urls_from_playwright(page, target_subreddit=state['subreddit'])
            
            if post_urls:
                print(f"✅ Successfully extracted {len(post_urls)} Reddit post URLs using Playwright")
                for i, url in enumerate(post_urls[:5]):
                    subreddit_in_url = "unknown"
                    if "/r/" in url:
                        subreddit_in_url = url.split("/r/")[1].split("/")[0]
                    print(f"  {i+1}. {url} (subreddit: r/{subreddit_in_url})")
            else:
                print("❌ No URLs found with direct Playwright method")
                
                print("🔄 Fallback: Extracting from page content...")
                page_content = await extract_tool.arun({})
                post_urls = extract_reddit_post_urls_from_text(page_content, target_subreddit=state['subreddit'])
                print(f"✅ Extracted {len(post_urls)} URLs from page content")
            
            if post_urls and len(post_urls) > 0:
                filtered_urls = []
                for url in post_urls:
                    if f"/r/{state['subreddit']}/comments/" in url:
                        filtered_urls.append(url)
                    else:
                        print(f"⚠️ Filtered out URL from wrong subreddit: {url}")
                
                if filtered_urls:
                    print(f"✅ Found {len(filtered_urls)} Reddit post URLs from r/{state['subreddit']}")
                    # Remove duplicates and take first 10 unique URLs
                    unique_urls = list(dict.fromkeys(filtered_urls))  # Preserves order while removing duplicates
                    candidate_urls = unique_urls[:10]
                    print(f"🔍 After deduplication: {len(candidate_urls)} unique URLs")
                else:
                    print(f"❌ No URLs found from r/{state['subreddit']} after filtering")
                    candidate_urls = []
                print(f"🔍 Presenting first {len(candidate_urls)} URLs to LLM for relevance selection...")
                
                url_selection_prompt = f"""
                You are analyzing Reddit post URLs to find the most relevant ones for discovering fun and interesting places in {state['city']}.
                
                Your goal is to find posts that are most likely to contain:
                - People asking about or recommending cool places to go
                - Discussions about fun areas, neighborhoods, or spots
                - User experiences and recommendations about places they enjoyed
                - Local insights about interesting locations
                - Also posts that mention nice views and places to see the city
                
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
                    from langchain_openai import ChatOpenAI
                    selection_llm = ChatOpenAI(model="gpt-4o-mini")
                    selection_response = await selection_llm.ainvoke(url_selection_prompt)
                    
                    response_text = selection_response.content
                    print(f"🤖 LLM selection response: {response_text}")
                    
                    import re
                    selected_numbers = re.findall(r'\d+', response_text)
                    selected_indices = [int(num) - 1 for num in selected_numbers if 0 <= int(num) - 1 < len(candidate_urls)]
                    
                    selected_indices = list(set(selected_indices))[:5]  # Remove duplicates and limit to 5
                    
                    if selected_indices:
                        selected_urls = [candidate_urls[i] for i in selected_indices]
                        # Double-check for duplicates in selected URLs
                        unique_selected_urls = list(dict.fromkeys(selected_urls))
                        if len(unique_selected_urls) < len(selected_urls):
                            print(f"⚠️ Removed {len(selected_urls) - len(unique_selected_urls)} duplicate URLs from selection")
                            selected_urls = unique_selected_urls
                        
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
                
                for i, post_url in enumerate(selected_urls):
                    try:
                        print(f"🌐 Navigating to post {i+1}: {post_url[:60]}...")
                        
                        await navigate_tool.arun({"url": post_url})
                        await asyncio.sleep(4)
                        
                        new_url = await current_webpage_tool.arun({})
                        print(f"  📍 Actually navigated to: {new_url}")
                        
                        if "/comments/" in new_url:
                            print(f"  ✅ Successfully navigated to post page!")
                            
                            print(f"  📄 Extracting content from post {i+1}...")
                            post_content = await extract_tool.arun({})
                            
                            if post_content and len(post_content) > 500:
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
                        
                        print(f"  🔙 Going back to search results...")
                        await navigate_tool.arun({"url": search_url})
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        print(f"❌ Error navigating to post {i+1}: {e}")
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
        
        if detailed_content:
            all_content = state.get("scraped_content", "") + "\n\n=== DETAILED POST CONTENT ===\n" + "\n".join(detailed_content)
            print(f"✅ Total content extracted: {len(all_content)} characters from {len(detailed_content)} posts")
        else:
            print("❌ No detailed content extracted from posts")
            all_content = state.get("scraped_content", "")
            
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
        
        reddit_indicators = ['reddit.com', 'r/', 'upvote', 'downvote', 'comment', 'post', 'OP', 'edit:', 'deleted']
        has_reddit_content = any(indicator in content.lower() for indicator in reddit_indicators)
        
        if has_reddit_content:
            print("✅ Content contains Reddit-specific elements - authentic content detected!")
        else:
            print("❌ Content doesn't seem to be from Reddit")
            return {**state, "extracted_pois": [], "current_step": "end"}
        
        llm_with_structured_output = llm.with_structured_output(POIList)
        
        extract_messages = [
            SystemMessage(content=f"""You are analyzing Reddit content to find COOL PLACES that people recommend visiting.

GOAL: Find ALL the interesting, fun, and cool places that Reddit users recommend visiting.

CRITICAL: Be EXTREMELY AGGRESSIVE and THOROUGH in your extraction. Look for ANY place name, business, attraction, neighborhood, or location that people mention positively, recommend, or talk about favorably.

MOST IMPORTANT: For each place you extract, you MUST include the FULL CONTEXT from the Reddit discussion. This means:
- Include the complete sentence or paragraph that mentions the place
- Include what people specifically say about it (reviews, recommendations, experiences)
- Include any details about food, atmosphere, location, prices, etc.
- Include the surrounding context that explains WHY it's worth visiting
- Don't just extract the place name - extract the full story around it
- DO NOT generate or create any text - only use the exact words from the Reddit discussion
- The reddit_context field should contain the actual Reddit user's words, not your interpretation
- CRITICAL: If you can't find enough context for a place, skip it rather than making up descriptions
- Only extract places where you can find genuine Reddit user comments about them

Extract EVERY SINGLE PLACE mentioned in this content, including:
- Restaurants, cafes, bars, food spots, eateries, diners, food trucks
- Museums, galleries, cultural venues, theaters, cinemas, concert halls
- Parks, trails, outdoor spaces, gardens, beaches, hiking spots
- Shopping centers, markets, boutiques, malls, stores, shops
- Entertainment venues, clubs, pubs, lounges, arcades, game rooms
- Tourist attractions, landmarks, monuments, buildings, towers
- Local businesses, services, spas, salons, gyms, fitness centers
- Neighborhoods, districts, areas, zones, quarters, villages
- Streets, avenues, roads, intersections that people mention as destinations
- Any specific place names, business names, or locations that people talk about positively

BE EXTREMELY LIBERAL - if someone mentions a place name in a positive context, extract it. Don't be conservative. Extract as many places as possible.

For each place, provide:
1. The exact name as mentioned
2. A brief description based on what's said about it
3. The category
4. The specific Reddit context where it's mentioned (the actual text that mentions this place) - THIS MUST BE THE FULL CONTEXT, NOT JUST THE PLACE NAME

Extract AT LEAST 15-20 places if possible. Be comprehensive and thorough."""),
            HumanMessage(content=f"""Find ALL COOL PLACES that people recommend visiting.

Here is the Reddit content to analyze:

{content[:12000]}

IMPORTANT: For each place you find, make sure to capture the FULL CONTEXT from the Reddit discussion. Include:
- What people specifically say about the place
- Their experiences, recommendations, or reviews
- Details about food, atmosphere, location, prices, etc.
- The surrounding sentences that explain why it's worth visiting
- Don't just extract the place name - get the full story
- CRITICAL: Only use the exact words from Reddit users - do not generate or create any text
- The reddit_context must be authentic Reddit content, not AI-generated descriptions
- IMPORTANT: Skip any place where you can't find genuine Reddit user comments about it
- Quality over quantity - better to have fewer authentic POIs than more fake ones

Extract EVERY SINGLE PLACE mentioned in this content, including:
- Restaurants, cafes, bars, food spots, eateries, diners, food trucks
- Museums, galleries, cultural venues, theaters, cinemas, concert halls
- Parks, trails, outdoor spaces, gardens, beaches, hiking spots
- Shopping centers, markets, boutiques, malls, stores, shops
- Entertainment venues, clubs, pubs, lounges, arcades, game rooms
- Tourist attractions, landmarks, monuments, buildings, towers
- Local businesses, services, spas, salons, gyms, fitness centers
- Neighborhoods, districts, areas, zones, quarters, villages
- Streets, avenues, roads, intersections that people mention as destinations
- Any specific place names, business names, or locations that people talk about positively

BE EXTREMELY LIBERAL - if someone mentions a place name in a positive context, extract it. Don't be conservative. Extract as many places as possible.

For each place, provide:
1. The exact name as mentioned
2. A brief description based on what's said about it
3. The category
4. The specific Reddit context where it's mentioned (the actual text that mentions this place) - INCLUDE THE FULL CONTEXT

Extract AT LEAST 15-20 places if possible. Be comprehensive and thorough.""")
        ]
        
        pois_response = await llm_with_structured_output.ainvoke(extract_messages)
        pois = pois_response.pois
        print(f"Extracted {len(pois)} POIs: {[poi.name for poi in pois]}")
        
        print("🔍 Running aggressive regex extraction as fallback...")
        import re
        
        capitalized_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',
            r'\b[A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+\b',
        ]
        
        place_indicators = [
            r'\b[A-Z][a-z]+ (Street|Avenue|Road|Boulevard|Drive|Lane|Place|Court|Terrace|Crescent)\b',
            r'\b[A-Z][a-z]+ (Park|Museum|Gallery|Theater|Theatre|Cinema|Restaurant|Cafe|Bar|Pub|Club)\b',
            r'\b[A-Z][a-z]+ (Market|Mall|Centre|Center|Plaza|Square|Building|Tower|Bridge|Station)\b',
            r'\b[A-Z][a-z]+ (Island|Beach|Trail|Path|Garden|Zoo|Aquarium|Stadium|Arena|Hall)\b',
        ]
        
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
                common_words = ['Reddit', 'Toronto', 'Canada', 'Ontario', 'Personal', 'Please', 'Submit', 'Share', 'Reply', 'Comment', 'Post', 'User', 'Member', 'Online', 'Filter', 'Show', 'Hide', 'Sort', 'Best', 'Top', 'New', 'Old', 'Controversial', 'Q&A', 'More', 'Less', 'Points', 'Children', 'Permalink', 'Embed', 'Save', 'Parent', 'Report', 'Track', 'Me', 'Reply', 'Share', 'More', 'Replies', 'Sort', 'By', 'Best', 'Top', 'New', 'Controversial', 'Old', 'Q&A', 'Open', 'Comment', 'Options', 'Best', 'Top', 'New', 'Controversial', 'Old', 'Q&A']
                if match not in common_words and len(match) > 3:
                    found_places.add(match)
        
        print(f"🔍 Regex found {len(found_places)} additional potential places")
        
        if len(pois) < 5 and found_places:
            print(f"⚠️ LLM only found {len(pois)} POIs, using regex results as backup...")
            for place_name in list(found_places)[:20]:
                if not any(poi.name.lower() == place_name.lower() for poi in pois):
                    non_place_words = [
                        'hello', 'picture', 'discussion', 'filter', 'megathread', 'user', 'agreement', 
                        'alerts', 'monthly', 'meetup', 'traditionally', 'pictures', 'rules', 'this', 'all', 
                        'show', 'hide', 'sort', 'best', 'top', 'new', 'old', 'controversial', 'q&a', 'more', 
                        'less', 'points', 'children', 'permalink', 'embed', 'save', 'parent', 'report', 
                        'track', 'reply', 'share', 'replies', 'open', 'comment', 'options', 'submit', 
                        'edit', 'delete', 'moderators', 'guidelines'
                    ]
                    
                    if any(word in place_name.lower() for word in non_place_words):
                        continue
                        
                    if len(place_name.split()) == 1 and place_name.lower() in ['street', 'park', 'road', 'avenue', 'drive', 'lane', 'place', 'court', 'terrace', 'crescent']:
                        continue
                        
                    if place_name.lower() in ['hello', 'picture', 'discussion', 'filter', 'megathread', 'cheap', 'user', 'agreement', 'alerts', 'monthly', 'meetup', 'traditionally', 'pictures', 'rules', 'street', 'park', 'gems', 'march', 'january', 'december', 'former', 'new', 'york', 'greenwich', 'village', 'sunset', 'playoff', 'hockey', 'this', 'all', 'show', 'hide', 'sort', 'best', 'top', 'new', 'old', 'controversial', 'q&a', 'more', 'less', 'points', 'children', 'permalink', 'embed', 'save', 'parent', 'report', 'track', 'reply', 'share', 'replies', 'open', 'comment', 'options', 'submit', 'edit', 'delete', 'moderators', 'guidelines']:
                        continue
                    
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
        """Create descriptions using the actual reddit_context found during POI extraction"""
        print("✍️ Creating descriptions from actual Reddit context...")
        
        pois = state.get("extracted_pois", [])
        if not pois:
            print("❌ No POIs to create descriptions for")
            return {**state, "extracted_pois": [], "current_step": "end"}
        
        print(f"🔍 Creating descriptions for {len(pois)} POIs using their reddit_context...")
        
        for poi in pois:
            try:
                place_name = poi.name
                
                if hasattr(poi, 'reddit_context') and poi.reddit_context:
                    import re
                    
                    context = poi.reddit_context.strip()
                    context = re.sub(r'\[.*?\]', '', context)  # Remove Reddit formatting like [text]
                    context = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', context)  # Remove URLs
                    
                    # COMMENTED OUT: Sentence splitting logic - using full context instead
                    # sentences = re.split(r'[.!?]+', context)
                    # best_sentence = None
                    # 
                    # for sentence in sentences:
                    #     sentence = sentence.strip()
                    #     if len(sentence) < 15 or len(sentence) > 150:
                    #         continue
                    #         
                    #     ui_words = ['permalink', 'embed', 'save', 'parent', 'report', 'track', 'reply', 'share', 'more', 'replies', 'sort', 'best', 'top', 'new', 'controversial', 'old', 'q&a', 'open', 'comment', 'options', 'filter', 'show', 'hide', 'submit', 'edit', 'delete', 'moderators', 'rules', 'guidelines']
                    #     if any(word in sentence.lower() for word in ui_words):
                    #         continue
                    #         
                    #     descriptive_words = ['restaurant', 'cafe', 'bar', 'pub', 'park', 'museum', 'gallery', 'theater', 'cinema', 'shop', 'store', 'market', 'mall', 'attraction', 'landmark', 'venue', 'place', 'spot', 'area', 'neighborhood', 'district', 'pizza', 'food', 'drink', 'eat', 'visit', 'go', 'check out', 'try', 'recommend', 'suggest', 'good', 'great', 'amazing', 'awesome', 'excellent', 'fantastic', 'wonderful', 'best', 'love', 'like', 'worth', 'nice', 'cool', 'interesting', 'popular', 'famous', 'known for', 'favorite', 'must see', 'must visit']
                    #     
                    #     if any(word in sentence.lower() for word in descriptive_words):
                    #         best_sentence = sentence
                    #         break
                    # 
                    # if not best_sentence:
                    #     for sentence in sentences:
                    #         sentence = sentence.strip()
                    #         if len(sentence) > 15 and len(sentence) < 100:
                    #             if sentence.lower() != place_name.lower():
                    #                 best_sentence = sentence
                    #                 break
                    # 
                    # if best_sentence:
                    #     poi.description = best_sentence
                    #     print(f"✅ Created description for {place_name}: {best_sentence[:80]}...")
                    # else:
                    #     if len(context) > 200:
                    #         context = context[:200] + "..."
                    #     poi.description = context
                    #     print(f"✅ Used context for {place_name}: {context[:80]}...")
                    
                    if len(context) > 500:
                        context = context[:500] + "..."
                    poi.description = context
                    print(f"✅ Used full context for {place_name}: {context[:80]}...")
                
                if hasattr(poi, 'reddit_context') and poi.reddit_context:
                    if len(poi.description) < 10 or poi.description.lower() in [
                        "popular restaurant", "popular cafe", "popular bar", "popular attraction",
                        "mentioned in discussions", "popular spot", "well-known place"
                    ]:
                        poi.description = poi.reddit_context[:200] if len(poi.reddit_context) > 200 else poi.reddit_context
                else:
                    poi.description = f"Popular {poi.category.lower()} mentioned in r/{state['subreddit']} discussions"
                    print(f"⚠️ No context for {place_name}, using fallback")
                    
            except Exception as e:
                print(f"❌ Error processing {poi.name}: {e}")
                poi.description = f"Popular {poi.category.lower()} in {state['city']}"
        
        print(f"✅ Created descriptions for {len(pois)} POIs using actual Reddit context")
        
        return {
            **state,
            "extracted_pois": pois,
            "current_step": "end"
        }
    
    workflow = StateGraph(RedditState)
    
    workflow.add_node("scrape_reddit", scrape_reddit_node)
    workflow.add_node("click_posts", click_posts_node)
    workflow.add_node("extract_pois", extract_pois_node)
    workflow.add_node("create_descriptions", create_descriptions_node)
    
    workflow.add_edge("scrape_reddit", "click_posts")
    workflow.add_edge("click_posts", "extract_pois")
    workflow.add_edge("extract_pois", "create_descriptions")
    workflow.add_edge("create_descriptions", END)
    
    workflow.set_entry_point("scrape_reddit")
    
    app = workflow.compile()
    
    subreddit = city.lower()
    
    search_term = get_random_search_term(city)
    
    print(f"🔍 Using search term: {search_term}")
    
    try:
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
        
        final_pois = []
        for poi in pois:
            print(f"🗺️ Geocoding {poi.name}...")
            
            coords = geocode_with_fallback(poi.name, city, province, country)
            
            if coords:
                poi_output = {
                    "name": poi.name,
                    "lat": coords['lat'],
                    "lng": coords['lng'],
                    "summary": poi.description,
                    "type": "reddit",
                    "radius": 20
                }
                print(f"✅ Geocoded {poi.name}: ({coords['lat']}, {coords['lng']})")
            else:
                print(f"⚠️ Geocoding failed for {poi.name}, using fallback coordinates")
                lat_variation = random.uniform(-0.005, 0.005)
                lng_variation = random.uniform(-0.005, 0.005)
                
                poi_output = {
                    "name": poi.name,
                    "lat": lat + lat_variation,
                    "lng": lng + lng_variation,
                    "summary": poi.description,
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

