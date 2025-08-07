from playwright.async_api import async_playwright
import asyncio
from utils.location import get_location_name, get_user_location

async def scrape_reddit_local():
    lat, lon = get_user_location()
    location_name = get_location_name(lat, lon)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        subreddits = []
        
        try:
            await page.goto(f"https://www.reddit.com/r/{location_name.lower()}/")
            if await page.locator("h1").count() > 0:
                subreddits.append(location_name.lower())
        except:
            pass
        
        subreddits.extend(["local", "community", "events"])
        
        posts = []
        for subreddit in subreddits:
            try:
                await page.goto(f"https://www.reddit.com/r/{subreddit}/")
                titles = await page.locator("h3").all_text_contents()
                posts.extend([{"source": f"r/{subreddit}", "title": title} for title in titles[:3]])
            except:
                continue
        
        await browser.close()
        return posts