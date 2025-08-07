'use client';
import { useEffect, useState, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

interface Location {
  lat: number;
  lng: number;
  name: string;
  summary: string;
  type: string;
  radius: number;
}

export default function HomePage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    // Get user location
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          fetchLocations(latitude, longitude);
          initializeMap(longitude, latitude);
        },
        (error) => {
          console.log('Error getting location:', error);
          // Fallback to default location
          fetchLocations(43.6532, -79.3832);
          initializeMap(-79.3832, 43.6532);
        }
      );
    } else {
      // Fallback to default location
      fetchLocations(43.6532, -79.3832);
      initializeMap(-79.3832, 43.6532);
    }
  }, []);

  const initializeMap = (lng: number, lat: number) => {
    if (map.current) return; // Initialize map only once

    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || 'pk.test';
    
    map.current = new mapboxgl.Map({
      container: mapContainer.current!,
      style: 'mapbox://styles/mapbox/outdoors-v12',
      center: [lng, lat],
      zoom: 12,
      pitch: 60,
      bearing: 0,
      antialias: true
    });

    map.current.on('load', () => {
      console.log('Map loaded');
    });
  };

  const fetchLocations = async (lat: number, lon: number) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/api/locations?lat=${lat}&lon=${lon}`);
      if (!response.ok) {
        throw new Error('Failed to fetch locations');
      }
      const data = await response.json();
      setLocations(data);
      addMarkersToMap(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  const addMarkersToMap = (locations: Location[]) => {
    if (!map.current) return;

    // Remove existing markers
    const existingMarkers = document.querySelectorAll('.mapboxgl-marker');
    existingMarkers.forEach(marker => marker.remove());

    locations.forEach((location, idx) => {
      // Create marker element
      const markerEl = document.createElement('div');
      markerEl.className = 'marker';
      markerEl.innerHTML = getMarkerColor(location.type);
      markerEl.style.fontSize = '24px';
      markerEl.style.cursor = 'pointer';
      markerEl.style.userSelect = 'none';

      // Create popup
      const popup = new mapboxgl.Popup({ offset: 25 })
        .setHTML(`
          <div class="p-2 max-w-xs">
            <h3 class="font-bold text-lg mb-2">${location.name}</h3>
            <div class="text-sm text-gray-600 whitespace-pre-line">
              ${location.summary}
            </div>
            <div class="text-xs text-gray-500 mt-2">
              Type: ${location.type}
            </div>
          </div>
        `);

      // Create and add marker
      const marker = new mapboxgl.Marker(markerEl)
        .setLngLat([location.lng, location.lat])
        .setPopup(popup)
        .addTo(map.current!);

      // Add click event
      markerEl.addEventListener('click', () => {
        setSelectedLocation(location);
      });
    });
  };

  const getMarkerColor = (type: string) => {
    switch (type) {
      case 'weather':
        return '🔵';
      case 'event':
        return '🟢';
      case 'news':
        return '🟡';
      case 'reddit':
        return '🟠';
      default:
        return '📍';
    }
  };

  if (error) {
    return (
      <div className="h-screen w-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Error</h1>
          <p className="text-gray-600">{error}</p>
          <button 
            onClick={() => fetchLocations(43.6532, -79.3832)}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen relative">
      {loading && (
        <div className="absolute top-4 left-4 z-10 bg-white p-4 rounded-lg shadow-lg">
          <div className="flex items-center space-x-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
            <span>Loading local data...</span>
          </div>
        </div>
      )}
      
      <div ref={mapContainer} className="h-full w-full" />
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg">
        <h4 className="font-bold mb-2">Legend</h4>
        <div className="space-y-1 text-sm">
          <div className="flex items-center space-x-2">
            <span>🔵</span>
            <span>Weather</span>
          </div>
          <div className="flex items-center space-x-2">
            <span>🟢</span>
            <span>Events</span>
          </div>
          <div className="flex items-center space-x-2">
            <span>🟡</span>
            <span>News</span>
          </div>
          <div className="flex items-center space-x-2">
            <span>🟠</span>
            <span>Reddit</span>
          </div>
        </div>
      </div>
    </div>
  );
}
