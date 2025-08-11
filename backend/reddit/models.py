"""
Pydantic models for Reddit POI extraction
"""
from pydantic import BaseModel, Field
from typing import List

class POI(BaseModel):
    name: str = Field(description="Name of the point of interest")
    description: str = Field(description="Brief description of what makes this place special")
    category: str = Field(description="Category like 'museum', 'park', 'restaurant', 'attraction'")
    reddit_context: str = Field(description="Original Reddit content mentioning this place for authentic summary generation")

class POIList(BaseModel):
    city: str = Field(description="The city being analyzed")
    pois: List[POI] = Field(description="List of points of interest found")

class POIOutput(BaseModel):
    name: str = Field(description="Name of the point of interest")
    lat: float = Field(description="Latitude coordinate")
    lng: float = Field(description="Longitude coordinate")
    summary: str = Field(description="Summary of what's happening at this location")
    type: str = Field(description="Type of POI (reddit, event, restaurant, etc.)")
    radius: int = Field(description="Radius in kilometers")

class Coordinates(BaseModel):
    lat: float = Field(description="Latitude coordinate")
    lng: float = Field(description="Longitude coordinate")

class EnhancedPOI(BaseModel):
    name: str = Field(description="Name of the point of interest")
    description: str = Field(description="Brief category description")
    category: str = Field(description="Type of place")
    reddit_context: str = Field(description="Original Reddit content")
    user_quote: str = Field(description="A short, authentic quote from Reddit users about this place (max 100 words)")

class EnhancedPOIList(BaseModel):
    city: str = Field(description="The city being analyzed")
    pois: List[EnhancedPOI] = Field(description="List of enhanced POIs with user quotes")
