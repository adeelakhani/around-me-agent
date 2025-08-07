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
      case 'weather': return '🌤️';
      case 'event': return '🎉';
      case 'news': return '📰';
      case 'reddit': return '💬';
      default: return '📍';
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 text-white rounded-lg shadow-2xl max-w-md mx-4 border border-gray-700">
        {/* Header */}
        <div className={`p-4 ${getTypeColor(location.type)} rounded-t-lg`}>
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{getTypeIcon(location.type)}</span>
            <div>
              <h3 className="font-bold text-lg">{location.name}</h3>
              <p className="text-sm opacity-90 capitalize">{location.type}</p>
            </div>
          </div>
        </div>
        
        {/* Content */}
        <div className="p-4">
          <div className="text-gray-300 whitespace-pre-line leading-relaxed">
            {location.summary}
          </div>
          
          {/* Footer */}
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="flex items-center justify-between text-sm text-gray-400">
              <span>📍 {location.lat.toFixed(4)}, {location.lng.toFixed(4)}</span>
              <button 
                onClick={onClose}
                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
              >
                Close
              </button>
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
      style: 'mapbox://styles/mapbox/navigation-night-v1',
      center: [lng, lat],
      zoom: 13,
      pitch: 45,
      bearing: 0,
      antialias: true
    });

    map.current.on('load', () => {
      console.log('Map loaded');
      
      if (map.current) {
        // Add terrain
        map.current.addSource('mapbox-terrain', {
          'type': 'vector',
          'url': 'mapbox://mapbox.mapbox-terrain-v2'
        });
        
        map.current.addLayer({
          'id': 'terrain',
          'type': 'hillshade',
          'source': 'mapbox-terrain',
          'source-layer': 'terrain',
          'paint': {
            'hillshade-shadow-color': '#000000',
            'hillshade-highlight-color': '#FFFFFF',
            'hillshade-accent-color': '#000000'
          }
        });
        
        // Add 3D building extrusions
        map.current.addLayer({
          'id': '3d-buildings',
          'source': 'composite',
          'source-layer': 'building',
          'filter': ['==', 'extrude', 'true'],
          'type': 'fill-extrusion',
          'minzoom': 15,
          'paint': {
            'fill-extrusion-color': '#404040',
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
            'fill-extrusion-opacity': 0.8
          }
        });
      }
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
      // Create marker element with always-visible label
      const markerEl = document.createElement('div');
      markerEl.className = 'marker-container';
      markerEl.innerHTML = `
        <div class="marker-icon">${getMarkerColor(location.type)}</div>
        <div class="marker-label">
          <div class="label-bg">
            <span class="label-text">${location.name}</span>
          </div>
        </div>
      `;
      
      // Add styles for the marker
      markerEl.style.position = 'relative';
      markerEl.style.cursor = 'pointer';
      markerEl.style.userSelect = 'none';
      markerEl.style.zIndex = '1000';
      
      // Style the marker icon
      const iconEl = markerEl.querySelector('.marker-icon') as HTMLElement;
      if (iconEl) {
        iconEl.style.fontSize = '32px';
        iconEl.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.8))';
        iconEl.style.display = 'block';
        iconEl.style.textAlign = 'center';
      }
      
      // Style the label
      const labelEl = markerEl.querySelector('.marker-label') as HTMLElement;
      if (labelEl) {
        labelEl.style.position = 'absolute';
        labelEl.style.top = '-50px';
        labelEl.style.left = '50%';
        labelEl.style.transform = 'translateX(-50%)';
        labelEl.style.whiteSpace = 'nowrap';
        labelEl.style.zIndex = '1001';
        labelEl.style.pointerEvents = 'none';
      }
      
      const labelBgEl = markerEl.querySelector('.label-bg') as HTMLElement;
      if (labelBgEl) {
        labelBgEl.style.background = 'rgba(0,0,0,0.9)';
        labelBgEl.style.color = 'white';
        labelBgEl.style.padding = '6px 10px';
        labelBgEl.style.borderRadius = '6px';
        labelBgEl.style.fontSize = '11px';
        labelBgEl.style.fontWeight = '600';
        labelBgEl.style.backdropFilter = 'blur(8px)';
        labelBgEl.style.border = '1px solid rgba(255,255,255,0.2)';
        labelBgEl.style.maxWidth = '200px';
        labelBgEl.style.overflow = 'hidden';
        labelBgEl.style.textOverflow = 'ellipsis';
      }

      // Create and add marker with proper positioning
      const marker = new mapboxgl.Marker({
        element: markerEl,
        anchor: 'bottom'
      })
        .setLngLat([location.lng, location.lat])
        .addTo(map.current!);

      // Debug: Log marker position
      console.log(`Marker ${location.name}:`, { lat: location.lat, lng: location.lng });

      // Add click event to the entire marker element
      markerEl.addEventListener('click', (e) => {
        e.stopPropagation();
        console.log('Marker clicked:', location.name);
        setSelectedLocation(location);
      });

      // Also add click event to the marker icon specifically
      const iconElement = markerEl.querySelector('.marker-icon') as HTMLElement;
      if (iconElement) {
        iconElement.addEventListener('click', (e) => {
          e.stopPropagation();
          console.log('Marker icon clicked:', location.name);
          setSelectedLocation(location);
        });
      }
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
      <div className="h-screen w-screen flex items-center justify-center bg-gray-900">
        <div className="text-center text-white">
          <h1 className="text-2xl font-bold text-red-400 mb-4">Error</h1>
          <p className="text-gray-300">{error}</p>
          <button 
            onClick={() => fetchLocations(43.6532, -79.3832)}
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
          <div className="absolute top-4 left-4 z-10 bg-gray-800 text-white p-4 rounded-lg shadow-lg border border-gray-700">
            <div className="flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              <span>Loading local data...</span>
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
