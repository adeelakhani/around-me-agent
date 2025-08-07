from playwright.async_api import async_playwright
import asyncio
from utils.location import get_location_name, get_user_location

async def scrape_reddit_local():
    lat, lon = get_user_location()
    location_name = get_location_name(lat, lon)
    
    print(f"🔍 Reddit scraper: Location = {location_name}, Coords = {lat}, {lon}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set user agent to avoid being blocked
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        subreddits = []
        
        # Try to find city-specific subreddit
        try:
            print(f"🔍 Trying subreddit: r/{location_name.lower()}")
            await page.goto(f"https://www.reddit.com/r/{location_name.lower()}/")
            await page.wait_for_timeout(2000)  # Wait for page to load
            
            # Check if page exists by looking for Reddit's error page
            error_text = await page.locator("text=Sorry, nobody on Reddit goes by that name").count()
            if error_text == 0:
                subreddits.append(location_name.lower())
                print(f"✅ Found subreddit: r/{location_name.lower()}")
            else:
                print(f"❌ Subreddit r/{location_name.lower()} not found")
        except Exception as e:
            print(f"❌ Error checking subreddit r/{location_name.lower()}: {e}")
        
        # Add generic subreddits
        subreddits.extend(["local", "community", "events"])
        print(f"📱 Will try subreddits: {subreddits}")
        
        posts = []
        for subreddit in subreddits:
            try:
                print(f"🔍 Scraping r/{subreddit}...")
                await page.goto(f"https://www.reddit.com/r/{subreddit}/")
                await page.wait_for_timeout(3000)  # Wait for content to load
                
                # Try multiple selectors for post titles
                selectors = [
                    "h3",  # Original selector
                    "[data-testid='post-container'] h3",  # More specific
                    "a[data-testid='post-container'] h3",  # Even more specific
                    ".Post h3",  # Class-based selector
                ]
                
                titles = []
                for selector in selectors:
                    try:
                        titles = await page.locator(selector).all_text_contents()
                        if titles:
                            print(f"✅ Found {len(titles)} posts using selector: {selector}")
                            break
                    except:
                        continue
                
                if titles:
                    print(f"📝 Found {len(titles)} posts in r/{subreddit}")
                    
                    # Try to get usernames for each post
                    usernames = []
                    try:
                        username_selectors = [
                            "a[data-testid='post_author_link']",
                            ".Post a[href*='/user/']",
                            "a[href*='/user/']",
                            ".Post span[class*='author']"
                        ]
                        
                        for selector in username_selectors:
                            try:
                                username_elements = await page.locator(selector).all()
                                if username_elements:
                                    for element in username_elements[:len(titles)]:
                                        username = await element.text_content()
                                        if username and username.strip():
                                            usernames.append(username.strip())
                                        else:
                                            usernames.append("Anonymous Redditor")
                                    break
                            except:
                                continue
                        
                        # If we couldn't get usernames, fill with defaults
                        while len(usernames) < len(titles):
                            usernames.append("Anonymous Redditor")
                            
                    except Exception as e:
                        print(f"⚠️ Couldn't extract usernames: {e}")
                        usernames = ["Anonymous Redditor"] * len(titles)
                    
                    # Create posts with usernames
                    for i, title in enumerate(titles[:5]):
                        username = usernames[i] if i < len(usernames) else "Anonymous Redditor"
                        posts.append({
                            "source": f"r/{subreddit}",
                            "title": title,
                            "username": username,
                            "engagement": "🔥 Hot" if i < 2 else "📱 Trending" if i < 4 else "💬 Active"
                        })
                else:
                    print(f"❌ No posts found in r/{subreddit}")
                    
            except Exception as e:
                print(f"❌ Error scraping r/{subreddit}: {e}")
                continue
        
        await browser.close()
        print(f"🎉 Total posts found: {len(posts)}")
        return posts