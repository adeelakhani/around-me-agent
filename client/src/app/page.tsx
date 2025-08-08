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

// Better Popup Component
const LocationPopup = ({ location, onClose }: { location: Location; onClose: () => void }) => {
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'weather': return 'W';
      case 'event': return 'E';
      case 'news': return 'N';
      case 'reddit': return 'R';
      default: return '•';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'weather': return 'bg-blue-500';
      case 'event': return 'bg-green-500';
      case 'news': return 'bg-yellow-500';
      case 'reddit': return 'bg-orange-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      <div className="bg-gray-900 text-white rounded-lg shadow-2xl border border-gray-700">
        {/* Header */}
        <div className={`p-4 ${getTypeColor(location.type)} rounded-t-lg`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">{getTypeIcon(location.type)}</span>
              <div>
                <h3 className="font-bold text-lg">{location.name}</h3>
                <p className="text-sm opacity-90 capitalize">{location.type}</p>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="text-white hover:text-gray-200 text-xl font-bold"
            >
              ×
            </button>
          </div>
        </div>
        
        {/* Content */}
        <div className="p-4">
          <div className="text-gray-300 whitespace-pre-line leading-relaxed text-sm">
            {location.summary}
          </div>
          
          {/* Footer */}
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="text-sm text-gray-400">
              <span>{location.lat.toFixed(4)}, {location.lng.toFixed(4)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function HomePage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);

  // Downtown Toronto coordinates
  const TORONTO_LAT = 43.6532;
  const TORONTO_LNG = -79.3832;
  const RADIUS_KM = 8; // Adjust this value to change boundary size

  useEffect(() => {
    // Use downtown Toronto as the center
    console.log('Initializing map with Toronto coordinates:', { lat: TORONTO_LAT, lng: TORONTO_LNG });
    fetchLocations(TORONTO_LAT, TORONTO_LNG);
    initializeMap(TORONTO_LNG, TORONTO_LAT);
  }, []);

  const initializeMap = (lng: number, lat: number) => {
    if (map.current) return; // Initialize map only once

    mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || 'pk.test';
    
    map.current = new mapboxgl.Map({
      container: mapContainer.current!,
      style: 'mapbox://styles/adeel712/cme2f1k6500rc01s7fmh93ciq',
      center: [lng, lat],
      zoom: 18, // Much more zoomed in
      pitch: 45,
      bearing: 0,
      antialias: true
    });

    console.log('Map initialized with center:', [lng, lat]);

    map.current.on('load', () => {
      console.log('Map loaded');
      
              if (map.current) {
          // Wait for the map to be fully loaded
          map.current.on('idle', () => {
            if (!map.current) return;
            console.log('Custom Mapbox style loaded');
          });
          
          // Add 3D building extrusions with better visibility
          map.current.addLayer({
            'id': '3d-buildings',
            'source': 'composite',
            'source-layer': 'building',
            'filter': ['==', 'extrude', 'true'],
            'type': 'fill-extrusion',
            'minzoom': 15,
            'paint': {
              'fill-extrusion-color': '#3a3a3a',
              'fill-extrusion-height': [
                'interpolate',
                ['linear'],
                ['zoom'],
                15,
                0,
                15.05,
                ['get', 'height']
              ],
              'fill-extrusion-base': [
                'interpolate',
                ['linear'],
                ['zoom'],
                15,
                0,
                15.05,
                ['get', 'min_height']
              ],
              'fill-extrusion-opacity': 0.9
            }
          });

          // Add map constraints to keep view within 10km radius
          addMapConstraints(lat, lng);
        }
    });
  };

  const addMapConstraints = (lat: number, lng: number) => {
    if (!map.current) return;

    // Calculate the bounds for 10km radius
    // At Toronto's latitude (43.6532°), 1° latitude ≈ 111.32 km
    // 1° longitude ≈ 111.32 * cos(43.6532°) ≈ 80.4 km
    const radiusLatDegrees = RADIUS_KM / 111.32;
    const radiusLngDegrees = RADIUS_KM / (111.32 * Math.cos(lat * Math.PI / 180));

    // Calculate bounds
    const bounds = [
      [lng - radiusLngDegrees, lat - radiusLatDegrees], // Southwest
      [lng + radiusLngDegrees, lat + radiusLatDegrees]  // Northeast
    ] as [[number, number], [number, number]];

    // Set the map bounds to constrain the view
    map.current.setMaxBounds(bounds);
    
    // Also set a maximum zoom level to prevent zooming out too far
    map.current.setMaxZoom(16);
    
    // Add center point marker
    const centerMarkerEl = document.createElement('div');
    centerMarkerEl.className = 'center-marker';
    centerMarkerEl.innerHTML = `
      <div style="
        width: 16px;
        height: 16px;
        background: #3B82F6;
        border: 3px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      "></div>
    `;

    new mapboxgl.Marker({
      element: centerMarkerEl,
      anchor: 'center'
    })
      .setLngLat([lng, lat])
      .addTo(map.current!);
  };

  const fetchLocations = async (lat: number, lon: number) => {
    try {
      setLoading(true);
      console.log('Fetching locations for:', { lat, lon });
      const response = await fetch(`http://localhost:8000/api/locations?lat=${lat}&lon=${lon}&t=${Date.now()}`);
      if (!response.ok) {
        throw new Error('Failed to fetch locations');
      }
      const data = await response.json();
      console.log('Received data from backend:', data);
      console.log('Backend data details:');
      data.forEach((location: Location, index: number) => {
        console.log(`Location ${index + 1}:`, {
          name: location.name,
          lat: location.lat,
          lng: location.lng,
          type: location.type,
          summary: location.summary?.substring(0, 100) + '...'
        });
      });
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

    console.log('Adding markers for locations:', locations);

    // Remove existing markers
    const existingMarkers = document.querySelectorAll('.mapboxgl-marker:not(.center-marker)');
    existingMarkers.forEach(marker => marker.remove());

    locations.forEach((location, idx) => {
      console.log(`Creating marker ${idx + 1}:`, {
        name: location.name,
        lat: location.lat,
        lng: location.lng,
        type: location.type,
        latType: typeof location.lat,
        lngType: typeof location.lng
      });

      // Ensure coordinates are numbers and validate them
      const lat = Number(location.lat);
      const lng = Number(location.lng);
      
      // Validate coordinates
      if (isNaN(lat) || isNaN(lng)) {
        console.error(`Invalid coordinates for ${location.name}: lat=${location.lat}, lng=${location.lng}`);
        return;
      }
      
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        console.error(`Coordinates out of range for ${location.name}: lat=${lat}, lng=${lng}`);
        return;
      }
      
      console.log(`Parsed coordinates: lat=${lat} (${typeof lat}), lng=${lng} (${typeof lng})`);

      // Create a simple colored circle marker
      const markerEl = document.createElement('div');
      markerEl.style.width = '32px';
      markerEl.style.height = '32px';
      markerEl.style.backgroundColor = getMarkerColor(location.type);
      markerEl.style.border = '3px solid white';
      markerEl.style.borderRadius = '50%';
      markerEl.style.boxShadow = '0 4px 8px rgba(0,0,0,0.5)';
      markerEl.style.cursor = 'pointer';
      markerEl.style.zIndex = '1000';

      // Create and add marker with proper positioning
      const marker = new mapboxgl.Marker({
        element: markerEl,
        anchor: 'center'
      })
        .setLngLat([lng, lat])
        .addTo(map.current!);

      console.log(`Marker ${location.name} positioned at:`, [lng, lat]);
      console.log(`Raw coordinates from backend: lat=${location.lat}, lng=${location.lng}`);
      console.log(`Mapbox expects: [longitude, latitude] = [${lng}, ${lat}]`);

      // Add click event
      markerEl.addEventListener('click', (e) => {
        e.stopPropagation();
        console.log('Marker clicked:', location.name);
        console.log('Setting selected location with coordinates:', { lat: location.lat, lng: location.lng });
        setSelectedLocation(location);
      });
    });
  };

  const getMarkerColor = (type: string) => {
    switch (type) {
      case 'weather':
        return '#3B82F6'; // Blue
      case 'event':
        return '#10B981'; // Green
      case 'news':
        return '#F59E0B'; // Yellow
      case 'reddit':
        return '#F97316'; // Orange
      default:
        return '#6B7280'; // Gray
    }
  };

  if (error) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-gray-900">
        <div className="text-center text-white">
          <h1 className="text-2xl font-bold text-red-400 mb-4">Error</h1>
          <p className="text-gray-300">{error}</p>
          <button 
            onClick={() => fetchLocations(TORONTO_LAT, TORONTO_LNG)}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen relative bg-gray-900">
      {/* Map Container */}
      <div className="h-full w-full relative">
        {loading && (
          <div className="absolute inset-0 z-50 bg-gray-900 bg-opacity-95 backdrop-blur-sm flex items-center justify-center">
            <div className="text-center">
              {/* Animated Logo/Icon */}
              <div className="mb-6">
                <div className="relative w-16 h-16 mx-auto">
                  <div className="absolute inset-0 bg-blue-500 rounded-full animate-pulse"></div>
                  <div className="absolute inset-2 bg-gray-900 rounded-full"></div>
                  <div className="absolute inset-4 bg-blue-400 rounded-full animate-bounce"></div>
                </div>
              </div>
              
              {/* Loading Text */}
              <div className="text-white text-xl font-light mb-2">
                Discovering your area
              </div>
              <div className="text-gray-400 text-sm">
                Finding the best local spots
              </div>
              
              {/* Progress Bar */}
              <div className="mt-6 w-48 mx-auto">
                <div className="bg-gray-700 rounded-full h-1 overflow-hidden">
                  <div className="bg-blue-500 h-1 rounded-full animate-pulse" style={{width: '60%'}}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={mapContainer} className="h-full w-full" />
        
        {/* Map Controls - Top Left */}
        <div className="absolute top-4 left-4 z-10">
          <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-2">
            <div className="space-y-2">
              <button className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded flex items-center justify-center text-gray-700">
                +
              </button>
              <button className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded flex items-center justify-center text-gray-700">
                -
              </button>
              <button className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded flex items-center justify-center text-gray-700">
                3D
              </button>
              <button className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded flex items-center justify-center text-gray-700">
                🧭
              </button>
            </div>
          </div>
        </div>

        {/* Radius Info */}
        <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-lg border border-gray-200 p-3">
          <div className="text-sm text-gray-700">
            <div className="font-semibold">Downtown Toronto</div>
            <div className="text-xs text-gray-500">{RADIUS_KM}km radius</div>
          </div>
        </div>
      </div>
      
      {/* Selected Location Popup */}
      {selectedLocation && (
        <LocationPopup 
          location={selectedLocation} 
          onClose={() => setSelectedLocation(null)} 
        />
      )}
    </div>
  );
}
