"""
Municipal API Discovery Agent

Intelligent discovery of municipal 311/open data APIs using:
1. Search for official 311 portals using "{city} {province} 311" pattern
2. Extract API endpoints from official portal pages
3. Known patterns for common platforms (CKAN, Socrata, Open311) as fallback
4. Actual API validation by fetching and checking response
5. Caching of discovered endpoints
"""

import requests
import json
import os
import re
from typing import Optional, List, Dict, Any
from reddit.geocoding import search_serper
from .data_portal_discovery import DataPortalDiscovery
from datetime import datetime, timedelta

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
        "https://{city_slug}-opendata.ca",
        "https://opendata.{city_slug}.gov",
        "https://data.{city_slug}.gov"
    ]
}

def discover_municipal_api_endpoint(city: str, province: str, country: str) -> Optional[str]:
    """
    Discover municipal API endpoint using comprehensive approach.
    
    Args:
        city: City name
        province: Province/state name
        country: Country name
        
    Returns:
        API endpoint URL if found, None otherwise
    """
    print(f"Municipal API Discovery Agent: Searching for {city}, {province}, {country}")
    
    endpoint = find_official_311_portal(city, province, country)
    if endpoint:
        return endpoint
    
    portal_discovery = DataPortalDiscovery()
    endpoint = portal_discovery.discover_311_data(city, province, country)
    if endpoint:
        return endpoint
    
    endpoint = try_known_patterns(city, province, country)
    if endpoint:
        return endpoint
    
    endpoint = try_domain_restricted_search(city, province, country)
    if endpoint:
        return endpoint
    
    print("Municipal API Discovery Agent: No valid endpoint found")
    return None

def find_official_311_portal(city: str, province: str, country: str) -> Optional[str]:
    """
    Find the official 311 portal by searching "{city} {province} 311 api" first,
    then fallback to "{city} {province} 311" if no API endpoints found.
    """
    print(f"Searching for official 311 portal with API focus: {city} {province} 311 api")
    
    search_query = f'"{city}" "{province}" "311" "api"'
    
    try:
        search_results = search_serper(search_query)
        
        if search_results.get("organic"):
            first_result = search_results["organic"][0]
            portal_url = first_result.get("link", "")
            title = first_result.get("title", "")
            
            print(f"Found portal with API search: {title}")
            print(f"Portal URL: {portal_url}")
            
            if is_official_government_portal(portal_url, city, province):
                print(f"Confirmed official government portal: {portal_url}")
                
                api_endpoint = extract_api_from_official_portal(portal_url, city)
                if api_endpoint:
                    print(f"Found API endpoint in official portal: {api_endpoint}")
                    return api_endpoint
                
                download_endpoint = extract_download_links_from_portal(portal_url, city)
                if download_endpoint:
                    print(f"Found download endpoint in official portal: {download_endpoint}")
                    return download_endpoint
                
                data_portal_endpoint = extract_data_portal_from_official_portal(portal_url, city)
                if data_portal_endpoint:
                    print(f"Found data portal link: {data_portal_endpoint}")
                    return data_portal_endpoint
            else:
                print(f"Not an official government portal: {portal_url}")
        
        print(f"API search didn't find endpoints, trying general 311 search: {city} {province} 311")
        fallback_query = f'"{city}" "{province}" "311"'
        
        search_results = search_serper(fallback_query)
        
        if search_results.get("organic"):
            first_result = search_results["organic"][0]
            portal_url = first_result.get("link", "")
            title = first_result.get("title", "")
            
            print(f"Found portal with general search: {title}")
            print(f"Portal URL: {portal_url}")
            
            if is_official_government_portal(portal_url, city, province):
                print(f"Confirmed official government portal: {portal_url}")
                
                api_endpoint = extract_api_from_official_portal(portal_url, city)
                if api_endpoint:
                    print(f"Found API endpoint in official portal: {api_endpoint}")
                    return api_endpoint
                
                download_endpoint = extract_download_links_from_portal(portal_url, city)
                if download_endpoint:
                    print(f"Found download endpoint in official portal: {download_endpoint}")
                    return download_endpoint
                
                data_portal_endpoint = extract_data_portal_from_official_portal(portal_url, city)
                if data_portal_endpoint:
                    print(f"Found data portal link: {data_portal_endpoint}")
                    return data_portal_endpoint
            else:
                print(f"Not an official government portal: {portal_url}")
        
        return None
        
    except Exception as e:
        print(f"Error searching for official 311 portal: {e}")
        return None

