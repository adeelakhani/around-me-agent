"""
311 API Integration Module

This module provides integration with municipal 311 APIs to fetch
city services, infrastructure data, events, and local government information.
"""

from .service import get_311_pois

__all__ = ['get_311_pois']
