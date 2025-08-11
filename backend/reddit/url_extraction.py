"""
Reddit URL extraction utilities
"""
import re
from typing import List
from bs4 import BeautifulSoup

def extract_reddit_post_urls_from_text(text_content: str, target_subreddit: str = None) -> List[str]:
    """Extract Reddit post URLs from plain text content using regex patterns"""
    try:
        post_urls = []
        
        # Look for Reddit post patterns in plain text
        # These patterns match the format of Reddit post URLs that might appear in text
        url_patterns = [
            # Full URLs
            r'https://old\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://www\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            # Relative URLs
            r'/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            # Post IDs (common in Reddit text)
            r'comments/([\w]+)/[\w\-\_]+',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    # If it's a tuple (from group capture), take the first element
                    match = match[0] if match else ""
                
                if match:
                    # Normalize URL
                    if match.startswith('/r/'):
                        full_url = f"https://old.reddit.com{match}"
                    elif match.startswith('http'):
                        full_url = match
                    elif 'comments/' in match:
                        # This is a post ID, construct the URL - use dynamic subreddit
                        # We'll need to get the subreddit from context or use a generic approach
                        # For now, skip these as we can't determine the correct subreddit
                        continue
                    else:
                        full_url = f"https://old.reddit.com{match}"
                    
                    # Clean up the URL
                    full_url = full_url.split('?')[0]  # Remove query parameters
                    full_url = full_url.rstrip('/')  # Remove trailing slash
                    
                    # Filter by subreddit if specified
                    if target_subreddit:
                        if f"/r/{target_subreddit}/comments/" in full_url and full_url not in post_urls:
                            post_urls.append(full_url)
                    elif full_url not in post_urls and '/comments/' in full_url:
                        post_urls.append(full_url)
        
        return list(set(post_urls))  # Remove duplicates
        
    except Exception as e:
        print(f"Error extracting Reddit URLs from text: {e}")
        return []

async def extract_reddit_post_urls_from_playwright(page, target_subreddit: str = None) -> List[str]:
    """Extract Reddit post URLs using direct Playwright methods (WORKING METHOD)"""
    try:
        post_urls = []
        
        # Use Playwright's direct methods to get all links with href containing '/comments/'
        comment_links = await page.query_selector_all("a[href*='/comments/']")
        
        for link in comment_links:
            try:
                href = await link.get_attribute('href')
                if href and 'reddit.com' in href:
                    # Normalize URL
                    if href.startswith('/'):
                        full_url = f"https://old.reddit.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://old.reddit.com{href}"
                    
                    # Clean up the URL
                    full_url = full_url.split('?')[0].rstrip('/')
                    
                    # Filter by subreddit if specified
                    if target_subreddit:
                        if f"/r/{target_subreddit}/comments/" in full_url:
                            if full_url not in post_urls:
                                post_urls.append(full_url)
                    else:
                        if full_url not in post_urls:
                            post_urls.append(full_url)
            except Exception as e:
                continue
        
        return list(set(post_urls))  # Remove duplicates
        
    except Exception as e:
        print(f"Error extracting URLs with Playwright: {e}")
        return []

def extract_reddit_post_urls_from_elements(elements: List[dict]) -> List[str]:
    """Extract Reddit post URLs from Playwright elements"""
    try:
        post_urls = []
        
        for element in elements:
            if isinstance(element, dict):
                # Check for href attribute
                href = element.get('href', '')
                if '/comments/' in href:
                    # Normalize URL
                    if href.startswith('/'):
                        full_url = f"https://old.reddit.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://old.reddit.com{href}"
                    
                    # Clean up the URL
                    full_url = full_url.split('?')[0].rstrip('/')
                    
                    if full_url not in post_urls:
                        post_urls.append(full_url)
        
        return list(set(post_urls))
        
    except Exception as e:
        print(f"Error extracting URLs from elements: {e}")
        return []

def extract_reddit_post_urls(html_content: str) -> List[str]:
    """Extract Reddit post URLs from HTML content using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        post_urls = []
        
        # Look for links that contain /comments/ pattern
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            if '/comments/' in href and 'reddit.com' in href:
                # Normalize URL
                if href.startswith('/'):
                    full_url = f"https://old.reddit.com{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://old.reddit.com{href}"
                
                # Clean up the URL
                full_url = full_url.split('?')[0]  # Remove query parameters
                full_url = full_url.rstrip('/')  # Remove trailing slash
                
                if full_url not in post_urls:
                    post_urls.append(full_url)
        
        # Also try regex patterns as backup
        url_patterns = [
            r'https://old\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'href="(/r/\w+/comments/[\w]+/[\w\-\_]+/?)"',
            r'href="(https://old\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?)"',
            r'href="(https://reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?)"',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if match.startswith('/r/'):
                    full_url = f"https://old.reddit.com{match}"
                elif match.startswith('http'):
                    full_url = match
                else:
                    full_url = f"https://old.reddit.com{match}"
                
                full_url = full_url.split('?')[0].rstrip('/')
                if full_url not in post_urls:
                    post_urls.append(full_url)
        
        return list(set(post_urls))  # Remove duplicates
        
    except Exception as e:
        print(f"Error extracting Reddit URLs: {e}")
        return []
