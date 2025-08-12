"""
Municipal API Discovery Agent

Intelligent discovery of municipal 311/open data APIs using:
1. Known patterns for common platforms (CKAN, Socrata, Open311)
2. Domain-restricted searches
3. Actual API validation by fetching and checking response
4. Caching of discovered endpoints
"""

import requests
import json
import os
from typing import Optional, List, Dict, Any
from reddit.geocoding import search_serper

# Known API patterns for different platforms
KNOWN_PATTERNS = {
    "open311": [
        "https://{city_slug}.open311.io/v2/services.json",
        "https://secure.{city_slug}.ca/open311/v2/services.json",
        "https://open311.{city_slug}.gov/v2/services.json",
        "https://api.{city_slug}.gov/open311/v2/services.json"
    ],
    "socrata": [
        "https://data.{city_slug}.gov/resource/",
        "https://{city_slug}-data.gov/resource/",
        "https://data.{city_slug}.ca/resource/"
    ],
    "ckan": [
        "https://{city_slug}-opendata.ca/api/3/action/package_search",
        "https://opendata.{city_slug}.gov/api/3/action/package_search",
        "https://data.{city_slug}.gov/api/3/action/package_search"
    ]
}

def discover_municipal_api_endpoint(city: str, province: str, country: str) -> Optional[str]:
    """
    Discover municipal API endpoint using structured approach.
    
    Args:
        city: City name
        province: Province/state name
        country: Country name
        
    Returns:
        API endpoint URL if found, None otherwise
    """
    print(f"Municipal API Discovery Agent: Searching for {city}, {province}, {country}")
    
    # Step 1: Try known patterns first
    endpoint = try_known_patterns(city, province, country)
    if endpoint:
        return endpoint
    
    # Step 2: Try domain-restricted search
    endpoint = try_domain_restricted_search(city, province, country)
    if endpoint:
        return endpoint
    
    # Step 3: Try broader search with validation
    endpoint = try_broad_search_with_validation(city, province, country)
    if endpoint:
        return endpoint
    
    print("Municipal API Discovery Agent: No valid endpoint found")
    return None

def try_known_patterns(city: str, province: str, country: str) -> Optional[str]:
    """Try known API patterns for common municipal platforms."""
    print("Trying known API patterns...")
    
    city_slug = city.lower().replace(" ", "").replace("-", "")
    
    # Try Open311 patterns
    for pattern in KNOWN_PATTERNS["open311"]:
        url = pattern.format(city_slug=city_slug)
        print(f"Testing Open311 pattern: {url}")
        if is_valid_api_endpoint(url):
            print(f"Found valid Open311 endpoint: {url}")
            return url
    
    # Try Socrata patterns
    for pattern in KNOWN_PATTERNS["socrata"]:
        base_url = pattern.format(city_slug=city_slug)
        # Try common Socrata resource endpoints
        test_urls = [
            f"{base_url}311-requests.json",
            f"{base_url}service-requests.json",
            f"{base_url}complaints.json"
        ]
        for url in test_urls:
            print(f"Testing Socrata pattern: {url}")
            if is_valid_api_endpoint(url):
                print(f"Found valid Socrata endpoint: {url}")
                return url
    
    # Try CKAN patterns and search for 311 datasets
    for pattern in KNOWN_PATTERNS["ckan"]:
        base_url = pattern.format(city_slug=city_slug)
        print(f"Testing CKAN pattern: {base_url}")
        
        # Try to find 311 datasets in CKAN
        ckan_endpoint = find_ckan_311_dataset(base_url, city)
        if ckan_endpoint:
            print(f"Found valid CKAN 311 dataset: {ckan_endpoint}")
            return ckan_endpoint
    
    return None

def try_domain_restricted_search(city: str, province: str, country: str) -> Optional[str]:
    """Search with domain restrictions to avoid SEO junk."""
    print("Trying domain-restricted search...")
    
    # Get country-specific domain
    if country.lower() == "usa":
        domain = "*.gov"
    elif country.lower() == "canada":
        domain = "*.ca"
    else:
        domain = "*.gov"
    
    search_queries = [
        f'site:{domain} "{city}" ("311" OR "service request" OR "open data" OR "municipal data") (api OR json OR endpoint)',
        f'site:{domain} "{city}" "open311" (api OR endpoint)',
        f'site:{domain} "{city}" "municipal services" (api OR json)',
        f'site:{domain} "{city}" "city services" (api OR json)',
        f'site:{domain} "{city}" "public works" (api OR json)'
    ]
    
    for query in search_queries:
        print(f"Searching: {query}")
        search_results = search_serper(query)
        
        if search_results.get("organic"):
            for result in search_results["organic"][:5]:
                link = result.get("link", "")
                if is_valid_api_endpoint(link):
                    print(f"Found valid endpoint via search: {link}")
                    return link
    
    return None

