"""
311 API Discovery

Handles discovery of 311 API endpoints for cities.
"""

from agents.municipal_api_discovery import discover_municipal_api_endpoint

def discover_311_endpoint(city: str, province: str, country: str):
    """Discover 311 API endpoint for a city."""
    print(f"Discovering 311 API for {city}, {province}, {country}")
    return discover_municipal_api_endpoint(city, province, country)
