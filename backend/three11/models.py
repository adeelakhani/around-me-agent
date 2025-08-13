"""
311 Data Models

Defines data structures and types for 311 service requests.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ServiceRequest:
    """Represents a 311 service request."""
    service_type: str
    latitude: float
    longitude: float
    status: str
    description: Optional[str] = None
    created_date: Optional[datetime] = None
    ward: Optional[str] = None
    postal_code: Optional[str] = None
    
    def to_poi(self, city: str) -> Dict[str, Any]:
        """Convert to POI format for the main app."""
        return {
            "name": f"{city} {self.service_type}",
            "lat": self.latitude,
            "lng": self.longitude,
            "type": "311_service",
            "summary": self.description or f"{self.service_type} in {city}",
            "source": "311_api",
            "status": self.status,
            "ward": self.ward,
            "postal_code": self.postal_code
        }

@dataclass
class APIConfig:
    """Configuration for a 311 API endpoint."""
    url: str
    format: str
    city: str
    province: str
    country: str
    
    def is_valid(self) -> bool:
        """Check if this API config is valid."""
        return bool(self.url and self.format and self.city)