def try_broad_search_with_validation(city: str, province: str, country: str) -> Optional[str]:
    """Simple search for 311 data."""
    print("Trying simple 311 search...")
    
    search_query = f'"{city}" "{province}" 311'
    print(f"Searching: {search_query}")
    search_results = search_serper(search_query)
    
    if search_results.get("organic"):
        for result in search_results["organic"][:5]:
            link = result.get("link", "")
            print(f"Found result: {result.get('title', 'No title')}")
            print(f"Link: {link}")
            
            # Test if it's actually an API endpoint
            if is_valid_api_endpoint(link):
                print(f"Found valid endpoint: {link}")
                return link
    
    return None

def is_valid_api_endpoint(url: str) -> bool:
    """
    Validate if URL is a legitimate API endpoint or dataset by actually fetching it.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid API endpoint or dataset
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("Content-Type", "").lower()
        
        # Accept JSON, CSV, and some text formats
        is_valid_content = any([
            "application/json" in content_type,
            "text/json" in content_type,
            "text/csv" in content_type,
            "application/csv" in content_type,
            "text/plain" in content_type  # Some datasets are served as plain text
        ])
        
        if not is_valid_content:
            print(f"Rejected: Not valid content type ({content_type})")
            return False
        
        # Try to parse as JSON first
        try:
            data = response.json()
            
            # Check for expected structure
            if isinstance(data, dict):
                # Open311 format
                if any(key in data for key in ["service_requests", "service_definitions", "requests", "services"]):
                    print(f"Valid API endpoint: Open311 format")
                    return True
                # General municipal data
                elif len(data) > 0:
                    print(f"Valid API endpoint: JSON object with data")
                    return True
            elif isinstance(data, list) and len(data) > 0:
                print(f"Valid API endpoint: JSON array with data")
                return True
            
        except json.JSONDecodeError:
            # Not JSON, check if it's CSV with location data
            text_content = response.text[:1000]  # Check first 1000 chars
            if "latitude" in text_content.lower() or "lat" in text_content.lower():
                print(f"Valid dataset: CSV with location data")
                return True
        
        print(f"Rejected: Invalid data structure")
        return False
        
    except Exception as e:
        print(f"Rejected: {e}")
        return False

def find_ckan_311_dataset(ckan_base_url: str, city: str) -> Optional[str]:
    """Find 311 datasets in CKAN portal."""
    try:
        # Search for 311 datasets
        search_url = f"{ckan_base_url}package_search?q=311"
        print(f"Searching CKAN for 311 datasets: {search_url}")
        
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not isinstance(data, dict) or not data.get("success") or "result" not in data:
            return None
        
        results = data["result"]["results"]
        print(f"Found {len(results)} datasets in CKAN")
        
        for dataset in results:
            title = dataset.get("title", "").lower()
            tags = [tag.get("name", "").lower() for tag in dataset.get("tags", [])]
            
            # Check if this looks like a 311 dataset
            if any(keyword in title for keyword in ["311", "service request", "complaint"]):
                print(f"Found 311 dataset: {dataset.get('title')}")
                
                # Look for JSON resources
                resources = dataset.get("resources", [])
                for resource in resources:
                    format_type = resource.get("format", "").upper()
                    url = resource.get("url", "")
                    
                    if format_type in ["JSON", "CSV"] and url:
                        print(f"Found {format_type} resource: {url}")
                        return url
        
        return None
        
    except Exception as e:
        print(f"CKAN search error: {e}")
        return None

def is_valid_ckan_endpoint(url: str) -> bool:
    """Validate CKAN API endpoint."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, dict) and data.get("success") and "result" in data:
            print(f"Valid CKAN endpoint")
            return True
        
        return False
    except:
        return False

def looks_like_api_url(url: str) -> bool:
    """Quick check if URL looks like it could be an API endpoint."""
    url_lower = url.lower()
    
    # Must have API indicators
    api_indicators = [".json", ".xml", "/api/", "/v1/", "/v2/", "resource"]
    has_api = any(indicator in url_lower for indicator in api_indicators)
    
    # Exclude obvious non-API sites
    exclude_sites = ["open311.org", "docs", "documentation", "wiki", "help", "blog"]
    is_excluded = any(site in url_lower for site in exclude_sites)
    
    return has_api and not is_excluded
