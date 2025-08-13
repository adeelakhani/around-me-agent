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
        
        url_patterns = [
            r'https://old\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'https://www\.reddit\.com/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'/r/\w+/comments/[\w]+/[\w\-\_]+/?',
            r'comments/([\w]+)/[\w\-\_]+',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                
                if match:
                    if match.startswith('/r/'):
                        full_url = f"https://old.reddit.com{match}"
                    elif match.startswith('http'):
                        full_url = match
                    elif 'comments/' in match:
                        continue
                    else:
                        full_url = f"https://old.reddit.com{match}"
                    
                    full_url = full_url.split('?')[0]
                    full_url = full_url.rstrip('/')
                    
                    if target_subreddit:
                        if f"/r/{target_subreddit}/comments/" in full_url and full_url not in post_urls:
                            post_urls.append(full_url)
                    elif full_url not in post_urls and '/comments/' in full_url:
                        post_urls.append(full_url)
        
        return list(set(post_urls))
        
    except Exception as e:
        print(f"Error extracting Reddit URLs from text: {e}")
        return []

async def extract_reddit_post_urls_from_playwright(page, target_subreddit: str = None) -> List[str]:
    """Extract Reddit post URLs using direct Playwright methods (WORKING METHOD)"""
    try:
        post_urls = []
        
        comment_links = await page.query_selector_all("a[href*='/comments/']")
        
        for link in comment_links:
            try:
                href = await link.get_attribute('href')
                if href and 'reddit.com' in href:
                    if href.startswith('/'):
                        full_url = f"https://old.reddit.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://old.reddit.com{href}"
                    
                    full_url = full_url.split('?')[0].rstrip('/')
                    
                    if target_subreddit:
                        if f"/r/{target_subreddit}/comments/" in full_url:
                            if full_url not in post_urls:
                                post_urls.append(full_url)
                    else:
                        if full_url not in post_urls:
                            post_urls.append(full_url)
            except Exception as e:
                continue
        
        return list(set(post_urls))
        
    except Exception as e:
        print(f"Error extracting URLs with Playwright: {e}")
        return []

def extract_reddit_post_urls(html_content: str) -> List[str]:
    """Extract Reddit post URLs from HTML content using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        post_urls = []
        
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            if '/comments/' in href and 'reddit.com' in href:
                if href.startswith('/'):
                    full_url = f"https://old.reddit.com{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://old.reddit.com{href}"
                
                full_url = full_url.split('?')[0]
                full_url = full_url.rstrip('/')
                
                if full_url not in post_urls:
                    post_urls.append(full_url)
        
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
        
        return list(set(post_urls))
        
    except Exception as e:
        print(f"Error extracting Reddit URLs: {e}")
        return []
