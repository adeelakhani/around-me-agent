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
from .data_portal_discovery import DataPortalDiscovery
from datetime import datetime, timedelta

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
        "https://{city_slug}-opendata.ca",
        "https://opendata.{city_slug}.gov",
        "https://data.{city_slug}.gov"
    ]
}

# Known working 311 APIs for major cities
KNOWN_311_APIS = {
    # Canada
    ("toronto", "ontario", "canada"): [
        "https://secure.toronto.ca/open311/v2/services.json",
        "https://open.toronto.ca/dataset/311-service-requests/",
        "https://open.toronto.ca/dataset/311-service-requests/resource/",
        "https://www.toronto.ca/city-government/data-research-maps/open-data/",
        "https://open.toronto.ca/wp-json/wp/v2/pages/1322",
        "https://open.toronto.ca/dataset/311-service-requests/resource/311-service-requests.json"
    ],
    ("vancouver", "british columbia", "canada"): [
        "https://opendata.vancouver.ca/api/v1/311-requests"
    ],
    ("montreal", "quebec", "canada"): [
        "https://donnees.montreal.ca/api/311-requests"
    ],
    ("calgary", "alberta", "canada"): [
        "https://data.calgary.ca/resource/311-requests.json"
    ],
    ("edmonton", "alberta", "canada"): [
        "https://data.edmonton.ca/resource/311-requests.json"
    ],
    ("ottawa", "ontario", "canada"): [
        "https://data.ottawa.ca/resource/311-requests.json"
    ],
    
    # USA
    ("new york", "new york", "usa"): [
        "https://data.cityofnewyork.us/resource/v6wi-cqs5.json"
    ],
    ("san francisco", "california", "usa"): [
        "https://open311.sfgov.org/dev/v2/services.json"
    ],
    ("chicago", "illinois", "usa"): [
        "https://data.cityofchicago.org/resource/v6wi-cqs5.json"
    ],
    ("los angeles", "california", "usa"): [
        "https://data.lacity.org/resource/311-requests.json"
    ],
    ("philadelphia", "pennsylvania", "usa"): [
        "https://data.phila.gov/resource/311-requests.json"
    ],
    ("boston", "massachusetts", "usa"): [
        "https://data.boston.gov/resource/311-requests.json"
    ],
    ("seattle", "washington", "usa"): [
        "https://data.seattle.gov/resource/311-requests.json"
    ],
    ("denver", "colorado", "usa"): [
        "https://data.denvergov.org/resource/311-requests.json"
    ],
    ("austin", "texas", "usa"): [
        "https://data.austintexas.gov/resource/311-requests.json"
    ],
    ("portland", "oregon", "usa"): [
        "https://data.portlandoregon.gov/resource/311-requests.json"
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
    
    # Step 1: Try comprehensive data portal discovery
    portal_discovery = DataPortalDiscovery()
    endpoint = portal_discovery.discover_311_data(city, province, country)
    if endpoint:
        return endpoint
    
    # Step 2: Try known patterns as fallback
    endpoint = try_known_patterns(city, province, country)
    if endpoint:
        return endpoint
    
    # Step 3: Try domain-restricted search
    endpoint = try_domain_restricted_search(city, province, country)
    if endpoint:
        return endpoint
    
    # Step 4: Try simple search as last resort
    endpoint = try_broad_search_with_validation(city, province, country)
    if endpoint:
        return endpoint
    
    print("Municipal API Discovery Agent: No valid endpoint found")
    return None

def create_mock_311_endpoint(city: str, province: str, country: str) -> str:
    """Create a mock 311 API endpoint for cities without real APIs."""
    # This would typically return a URL to a mock API service
    # For now, we'll return a special identifier that the 311 service can handle
    mock_endpoint = f"mock://{city.lower()}-{province.lower()}-{country.lower()}-311"
    print(f"Created mock 311 endpoint: {mock_endpoint}")
    return mock_endpoint

def extract_toronto_api_endpoints(portal_url: str) -> Optional[str]:
    """Extract API endpoints from Toronto's open data portal."""
    try:
        print(f"Extracting API endpoints from Toronto portal: {portal_url}")
        
        response = requests.get(portal_url, timeout=10)
        response.raise_for_status()
        
        content = response.text.lower()
        
        # Look for Toronto-specific API patterns
        toronto_patterns = [
            "https://open.toronto.ca/dataset/",
            "https://www.toronto.ca/city-government/data-research-maps/open-data/",
            "/api/3/action/",
            "/resource/",
            ".json"
        ]
        
        for pattern in toronto_patterns:
            if pattern in content:
                # Try to extract the full URL
                start_idx = content.find(pattern)
                if start_idx != -1:
                    # Find the end of the URL
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
                        
                        # Skip if it's just a file extension
                        if extracted_url.startswith('.') or extracted_url.startswith('/'):
                            continue
                        
                        # Add scheme if missing
                        if not extracted_url.startswith('http'):
                            if extracted_url.startswith('//'):
                                extracted_url = 'https:' + extracted_url
                            elif extracted_url.startswith('/'):
                                # Try to construct full URL from base
                                base_url = portal_url.split('/')[0] + '//' + portal_url.split('/')[2]
                                extracted_url = base_url + extracted_url
                            else:
                                continue
                        
                        # Validate the URL format
                        if not extracted_url.startswith('http'):
                            continue
                        
                        print(f"Extracted Toronto URL: {extracted_url}")
                        
                        if is_valid_api_endpoint(extracted_url):
                            return extracted_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting Toronto API endpoints: {e}")
        return None

def check_known_apis(city: str, province: str, country: str) -> Optional[str]:
    """Check if we have a known working API for this city."""
    city_key = (city.lower(), province.lower(), country.lower())
    
    if city_key in KNOWN_311_APIS:
        endpoints = KNOWN_311_APIS[city_key]
        print(f"Found known APIs for {city}: {endpoints}")
        
        # Test each endpoint to see if any are working
        for endpoint in endpoints:
            print(f"Testing known API: {endpoint}")
            
            # Test if the endpoint is still working
            if is_valid_api_endpoint(endpoint):
                print(f"Known API endpoint is working: {endpoint}")
                return endpoint
            else:
                print(f"Known API endpoint is not working: {endpoint}")
                
                # For Toronto, try to extract from the portal page
                if city.lower() == "toronto" and "open.toronto.ca" in endpoint:
                    extracted_endpoint = extract_toronto_api_endpoints(endpoint)
                    if extracted_endpoint:
                        print(f"Found working endpoint from Toronto portal: {extracted_endpoint}")
                        return extracted_endpoint
    
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
    
    # Try city-specific CKAN patterns
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
    
    # Get country-specific domain
    if country.lower() == "usa":
        domain = "*.gov"
    elif country.lower() == "canada":
        domain = "*.ca"
    else:
        domain = "*.gov"
    
    # More specific search queries that are more likely to find actual APIs
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
                
                # More flexible validation - check if it looks like an API endpoint
                if looks_like_api_url(link) and is_valid_api_endpoint(link):
                    print(f"Found valid endpoint via search: {link}")
                    return link
                
                # Also check if the page contains API endpoints
                api_endpoint = extract_api_from_page(link, city)
                if api_endpoint:
                    print(f"Found API endpoint in page: {api_endpoint}")
                    return api_endpoint
                
                # Check if this is a CKAN portal page
                ckan_endpoint = extract_ckan_from_page(link, city)
                if ckan_endpoint:
                    print(f"Found CKAN endpoint: {ckan_endpoint}")
                    return ckan_endpoint
    
    return None

def try_broad_search_with_validation(city: str, province: str, country: str) -> Optional[str]:
    """Simple search for 311 data."""
    print("Trying simple 311 search...")
    
    # More targeted search queries
    search_queries = [
        f'"{city}" "{province}" "311" "api"',
        f'"{city}" "311" "open data"',
        f'"{city}" "311" "service request" "json"',
        f'"{city}" "311" "municipal" "data"',
        f'"{city}" "311" "endpoint"',
        f'"{city}" "311" "dataset"',
        f'"{city}" "311" "resource"',
        f'"{city}" "311" "download"',
        f'"{city}" "311" "rest"',
        f'"{city}" "311" "geojson"'
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
                
                # Check if it's actually an API endpoint
                if looks_like_api_url(link) and is_valid_api_endpoint(link):
                    print(f"Found valid endpoint: {link}")
                    return link
                
                # Check if the page contains API endpoints
                api_endpoint = extract_api_from_page(link, city)
                if api_endpoint:
                    print(f"Found API endpoint in page: {api_endpoint}")
                    return api_endpoint
    
    return None

def extract_api_from_page(url: str, city: str) -> Optional[str]:
    """Extract API endpoints from a webpage that might contain them."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        content = response.text.lower()
        
        # Look for common API patterns in the page content
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
                # Try to extract the full URL
                start_idx = content.find(pattern)
                if start_idx != -1:
                    # Find the end of the URL
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
                        
                        # Clean up the URL
                        extracted_url = extracted_url.strip()
                        
                        # Skip if it's just a file extension
                        if extracted_url.startswith('.') or extracted_url.startswith('/'):
                            continue
                        
                        # Add scheme if missing
                        if not extracted_url.startswith('http'):
                            if extracted_url.startswith('//'):
                                extracted_url = 'https:' + extracted_url
                            elif extracted_url.startswith('/'):
                                # Try to construct full URL from base
                                base_url = url.split('/')[0] + '//' + url.split('/')[2]
                                extracted_url = base_url + extracted_url
                            else:
                                continue
                        
                        # Convert back to proper case for city name
                        extracted_url = extracted_url.replace(city.lower(), city)
                        
                        # Validate the URL format
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
        
        # Look for CKAN API patterns
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
                # Try to extract the full URL
                start_idx = content.find(pattern)
                if start_idx != -1:
                    # Find the end of the URL
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
                        
                        # Skip if it's just a path
                        if extracted_url.startswith('/'):
                            # Try to construct full URL from base
                            base_url = url.split('/')[0] + '//' + url.split('/')[2]
                            extracted_url = base_url + extracted_url
                        elif not extracted_url.startswith('http'):
                            continue
                        
                        print(f"Extracted CKAN URL: {extracted_url}")
                        
                        # Test if it's a valid CKAN endpoint
                        if test_ckan_endpoint(extracted_url):
                            return extracted_url
        
        return None
        
    except Exception as e:
        print(f"Error extracting CKAN from page: {e}")
        return None

def test_ckan_endpoint(url: str) -> bool:
    """Test if a URL is a valid CKAN API endpoint."""
    try:
        # Test with a simple CKAN API call
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
        
        # Check content type
        content_type = response.headers.get("Content-Type", "").lower()
        
        # Accept JSON, CSV, and some text formats
        is_valid_content = any([
            "application/json" in content_type,
            "text/json" in content_type,
            "text/csv" in content_type,
            "application/csv" in content_type,
            "text/plain" in content_type,  # Some datasets are served as plain text
            "application/geo+json" in content_type,  # GeoJSON
            "application/vnd.geo+json" in content_type  # Alternative GeoJSON
        ])
        
        if not is_valid_content:
            print(f"Rejected: Not valid content type ({content_type})")
            return False
        
        # Try to parse as JSON first
        try:
            data = response.json()
            
            # Reject historical/archival data
            if isinstance(data, dict):
                # Check for archival indicators
                text_content = str(data).lower()
                if any(archival in text_content for archival in ['1896', 'archive', 'historical', 'manuscript', 'order in council']):
                    print(f"Rejected: Historical/archival data")
                    return False
                
                # Open311 format
                if any(key in data for key in ["service_requests", "service_definitions", "requests", "services"]):
                    print(f"Valid API endpoint: Open311 format")
                    return True
                # General municipal data
                elif len(data) > 0:
                    print(f"Valid API endpoint: JSON object with data")
                    return True
            elif isinstance(data, list) and len(data) > 0:
                # Check for archival indicators in list data
                text_content = str(data).lower()
                if any(archival in text_content for archival in ['1896', 'archive', 'historical', 'manuscript']):
                    print(f"Rejected: Historical/archival data")
                    return False
                
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
        # Search for 311-related datasets - prioritize actual service requests
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
        
        # If no 311 datasets found, try to get the package list and search for 311
        try:
            package_list_url = f"{ckan_base_url.rstrip('/')}/api/3/action/package_list"
            response = requests.get(package_list_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict) and data.get("success") and "result" in data:
                packages = data["result"]
                print(f"Found {len(packages)} total packages")
                
                # Look for 311-related packages
                for package_name in packages:
                    if "311" in package_name.lower():
                        print(f"Found 311 package: {package_name}")
                        
                        # Get package details
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
    
    # Check if this looks like 311 data - prioritize actual service requests over metrics
    if not any(keyword in title or keyword in name for keyword in ["311", "service request", "complaint", "incident", "customer initiated"]):
        return None
    
    # Skip metrics datasets in favor of actual service request data
    if any(metric in title or metric in name for metric in ["metrics", "performance", "statistics"]):
        print(f"Skipping metrics dataset: {dataset.get('title')}")
        return None
    
    print(f"Found 311 dataset: {dataset.get('title')}")
    
    # Check last modified date
    last_modified = dataset.get("metadata_modified")
    if last_modified:
        try:
            modified_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            if modified_date < datetime.now(modified_date.tzinfo) - timedelta(days=365):
                print(f"Dataset too old: {modified_date}")
                return None
        except:
            pass
    
    # Look for JSON/GeoJSON resources first, then ZIP/CSV
    resources = dataset.get("resources", [])
    
    # Sort resources by preference: JSON > GEOJSON > ZIP > CSV > XLSX
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
    
    # Must have API indicators
    api_indicators = [".json", ".xml", "/api/", "/v1/", "/v2/", "resource", "rest", "services", "dataset"]
    has_api = any(indicator in url_lower for indicator in api_indicators)
    
    # Exclude obvious non-API sites
    exclude_sites = ["open311.org", "docs", "documentation", "wiki", "help", "blog", "news", "press"]
    is_excluded = any(site in url_lower for site in exclude_sites)
    
    # Also exclude common non-API file types
    exclude_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".html", ".htm"]
    has_excluded_extension = any(ext in url_lower for ext in exclude_extensions)
    
    return has_api and not is_excluded and not has_excluded_extension
