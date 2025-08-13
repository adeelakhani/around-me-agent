"""
Dynamic Data Portal Discovery Agent

Automatically detects and queries any city's open data portal technology:
- CKAN portals
- Socrata portals  
- ArcGIS REST services
- Other open data platforms

Searches for 311/service request datasets across all platforms.
"""

import requests
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from reddit.geocoding import search_serper

class DataPortalDiscovery:
    """Dynamic discovery of municipal data portals and 311 datasets."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AroundMeAgent/1.0 (Municipal Data Discovery)'
        })
    
    def discover_311_data(self, city: str, province: str, country: str) -> Optional[str]:
        """
        Main discovery method - tries all portal types for a city.
        
        Args:
            city: City name
            province: Province/state name
            country: Country name
            
        Returns:
            URL to 311 dataset if found, None otherwise
        """
        print(f"Data Portal Discovery: Searching for {city}, {province}, {country}")
        
        portal_info = self.find_open_data_portal(city, province, country)
        if not portal_info:
            print("No open data portal found")
            return None
        
        portal_type = portal_info['type']
        portal_url = portal_info['url']
        
        print(f"Found {portal_type} portal: {portal_url}")
        
        if portal_type == 'ckan':
            return self.search_ckan_portal(portal_url, city)
        elif portal_type == 'socrata':
            return self.search_socrata_portal(portal_url, city)
        elif portal_type == 'arcgis':
            return self.search_arcgis_portal(portal_url, city)
        else:
            print(f"Unknown portal type: {portal_type}")
            return None
    
    def find_open_data_portal(self, city: str, province: str, country: str) -> Optional[Dict[str, str]]:
        """Find the city's open data portal using search."""
        print("Searching for open data portal...")
        
        search_queries = [
            f'"{city}" "{province}" "open data" site:*.gov',
            f'"{city}" "{province}" "open data" site:*.ca',
            f'"{city}" "open data portal"',
            f'"{city}" "data portal"',
            f'"{city}" "opendata"',
            f'"{city}" "311" "open data"',
            f'"{city}" "service request" "data"',
            f'"{city}" "municipal" "data" "portal"',
            f'"{city}" "city" "data" "api"',
            f'"{city}" "government" "data" "download"'
        ]
        
        for i, query in enumerate(search_queries):
            if i >= 5:
                print("Reached search limit, stopping to prevent infinite loop")
                break
                
            print(f"Searching: {query}")
            search_results = search_serper(query)
            
            if search_results.get("organic"):
                for j, result in enumerate(search_results["organic"][:2]):
                    if j >= 2:
                        break
                    link = result.get("link", "")
                    title = result.get("title", "")
                    
                    print(f"Found result: {title}")
                    print(f"Link: {link}")
                    
                    portal_type = self.detect_portal_type(link, title)
                    if portal_type:
                        return {
                            'type': portal_type,
                            'url': link,
                            'title': title
                        }
                    
                    api_endpoint = self.extract_api_from_portal_page(link, city)
                    if api_endpoint:
                        return {
                            'type': 'extracted',
                            'url': api_endpoint,
                            'title': f"Extracted from {title}"
                        }
        
        return None
    
    def extract_api_from_portal_page(self, url: str, city: str) -> Optional[str]:
        """Extract API endpoints from a portal page."""
        try:
            response = self.session.get(url, timeout=10)
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
                        
                        if end_idx != -1:
                            extracted_url = content[start_idx:end_idx]
                            extracted_url = extracted_url.replace(city.lower(), city)
                            
                            if self.test_api_endpoint(extracted_url):
                                return extracted_url
            
            return None
            
        except Exception as e:
            print(f"Error extracting API from portal page: {e}")
            return None
    
    def test_api_endpoint(self, url: str) -> bool:
        """Test if a URL is a valid API endpoint."""
        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "").lower()
                return any([
                    "application/json" in content_type,
                    "text/json" in content_type,
                    "text/csv" in content_type,
                    "application/csv" in content_type,
                    "application/geo+json" in content_type
                ])
        except:
            pass
        return False
    
    def detect_portal_type(self, url: str, title: str) -> Optional[str]:
        """Detect what type of data portal this is."""
        url_lower = url.lower()
        title_lower = title.lower()
        
        if any(skip in url_lower for skip in ['pubmed', 'ncbi', 'library', 'archive', 'bac-lac']):
            return None
        
        if any(indicator in url_lower for indicator in ['/api/3/action', 'ckan', 'opendata']):
            return 'ckan'
        
        if any(indicator in url_lower for indicator in ['socrata', 'data.city', 'data.gov', '/resource/']):
            return 'socrata'
        
        if any(indicator in url_lower for indicator in ['arcgis', 'rest/services', 'gis']):
            return 'arcgis'
        
        if any(indicator in title_lower for indicator in ['open data', 'data portal', 'opendata']):
            if self.test_ckan_endpoint(url):
                return 'ckan'
            elif self.test_socrata_endpoint(url):
                return 'socrata'
            elif self.test_arcgis_endpoint(url):
                return 'arcgis'
        
        return None
    
    def test_ckan_endpoint(self, base_url: str) -> bool:
        """Test if URL is a CKAN portal."""
        try:
            test_url = f"{base_url.rstrip('/')}/api/3/action/package_list"
            response = self.session.get(test_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return isinstance(data, dict) and data.get("success") is True
        except:
            pass
        return False
    
    def test_socrata_endpoint(self, base_url: str) -> bool:
        """Test if URL is a Socrata portal."""
        try:
            test_url = f"{base_url.rstrip('/')}/api/views.json"
            response = self.session.get(test_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return isinstance(data, list)
        except:
            pass
        return False
    
    def test_arcgis_endpoint(self, base_url: str) -> bool:
        """Test if URL is an ArcGIS portal."""
        try:
            test_url = f"{base_url.rstrip('/')}/arcgis/rest/services"
            response = self.session.get(test_url, timeout=5)
            return response.status_code == 200
        except:
            pass
        return False
    
    def search_ckan_portal(self, portal_url: str, city: str) -> Optional[str]:
        """Search for 311 datasets in CKAN portal."""
        print(f"Searching CKAN portal: {portal_url}")
        
        try:
            search_terms = ['311', 'service request', 'complaint', 'incident']
            
            for term in search_terms:
                search_url = f"{portal_url.rstrip('/')}/api/3/action/package_search?q={term}"
                print(f"Searching CKAN for: {term}")
                
                try:
                    response = self.session.get(search_url, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    if not isinstance(data, dict) or not data.get("success"):
                        continue
                    
                    results = data["result"]["results"]
                    print(f"Found {len(results)} datasets")
                except Exception as e:
                    print(f"CKAN search failed for {term}: {e}")
                    continue
                
                for dataset in results:
                    dataset_url = self.find_best_ckan_resource(dataset, city)
                    if dataset_url:
                        return dataset_url
            
            return None
            
        except Exception as e:
            print(f"CKAN search error: {e}")
            return None
    
    def find_best_ckan_resource(self, dataset: Dict[str, Any], city: str) -> Optional[str]:
        """Find the best resource (JSON/GeoJSON) from a CKAN dataset."""
        title = dataset.get("title", "").lower()
        
        if not any(keyword in title for keyword in ["311", "service request", "complaint", "incident"]):
            return None
        
        print(f"Found 311 dataset: {dataset.get('title')}")
        
        last_modified = dataset.get("metadata_modified")
        if last_modified:
            try:
                modified_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                if modified_date < datetime.now(modified_date.tzinfo) - timedelta(days=90):
                    print(f"Dataset too old: {modified_date}")
                    return None
            except:
                pass
        
        resources = dataset.get("resources", [])
        for resource in resources:
            format_type = resource.get("format", "").upper()
            url = resource.get("url", "")
            
            if format_type in ["JSON", "GEOJSON"] and url:
                print(f"Found {format_type} resource: {url}")
                return url
        
        return None
    
    def search_socrata_portal(self, portal_url: str, city: str) -> Optional[str]:
        """Search for 311 datasets in Socrata portal."""
        print(f"Searching Socrata portal: {portal_url}")
        
        try:
            datasets_url = f"{portal_url.rstrip('/')}/api/views.json"
            response = self.session.get(datasets_url, timeout=10)
            response.raise_for_status()
            
            datasets = response.json()
            print(f"Found {len(datasets)} datasets")
            
            for dataset in datasets:
                name = dataset.get("name", "").lower()
                description = dataset.get("description", "").lower()
                
                if any(keyword in name or keyword in description for keyword in ["311", "service request", "complaint"]):
                    dataset_id = dataset.get("id")
                    if dataset_id:
                        resource_url = f"{portal_url.rstrip('/')}/resource/{dataset_id}.json"
                        print(f"Found 311 dataset: {dataset.get('name')}")
                        print(f"Resource URL: {resource_url}")
                        return resource_url
            
            return None
            
        except Exception as e:
            print(f"Socrata search error: {e}")
            return None
    
    def search_arcgis_portal(self, portal_url: str, city: str) -> Optional[str]:
        """Search for 311 datasets in ArcGIS portal."""
        print(f"Searching ArcGIS portal: {portal_url}")
        
        try:
            services_url = f"{portal_url.rstrip('/')}/arcgis/rest/services"
            response = self.session.get(services_url, timeout=10)
            response.raise_for_status()
            
            print("ArcGIS discovery not fully implemented")
            return None
            
        except Exception as e:
            print(f"ArcGIS search error: {e}")
            return None