def is_official_government_portal(url: str, city: str, province: str) -> bool:
    """
    Validate if URL is an official government portal.
    """
    url_lower = url.lower()
    city_lower = city.lower()
    province_lower = province.lower()
    
    government_domains = [
        ".gov", ".gov.ca", ".ca", ".gc.ca",
        ".gov", ".gov.us", ".us",
        ".gov.uk", ".uk",
        ".gov.au", ".au",
    ]
    
    is_government_domain = any(domain in url_lower for domain in government_domains)
    
    contains_city = city_lower in url_lower or city_lower.replace(" ", "") in url_lower
    
    exclude_sites = [
        "wikipedia", "facebook", "twitter", "instagram", "youtube", "linkedin",
        "yelp", "tripadvisor", "google", "bing", "yahoo", "reddit", "quora",
        "stackoverflow", "github", "medium", "wordpress", "blogspot"
    ]
    
    is_excluded = any(site in url_lower for site in exclude_sites)
    
    return is_government_domain and contains_city and not is_excluded

def extract_api_from_official_portal(portal_url: str, city: str) -> Optional[str]:
    """
    Extract API endpoints from an official government portal page.
    """
    try:
        print(f"Extracting API endpoints from portal: {portal_url}")
        
        response = requests.get(portal_url, timeout=15)
        response.raise_for_status()
        
        content = response.text
        content_lower = content.lower()
        
        api_patterns = [
            r'https?://[^"\s]+open311[^"\s]*/v2/services\.json',
            r'https?://[^"\s]+open311[^"\s]*/v2/requests\.json',
            
            r'https?://data\.[^"\s]+\.gov/resource/[^"\s]+\.json',
            r'https?://data\.[^"\s]+\.ca/resource/[^"\s]+\.json',
            r'https?://[^"\s]+-data\.gov/resource/[^"\s]+\.json',
            
            r'https?://[^"\s]+/api/3/action/[^"\s]+',
            r'https?://[^"\s]+/datastore_search[^"\s]*',
            r'https?://[^"\s]+/package_show[^"\s]*',
            
            r'https?://[^"\s]+/explore/dataset/[^"\s]+/api/',
            r'https?://[^"\s]+/api/explore/v2\.1/catalog/datasets/[^"\s]+',
            
            r'https?://[^"\s]+/api/[^"\s]+\.json',
            r'https?://[^"\s]+/rest/[^"\s]+\.json',
            r'https?://[^"\s]+/services/[^"\s]+\.json',
            
            r'https?://[^"\s]+311[^"\s]*\.json',
            r'https?://[^"\s]+service-requests[^"\s]*\.json',
            r'https?://[^"\s]+complaints[^"\s]*\.json',
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                clean_url = match.strip('"\'')
                
                if not clean_url.startswith('http'):
                    continue
                
                print(f"Found potential API endpoint: {clean_url}")
                
                if '/explore/dataset/' in clean_url and '/api/' in clean_url:
                    dataset_match = re.search(r'/explore/dataset/([^/]+)/', clean_url)
                    if dataset_match:
                        base_url = re.search(r'(https?://[^/]+)', clean_url)
                        if base_url:
                            dataset_name = dataset_match.group(1)
                            proper_api_url = f"{base_url.group(1)}/api/explore/v2.1/catalog/datasets/{dataset_name}/records?limit=1"
                            print(f"Converting to proper API URL: {proper_api_url}")
                            
                            if is_valid_api_endpoint(proper_api_url):
                                print(f"Valid converted API endpoint found: {proper_api_url}")
                                return proper_api_url
                
                if is_valid_api_endpoint(clean_url):
                    print(f"Valid API endpoint found: {clean_url}")
                    return clean_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting API from portal: {e}")
        return None

def extract_download_links_from_portal(portal_url: str, city: str) -> Optional[str]:
    """
    Extract data download links from an official government portal page.
    """
    try:
        print(f"Extracting download links from portal: {portal_url}")
        
        response = requests.get(portal_url, timeout=15)
        response.raise_for_status()
        
        content = response.text
        content_lower = content.lower()
        
        download_patterns = [
            r'https?://[^"\s]+\.csv[^"\s]*',
            r'https?://[^"\s]+\.json[^"\s]*',
            r'https?://[^"\s]+\.zip[^"\s]*',
            r'https?://[^"\s]+\.xlsx[^"\s]*',
            
            r'https?://[^"\s]+311[^"\s]*\.csv[^"\s]*',
            r'https?://[^"\s]+311[^"\s]*\.json[^"\s]*',
            r'https?://[^"\s]+311[^"\s]*\.zip[^"\s]*',
            r'https?://[^"\s]+service-requests[^"\s]*\.csv[^"\s]*',
            r'https?://[^"\s]+service-requests[^"\s]*\.json[^"\s]*',
            r'https?://[^"\s]+complaints[^"\s]*\.csv[^"\s]*',
            r'https?://[^"\s]+complaints[^"\s]*\.json[^"\s]*',
        ]
        
        for pattern in download_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                clean_url = match.strip('"\'')
                
                if not clean_url.startswith('http'):
                    continue
                
                print(f"Found potential download link: {clean_url}")
                
                if is_valid_data_file(clean_url):
                    print(f"Valid data file found: {clean_url}")
                    return clean_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting download links from portal: {e}")
        return None

def extract_data_portal_from_official_portal(portal_url: str, city: str) -> Optional[str]:
    """
    Extract links to data portals (CKAN, Socrata, etc.) from an official government portal page.
    """
    try:
        print(f"Extracting data portal links from portal: {portal_url}")
        
        response = requests.get(portal_url, timeout=15)
        response.raise_for_status()
        
        content = response.text
        content_lower = content.lower()
        
        portal_patterns = [
            r'https?://[^"\s]+opendata[^"\s]*',
            r'https?://[^"\s]+open-data[^"\s]*',
            r'https?://data\.[^"\s]+\.gov[^"\s]*',
            r'https?://data\.[^"\s]+\.ca[^"\s]*',
            r'https?://[^"\s]+-data\.gov[^"\s]*',
            
            r'https?://[^"\s]+ckan[^"\s]*',
            r'https?://[^"\s]+/api/3/action/[^"\s]*',
            
            r'https?://[^"\s]+socrata[^"\s]*',
            r'https?://[^"\s]+/resource/[^"\s]*',
        ]
        
        for pattern in portal_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                clean_url = match.strip('"\'')
                
                if not clean_url.startswith('http'):
                    continue
                
                print(f"Found potential data portal: {clean_url}")
                
                api_endpoint = find_311_datasets_in_portal(clean_url, city)
                if api_endpoint:
                    print(f"Found 311 dataset in data portal: {api_endpoint}")
                    return api_endpoint
        
        return None
        
    except Exception as e:
        print(f"Error extracting data portal links from portal: {e}")
        return None

def find_311_datasets_in_portal(portal_url: str, city: str) -> Optional[str]:
    """
    Find 311 datasets in a data portal (CKAN, Socrata, etc.).
    """
    try:
        if "/api/3/action/" in portal_url or "ckan" in portal_url.lower():
            return find_ckan_311_dataset(portal_url, city)
        
        if "socrata" in portal_url.lower() or "/resource/" in portal_url:
            return find_socrata_311_dataset(portal_url, city)
        
        return search_portal_for_311_datasets(portal_url, city)
        
    except Exception as e:
        print(f"Error finding 311 datasets in portal: {e}")
        return None

def find_socrata_311_dataset(portal_url: str, city: str) -> Optional[str]:
    """
    Find 311 datasets in a Socrata portal.
    """
    try:
        dataset_names = [
            "311-service-requests",
            "311-service-requests-customer-initiated",
            "311-requests",
            "service-requests",
            "complaints",
            "incidents",
            "customer-service-requests"
        ]
        
        for dataset_name in dataset_names:
            test_url = f"{portal_url.rstrip('/')}/{dataset_name}.json"
            print(f"Testing Socrata dataset: {test_url}")
            
            if is_valid_api_endpoint(test_url):
                print(f"Found valid Socrata 311 dataset: {test_url}")
                return test_url
        
        return None
        
    except Exception as e:
        print(f"Error finding Socrata 311 dataset: {e}")
        return None

def search_portal_for_311_datasets(portal_url: str, city: str) -> Optional[str]:
    """
    Generic search for 311 datasets in any portal.
    """
    try:
        response = requests.get(portal_url, timeout=15)
        response.raise_for_status()
        
        content = response.text
        content_lower = content.lower()
        
        if "311" in content_lower:
            url_pattern = r'https?://[^"\s]+'
            urls = re.findall(url_pattern, content)
            
            for url in urls:
                if "311" in url.lower() and (url.endswith('.json') or url.endswith('.csv')):
                    print(f"Found 311-related URL: {url}")
                    if is_valid_api_endpoint(url):
                        print(f"Valid 311 dataset found: {url}")
                        return url
        
        return None
        
    except Exception as e:
        print(f"Error searching portal for 311 datasets: {e}")
        return None

def is_valid_data_file(url: str) -> bool:
    """
    Validate if URL points to a valid data file (CSV, JSON, ZIP, etc.).
    """
    try:
        response = requests.head(url, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "").lower()
        content_length = response.headers.get("Content-Length", "0")
        
        try:
            size = int(content_length)
            if size < 100 or size > 100 * 1024 * 1024:
                return False
        except:
            pass
        
        valid_types = [
            "text/csv", "application/csv",
            "application/json", "text/json",
            "application/zip", "application/x-zip-compressed",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "text/plain"
        ]
        
        return any(valid_type in content_type for valid_type in valid_types)
        
    except Exception as e:
        print(f"Error validating data file: {e}")
        return False



def try_known_patterns(city: str, province: str, country: str) -> Optional[str]:
    """Try known API patterns for common municipal platforms."""
    print("Trying known API patterns...")
    
    city_slug = city.lower().replace(" ", "").replace("-", "")
    
    for pattern in KNOWN_PATTERNS["open311"]:
        url = pattern.format(city_slug=city_slug)
        print(f"Testing Open311 pattern: {url}")
        if is_valid_api_endpoint(url):
            print(f"Found valid Open311 endpoint: {url}")
            return url
    
    for pattern in KNOWN_PATTERNS["socrata"]:
        base_url = pattern.format(city_slug=city_slug)
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
    
    for pattern in KNOWN_PATTERNS["ckan"]:
        base_url = pattern.format(city_slug=city_slug)
        print(f"Testing CKAN pattern: {base_url}")
        
        ckan_endpoint = find_ckan_311_dataset(base_url, city)
        if ckan_endpoint:
            print(f"Found valid CKAN 311 dataset: {ckan_endpoint}")
            return ckan_endpoint
    
    city_ckan_patterns = [
        f"https://ckan0.cf.opendata.inter.prod-{city.lower()}.ca",
        f"https://{city.lower()}-opendata.ca",
        f"https://opendata.{city.lower()}.ca",
        f"https://data.{city.lower()}.ca"
    ]
    
    for ckan_url in city_ckan_patterns:
        print(f"Testing city-specific CKAN: {ckan_url}")
        ckan_endpoint = find_ckan_311_dataset(ckan_url, city)
        if ckan_endpoint:
            print(f"Found valid city CKAN 311 dataset: {ckan_endpoint}")
            return ckan_endpoint
    
    return None

def try_domain_restricted_search(city: str, province: str, country: str) -> Optional[str]:
    """Search with domain restrictions to avoid SEO junk."""
    print("Trying domain-restricted search...")
    
    if country.lower() == "usa":
        domain = "*.gov"
    elif country.lower() == "canada":
        domain = "*.ca"
    else:
        domain = "*.gov"
    
    search_queries = [
        f'site:{domain} "{city}" "311" "api" filetype:json',
        f'site:{domain} "{city}" "open311" "endpoint"',
        f'site:{city.lower()}.ca "311" "download" "data"',
        f'site:{city.lower()}.ca "311" "opendata" "resource"',
        f'site:{city.lower()}.ca "311" "service request" "dataset"',
        f'site:{city.lower()}.ca "311" "ckan" "api"',
        f'site:{city.lower()}.ca "311" "datastore" "search"',
        f'site:{city.lower()}.ca "311" "package" "show"',
        f'site:{city.lower()}.ca "311" "resource" "download"',
        f'site:{city.lower()}.ca "311" "zip" "csv" "xlsx"'
    ]
    
    for query in search_queries:
        print(f"Searching: {query}")
        search_results = search_serper(query)
        
        if search_results.get("organic"):
            for result in search_results["organic"][:5]:
                link = result.get("link", "")
                title = result.get("title", "")
                
                print(f"Found result: {title}")
                print(f"Link: {link}")
                
                if looks_like_api_url(link) and is_valid_api_endpoint(link):
                    print(f"Found valid endpoint via search: {link}")
                    return link
                
                api_endpoint = extract_api_from_page(link, city)
                if api_endpoint:
                    print(f"Found API endpoint in page: {api_endpoint}")
                    return api_endpoint
                
                ckan_endpoint = extract_ckan_from_page(link, city)
                if ckan_endpoint:
                    print(f"Found CKAN endpoint: {ckan_endpoint}")
                    return ckan_endpoint
    
    return None

def extract_api_from_page(url: str, city: str) -> Optional[str]:
    """Extract API endpoints from a webpage that might contain them."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        content = response.text.lower()
        
        api_patterns = [
            f"https://data.{city.lower()}.gov/resource/",
            f"https://{city.lower()}-data.gov/resource/",
            f"https://data.{city.lower()}.ca/resource/",
            f"https://{city.lower()}.open311.io/",
            f"https://api.{city.lower()}.gov/",
            f"https://{city.lower()}.gov/api/",
            f"https://{city.lower()}.ca/api/",
            "/api/3/action/",
            "/arcgis/rest/services/",
            ".json",
            "/resource/"
        ]
        
        for pattern in api_patterns:
            if pattern in content:
                start_idx = content.find(pattern)
                if start_idx != -1:
                    end_idx = content.find('"', start_idx)
                    if end_idx == -1:
                        end_idx = content.find("'", start_idx)
                    if end_idx == -1:
                        end_idx = content.find(" ", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\n", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\r", start_idx)
                    
                    if end_idx != -1:
                        extracted_url = content[start_idx:end_idx]
                        
                        extracted_url = extracted_url.strip()
                        
                        if extracted_url.startswith('.') or extracted_url.startswith('/'):
                            continue
                        
                        if not extracted_url.startswith('http'):
                            if extracted_url.startswith('//'):
                                extracted_url = 'https:' + extracted_url
                            elif extracted_url.startswith('/'):
                                base_url = url.split('/')[0] + '//' + url.split('/')[2]
                                extracted_url = base_url + extracted_url
                            else:
                                continue
                        
                        extracted_url = extracted_url.replace(city.lower(), city)
                        
                        if not extracted_url.startswith('http'):
                            continue
                        
                        print(f"Extracted URL: {extracted_url}")
                        
                        if is_valid_api_endpoint(extracted_url):
                            return extracted_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting API from page: {e}")
        return None

def extract_ckan_from_page(url: str, city: str) -> Optional[str]:
    """Extract CKAN API endpoints from a portal page."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        content = response.text.lower()
        
        ckan_patterns = [
            "/api/3/action/",
            "ckan0.cf.opendata",
            "ckanadmin",
            "datastore_search",
            "package_show",
            "resource_show"
        ]
        
        for pattern in ckan_patterns:
            if pattern in content:
                start_idx = content.find(pattern)
                if start_idx != -1:
                    end_idx = content.find('"', start_idx)
                    if end_idx == -1:
                        end_idx = content.find("'", start_idx)
                    if end_idx == -1:
                        end_idx = content.find(" ", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\n", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\r", start_idx)
                    
                    if end_idx != -1:
                        extracted_url = content[start_idx:end_idx].strip()
                        
                        if extracted_url.startswith('/'):
                            base_url = url.split('/')[0] + '//' + url.split('/')[2]
                            extracted_url = base_url + extracted_url
                        elif not extracted_url.startswith('http'):
                            continue
                        
                        print(f"Extracted CKAN URL: {extracted_url}")
                        
                        if test_ckan_endpoint(extracted_url):
                            return extracted_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting CKAN from page: {e}")
        return None

def test_ckan_endpoint(url: str) -> bool:
    """Test if a URL is a valid CKAN API endpoint."""
    try:
        test_url = url.rstrip('/') + '/package_list'
        response = requests.get(test_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return isinstance(data, dict) and data.get("success") is True
    except:
        pass
    return False

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
        
        content_type = response.headers.get("Content-Type", "").lower()
        
        is_valid_content = any([
            "application/json" in content_type,
            "text/json" in content_type,
            "text/csv" in content_type,
            "application/csv" in content_type,
            "text/plain" in content_type,
            "application/geo+json" in content_type,
            "application/vnd.geo+json" in content_type
        ])
        
        if not is_valid_content:
            print(f"Rejected: Not valid content type ({content_type})")
            return False
        
        try:
            data = response.json()
            
            if isinstance(data, dict):
                text_content = str(data).lower()
                if any(archival in text_content for archival in ['1896', 'archive', 'historical', 'manuscript', 'order in council']):
                    print(f"Rejected: Historical/archival data")
                    return False
                
                if any(key in data for key in ["service_requests", "service_definitions", "requests", "services"]):
                    print(f"Valid API endpoint: Open311 format")
                    return True
                elif len(data) > 0:
                    print(f"Valid API endpoint: JSON object with data")
                    return True
            elif isinstance(data, list) and len(data) > 0:
                text_content = str(data).lower()
                if any(archival in text_content for archival in ['1896', 'archive', 'historical', 'manuscript']):
                    print(f"Rejected: Historical/archival data")
                    return False
                
                print(f"Valid API endpoint: JSON array with data")
                return True
            
        except json.JSONDecodeError:
            text_content = response.text[:1000]
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
        search_terms = [
            '311-service-requests-customer-initiated',
            '311 service requests customer initiated',
            '311 service request',
            'service request',
            '311',
            'complaint',
            'incident',
            'customer initiated'
        ]
        
        for term in search_terms:
            search_url = f"{ckan_base_url.rstrip('/')}/api/3/action/package_search?q={term}"
            print(f"Searching CKAN for: {term}")
            
            try:
                response = requests.get(search_url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                if not isinstance(data, dict) or not data.get("success"):
                    continue
                
                results = data["result"]["results"]
                print(f"Found {len(results)} datasets")
                
                for dataset in results:
                    dataset_url = find_best_ckan_resource(dataset, city)
                    if dataset_url:
                        return dataset_url
                        
            except Exception as e:
                print(f"CKAN search failed for {term}: {e}")
                continue
        
        try:
            package_list_url = f"{ckan_base_url.rstrip('/')}/api/3/action/package_list"
            response = requests.get(package_list_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict) and data.get("success") and "result" in data:
                packages = data["result"]
                print(f"Found {len(packages)} total packages")
                
                for package_name in packages:
                    if "311" in package_name.lower():
                        print(f"Found 311 package: {package_name}")
                        
                        package_url = f"{ckan_base_url.rstrip('/')}/api/3/action/package_show?id={package_name}"
                        package_response = requests.get(package_url, timeout=10)
                        if package_response.status_code == 200:
                            package_data = package_response.json()
                            if package_data.get("success") and "result" in package_data:
                                dataset = package_data["result"]
                                dataset_url = find_best_ckan_resource(dataset, city)
                                if dataset_url:
                                    return dataset_url
                                    
        except Exception as e:
            print(f"Package list search failed: {e}")
        
        return None
        
    except Exception as e:
        print(f"CKAN search error: {e}")
        return None

def find_best_ckan_resource(dataset: Dict[str, Any], city: str) -> Optional[str]:
    """Find the best resource (JSON/GeoJSON) from a CKAN dataset."""
    title = dataset.get("title", "").lower()
    name = dataset.get("name", "").lower()
    
    if not any(keyword in title or keyword in name for keyword in ["311", "service request", "complaint", "incident", "customer initiated"]):
        return None
    
    if any(metric in title or metric in name for metric in ["metrics", "performance", "statistics"]):
        print(f"Skipping metrics dataset: {dataset.get('title')}")
        return None
    
    print(f"Found 311 dataset: {dataset.get('title')}")
    
    last_modified = dataset.get("metadata_modified")
    if last_modified:
        try:
            modified_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            if modified_date < datetime.now(modified_date.tzinfo) - timedelta(days=365):
                print(f"Dataset too old: {modified_date}")
                return None
        except:
            pass
    
    resources = dataset.get("resources", [])
    
    resource_preferences = ["JSON", "GEOJSON", "ZIP", "CSV", "XLSX"]
    
    for preference in resource_preferences:
        for resource in resources:
            format_type = resource.get("format", "").upper()
            url = resource.get("url", "")
            
            if format_type == preference and url:
                print(f"Found {format_type} resource: {url}")
                return url
    
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
    
    api_indicators = [".json", ".xml", "/api/", "/v1/", "/v2/", "resource", "rest", "services", "dataset"]
    has_api = any(indicator in url_lower for indicator in api_indicators)
    
    exclude_sites = ["open311.org", "docs", "documentation", "wiki", "help", "blog", "news", "press"]
    is_excluded = any(site in url_lower for site in exclude_sites)
    
    exclude_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".html", ".htm"]
    has_excluded_extension = any(ext in url_lower for ext in exclude_extensions)
    
    return has_api and not is_excluded and not has_excluded_extension



def try_known_patterns(city: str, province: str, country: str) -> Optional[str]:
    """Try known API patterns for common municipal platforms."""
    print("Trying known API patterns...")
    
    city_slug = city.lower().replace(" ", "").replace("-", "")
    
    for pattern in KNOWN_PATTERNS["open311"]:
        url = pattern.format(city_slug=city_slug)
        print(f"Testing Open311 pattern: {url}")
        if is_valid_api_endpoint(url):
            print(f"Found valid Open311 endpoint: {url}")
            return url
    
    for pattern in KNOWN_PATTERNS["socrata"]:
        base_url = pattern.format(city_slug=city_slug)
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
    
    for pattern in KNOWN_PATTERNS["ckan"]:
        base_url = pattern.format(city_slug=city_slug)
        print(f"Testing CKAN pattern: {base_url}")
        
        ckan_endpoint = find_ckan_311_dataset(base_url, city)
        if ckan_endpoint:
            print(f"Found valid CKAN 311 dataset: {ckan_endpoint}")
            return ckan_endpoint
    
    city_ckan_patterns = [
        f"https://ckan0.cf.opendata.inter.prod-{city.lower()}.ca",
        f"https://{city.lower()}-opendata.ca",
        f"https://opendata.{city.lower()}.ca",
        f"https://data.{city.lower()}.ca"
    ]
    
    for ckan_url in city_ckan_patterns:
        print(f"Testing city-specific CKAN: {ckan_url}")
        ckan_endpoint = find_ckan_311_dataset(ckan_url, city)
        if ckan_endpoint:
            print(f"Found valid city CKAN 311 dataset: {ckan_endpoint}")
            return ckan_endpoint
    
    return None

def try_domain_restricted_search(city: str, province: str, country: str) -> Optional[str]:
    """Search with domain restrictions to avoid SEO junk."""
    print("Trying domain-restricted search...")
    
    if country.lower() == "usa":
        domain = "*.gov"
    elif country.lower() == "canada":
        domain = "*.ca"
    else:
        domain = "*.gov"
    
    search_queries = [
        f'site:{domain} "{city}" "311" "api" filetype:json',
        f'site:{domain} "{city}" "open311" "endpoint"',
        f'site:{city.lower()}.ca "311" "download" "data"',
        f'site:{city.lower()}.ca "311" "opendata" "resource"',
        f'site:{city.lower()}.ca "311" "service request" "dataset"',
        f'site:{city.lower()}.ca "311" "ckan" "api"',
        f'site:{city.lower()}.ca "311" "datastore" "search"',
        f'site:{city.lower()}.ca "311" "package" "show"',
        f'site:{city.lower()}.ca "311" "resource" "download"',
        f'site:{city.lower()}.ca "311" "zip" "csv" "xlsx"'
    ]
    
    for query in search_queries:
        print(f"Searching: {query}")
        search_results = search_serper(query)
        
        if search_results.get("organic"):
            for result in search_results["organic"][:5]:
                link = result.get("link", "")
                title = result.get("title", "")
                
                print(f"Found result: {title}")
                print(f"Link: {link}")
                
                if looks_like_api_url(link) and is_valid_api_endpoint(link):
                    print(f"Found valid endpoint via search: {link}")
                    return link
                
                api_endpoint = extract_api_from_page(link, city)
                if api_endpoint:
                    print(f"Found API endpoint in page: {api_endpoint}")
                    return api_endpoint
                
                ckan_endpoint = extract_ckan_from_page(link, city)
                if ckan_endpoint:
                    print(f"Found CKAN endpoint: {ckan_endpoint}")
                    return ckan_endpoint
    
    return None



def extract_api_from_page(url: str, city: str) -> Optional[str]:
    """Extract API endpoints from a webpage that might contain them."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        content = response.text.lower()
        
        api_patterns = [
            f"https://data.{city.lower()}.gov/resource/",
            f"https://{city.lower()}-data.gov/resource/",
            f"https://data.{city.lower()}.ca/resource/",
            f"https://{city.lower()}.open311.io/",
            f"https://api.{city.lower()}.gov/",
            f"https://{city.lower()}.gov/api/",
            f"https://{city.lower()}.ca/api/",
            "/api/3/action/",
            "/arcgis/rest/services/",
            ".json",
            "/resource/"
        ]
        
        for pattern in api_patterns:
            if pattern in content:
                start_idx = content.find(pattern)
                if start_idx != -1:
                    end_idx = content.find('"', start_idx)
                    if end_idx == -1:
                        end_idx = content.find("'", start_idx)
                    if end_idx == -1:
                        end_idx = content.find(" ", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\n", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\r", start_idx)
                    
                    if end_idx != -1:
                        extracted_url = content[start_idx:end_idx]
                        
                        extracted_url = extracted_url.strip()
                        
                        if extracted_url.startswith('.') or extracted_url.startswith('/'):
                            continue
                        
                        if not extracted_url.startswith('http'):
                            if extracted_url.startswith('//'):
                                extracted_url = 'https:' + extracted_url
                            elif extracted_url.startswith('/'):
                                base_url = url.split('/')[0] + '//' + url.split('/')[2]
                                extracted_url = base_url + extracted_url
                            else:
                                continue
                        
                        extracted_url = extracted_url.replace(city.lower(), city)
                        
                        if not extracted_url.startswith('http'):
                            continue
                        
                        print(f"Extracted URL: {extracted_url}")
                        
                        if is_valid_api_endpoint(extracted_url):
                            return extracted_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting API from page: {e}")
        return None

def extract_ckan_from_page(url: str, city: str) -> Optional[str]:
    """Extract CKAN API endpoints from a portal page."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        content = response.text.lower()
        
        ckan_patterns = [
            "/api/3/action/",
            "ckan0.cf.opendata",
            "ckanadmin",
            "datastore_search",
            "package_show",
            "resource_show"
        ]
        
        for pattern in ckan_patterns:
            if pattern in content:
                start_idx = content.find(pattern)
                if start_idx != -1:
                    end_idx = content.find('"', start_idx)
                    if end_idx == -1:
                        end_idx = content.find("'", start_idx)
                    if end_idx == -1:
                        end_idx = content.find(" ", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\n", start_idx)
                    if end_idx == -1:
                        end_idx = content.find("\r", start_idx)
                    
                    if end_idx != -1:
                        extracted_url = content[start_idx:end_idx].strip()
                        
                        if extracted_url.startswith('/'):
                            base_url = url.split('/')[0] + '//' + url.split('/')[2]
                            extracted_url = base_url + extracted_url
                        elif not extracted_url.startswith('http'):
                            continue
                        
                        print(f"Extracted CKAN URL: {extracted_url}")
                        
                        if test_ckan_endpoint(extracted_url):
                            return extracted_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting CKAN from page: {e}")
        return None

def test_ckan_endpoint(url: str) -> bool:
    """Test if a URL is a valid CKAN API endpoint."""
    try:
        test_url = url.rstrip('/') + '/package_list'
        response = requests.get(test_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return isinstance(data, dict) and data.get("success") is True
    except:
        pass
    return False

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
        
        content_type = response.headers.get("Content-Type", "").lower()
        
        is_valid_content = any([
            "application/json" in content_type,
            "text/json" in content_type,
            "text/csv" in content_type,
            "application/csv" in content_type,
            "text/plain" in content_type,
            "application/geo+json" in content_type,
            "application/vnd.geo+json" in content_type
        ])
        
        if not is_valid_content:
            print(f"Rejected: Not valid content type ({content_type})")
            return False
        
        try:
            data = response.json()
            
            if isinstance(data, dict):
                text_content = str(data).lower()
                if any(archival in text_content for archival in ['1896', 'archive', 'historical', 'manuscript', 'order in council']):
                    print(f"Rejected: Historical/archival data")
                    return False
                
                if any(key in data for key in ["service_requests", "service_definitions", "requests", "services"]):
                    print(f"Valid API endpoint: Open311 format")
                    return True
                elif len(data) > 0:
                    print(f"Valid API endpoint: JSON object with data")
                    return True
            elif isinstance(data, list) and len(data) > 0:
                text_content = str(data).lower()
                if any(archival in text_content for archival in ['1896', 'archive', 'historical', 'manuscript']):
                    print(f"Rejected: Historical/archival data")
                    return False
                
                print(f"Valid API endpoint: JSON array with data")
                return True
            
        except json.JSONDecodeError:
            text_content = response.text[:1000]
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
        search_terms = [
            '311-service-requests-customer-initiated',
            '311 service requests customer initiated',
            '311 service request',
            'service request',
            '311',
            'complaint',
            'incident',
            'customer initiated'
        ]
        
        for term in search_terms:
            search_url = f"{ckan_base_url.rstrip('/')}/api/3/action/package_search?q={term}"
            print(f"Searching CKAN for: {term}")
            
            try:
                response = requests.get(search_url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                if not isinstance(data, dict) or not data.get("success"):
                    continue
                
                results = data["result"]["results"]
                print(f"Found {len(results)} datasets")
                
                for dataset in results:
                    dataset_url = find_best_ckan_resource(dataset, city)
                    if dataset_url:
                        return dataset_url
                        
            except Exception as e:
                print(f"CKAN search failed for {term}: {e}")
                continue
        
        try:
            package_list_url = f"{ckan_base_url.rstrip('/')}/api/3/action/package_list"
            response = requests.get(package_list_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict) and data.get("success") and "result" in data:
                packages = data["result"]
                print(f"Found {len(packages)} total packages")
                
                for package_name in packages:
                    if "311" in package_name.lower():
                        print(f"Found 311 package: {package_name}")
                        
                        package_url = f"{ckan_base_url.rstrip('/')}/api/3/action/package_show?id={package_name}"
                        package_response = requests.get(package_url, timeout=10)
                        if package_response.status_code == 200:
                            package_data = package_response.json()
                            if package_data.get("success") and "result" in package_data:
                                dataset = package_data["result"]
                                dataset_url = find_best_ckan_resource(dataset, city)
                                if dataset_url:
                                    return dataset_url
                                    
        except Exception as e:
            print(f"Package list search failed: {e}")
        
        return None
        
    except Exception as e:
        print(f"CKAN search error: {e}")
        return None

def find_best_ckan_resource(dataset: Dict[str, Any], city: str) -> Optional[str]:
    """Find the best resource (JSON/GeoJSON) from a CKAN dataset."""
    title = dataset.get("title", "").lower()
    name = dataset.get("name", "").lower()
    
    if not any(keyword in title or keyword in name for keyword in ["311", "service request", "complaint", "incident", "customer initiated"]):
        return None
    
    if any(metric in title or metric in name for metric in ["metrics", "performance", "statistics"]):
        print(f"Skipping metrics dataset: {dataset.get('title')}")
        return None
    
    print(f"Found 311 dataset: {dataset.get('title')}")
    
    last_modified = dataset.get("metadata_modified")
    if last_modified:
        try:
            modified_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            if modified_date < datetime.now(modified_date.tzinfo) - timedelta(days=365):
                print(f"Dataset too old: {modified_date}")
                return None
        except:
            pass
    
    resources = dataset.get("resources", [])
    
    resource_preferences = ["JSON", "GEOJSON", "ZIP", "CSV", "XLSX"]
    
    for preference in resource_preferences:
        for resource in resources:
            format_type = resource.get("format", "").upper()
            url = resource.get("url", "")
            
            if format_type == preference and url:
                print(f"Found {format_type} resource: {url}")
                return url
    
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
    
    api_indicators = [".json", ".xml", "/api/", "/v1/", "/v2/", "resource", "rest", "services", "dataset"]
    has_api = any(indicator in url_lower for indicator in api_indicators)
    
    exclude_sites = ["open311.org", "docs", "documentation", "wiki", "help", "blog", "news", "press"]
    is_excluded = any(site in url_lower for site in exclude_sites)
    
    exclude_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".html", ".htm"]
    has_excluded_extension = any(ext in url_lower for ext in exclude_extensions)
    
    return has_api and not is_excluded and not has_excluded_extension
