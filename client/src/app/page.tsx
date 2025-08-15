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
  creation_date?: string; // Optional date field for 311 services
}

// Helper function to format dates
const formatDate = (dateString: string) => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    return dateString; // Return original string if parsing fails
  }
};

const getThemeColors = (type: string) => {
  switch (type) {
    case "event":
      return {
        primary: "#8b5cf6", // purple
        secondary: "#7c3aed",
        light: "#f3e8ff",
        text: "#581c87",
        gradient: "from-violet-400 to-violet-600",
      }
    case "news":
      return {
        primary: "#ef4444", // red
        secondary: "#dc2626",
        light: "#fef2f2",
        text: "#991b1b",
        gradient: "from-red-400 to-red-600",
      }
    case "reddit":
      return {
        primary: "#f97316", // orange
        secondary: "#ea580c",
        light: "#fff7ed",
        text: "#9a3412",
        gradient: "from-orange-400 to-orange-600",
      }
    case "311_service":
      return {
        primary: "#10b981", // emerald
        secondary: "#059669",
        light: "#ecfdf5",
        text: "#065f46",
        gradient: "from-emerald-400 to-emerald-600",
      }
    default:
      return {
        primary: "#6b7280",
        secondary: "#4b5563",
        light: "#f9fafb",
        text: "#374151",
        gradient: "from-gray-400 to-gray-600",
      }
  }
}

const LocationPopup = ({ location, onClose }: { location: Location; onClose: () => void }) => {
  const theme = getThemeColors(location.type)
  const isEvent = location.type === 'event'

  const shareLocation = async () => {
    const shareData = {
      title: location.name,
      text: `${location.name} - ${location.summary}`,
      url: `https://maps.google.com/?q=${location.lat},${location.lng}`
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
      } else {
        const shareText = `${location.name}\n\n${location.summary}\n\nLocation: https://maps.google.com/?q=${location.lat},${location.lng}`;
        await navigator.clipboard.writeText(shareText);
        showToast('Location shared to clipboard!');
      }
    } catch (error) {
      console.error('Error sharing:', error);
      showToast('Failed to share location');
    }
  };

  const copyToClipboard = async () => {
    const coordinates = `${location.lat}, ${location.lng}`;
    try {
      await navigator.clipboard.writeText(coordinates);
      showToast('Coordinates copied to clipboard!');
    } catch (error) {
      console.error('Error copying:', error);
      showToast('Failed to copy coordinates');
    }
  };

  const showToast = (message: string) => {
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 right-4 z-[10001] bg-gray-900 text-white px-4 py-3 rounded-lg shadow-xl text-sm font-medium transform transition-all duration-300 ease-out opacity-0 translate-y-2';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => {
      toast.classList.remove('opacity-0', 'translate-y-2');
      toast.classList.add('opacity-100', 'translate-y-0');
    }, 10);
    
    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-2');
      setTimeout(() => {
        if (document.body.contains(toast)) {
          document.body.removeChild(toast);
        }
      }, 300);
    }, 2700);
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'event': 
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
          </svg>
        );
      case 'news': 
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        );
      case 'reddit': 
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case '311_service': 
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        );
      default: 
        return (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
          </svg>
        );
    }
  };

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-6 bg-black/5 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className={`${
          isEvent ? 'max-w-4xl' : 'max-w-2xl'
        } w-full bg-white/90 backdrop-blur-xl rounded-2xl shadow-lg border border-white/20 overflow-hidden transform transition-all duration-300 ease-out scale-100 animate-in fade-in-0 zoom-in-95`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Clean Header */}
        <div className="p-8 pb-6">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: theme.primary + '10' }}>
                <div style={{ color: theme.primary }}>
                  {getTypeIcon(location.type)}
                </div>
              </div>
              <div className="min-w-0">
                <h3 className={`${
                  isEvent ? 'text-2xl' : 'text-xl'
                } font-light text-gray-900 leading-tight tracking-tight`}>
                  {location.name}
                </h3>
                <p className="text-sm text-gray-500 mt-1 font-medium tracking-wide">
                  {location.type.replace("_", " ")}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-all duration-200 cursor-pointer"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="space-y-6">
            {/* Summary */}
            <div>
              <p className="text-gray-600 leading-relaxed font-light text-sm tracking-wide">
                {location.summary}
              </p>
            </div>

            {/* Date for 311 services */}
            {location.type === "311_service" && location.creation_date && (
              <div
                className="rounded-xl p-4 border"
                style={{
                  backgroundColor: theme.light,
                  borderColor: theme.primary + "20",
                }}
              >
                <div className="text-xs uppercase tracking-[0.2em] font-medium mb-2" style={{ color: theme.text }}>
                  Reported
                </div>
                <div className="text-sm text-gray-700 font-light tracking-wide">
                  {formatDate(location.creation_date)}
                </div>
              </div>
            )}

            {/* Coordinates and Actions */}
            <div className="pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-[0.2em] font-medium mb-1 text-gray-500">
                    Location
                  </div>
                  <div className="text-sm text-gray-600 font-mono tracking-wide">
                    {location.lat.toFixed(6)}, {location.lng.toFixed(6)}
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={shareLocation}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-white transition-all duration-200 hover:scale-105 cursor-pointer"
                    style={{ backgroundColor: theme.primary }}
                    title="Share location"
                  >
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                    </svg>
                  </button>
                  <button
                    onClick={copyToClipboard}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-white transition-all duration-200 hover:scale-105 cursor-pointer"
                    style={{ backgroundColor: theme.primary }}
                    title="Copy coordinates"
                  >
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
};

const Sidebar = ({ isOpen, onToggle, locations, activeFilters, onFilterChange, recentLocations, onLocationSelect, useLiveCoordinates, onToggleLiveCoordinates, currentCity }: { 
  isOpen: boolean; 
  onToggle: () => void; 
  locations: Location[];
  activeFilters: string[];
  onFilterChange: (filters: string[]) => void;
  recentLocations: Location[];
  onLocationSelect: (location: Location) => void;
  useLiveCoordinates: boolean;
  onToggleLiveCoordinates: () => void;
  currentCity: string;
}) => {
  const locationTypes = [
    {
      type: "event",
      label: "Events",
      color: "bg-slate-700",
      count: locations.filter((l) => l.type === "event").length,
    },
    { type: "news", label: "News", color: "bg-slate-600", count: locations.filter((l) => l.type === "news").length },
    {
      type: "reddit",
      label: "Reddit",
      color: "bg-slate-500",
      count: locations.filter((l) => l.type === "reddit").length,
    },
    {
      type: "311_service",
      label: "Services",
      color: "bg-slate-400",
      count: locations.filter((l) => l.type === "311_service").length,
    },
  ]

  const toggleFilter = (type: string) => {
    const newFilters = activeFilters.includes(type) 
      ? activeFilters.filter((t) => t !== type) 
      : [...activeFilters, type];
    onFilterChange(newFilters);
  }

  // Calculate real statistics
  const totalPoints = locations.length;
  const visiblePoints = activeFilters.length === 0 ? 0 : locations.filter(l => activeFilters.includes(l.type)).length;
  const radiusKm = 8; // This could be made dynamic based on actual data

  return (
    <div
      className={`fixed left-0 top-0 h-full w-96 bg-white/95 backdrop-blur-2xl z-50 shadow-2xl border-r border-gray-100/50 transition-all duration-700 ease-out ${
        isOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
             {/* Header */}
       <div className="p-8 border-b border-gray-50/50">
         <div className="flex items-center justify-between mb-4">
           <div>
             <h2 className="text-2xl font-light text-gray-900 tracking-tight">Insights</h2>
             <p className="text-sm text-gray-400 mt-1 font-light tracking-wide">{currentCity} Data Explorer</p>
           </div>
           <button
             onClick={onToggle}
             className="w-10 h-10 bg-gray-50/50 hover:bg-gray-100/50 rounded-2xl flex items-center justify-center text-gray-400 hover:text-gray-600 transition-all duration-300 border border-gray-100/30 cursor-pointer"
           >
             <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
               <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
             </svg>
           </button>
         </div>

         {/* Live Coordinates Toggle */}
         <div className="mb-4">
           <label className="flex items-center space-x-3 cursor-pointer">
             <div className="relative">
               <input
                 type="checkbox"
                 checked={useLiveCoordinates}
                 onChange={onToggleLiveCoordinates}
                 className="sr-only"
               />
               <div className={`w-12 h-6 rounded-full transition-colors duration-300 ${useLiveCoordinates ? 'bg-blue-500' : 'bg-gray-300'}`}>
                 <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-300 ${useLiveCoordinates ? 'translate-x-6' : 'translate-x-1'}`}></div>
               </div>
             </div>
             <span className="text-sm font-medium text-gray-700">
               Use Live Coordinates
             </span>
           </label>
           <p className="text-xs text-gray-500 mt-1 ml-15">
             {useLiveCoordinates ? 'Using your current location' : 'Using Toronto coordinates'}
           </p>
         </div>
       </div>

      {/* Content */}
      <div className="p-8 space-y-10 overflow-y-auto h-full pb-32">
        {/* Statistics */}
        <div>
          <h3 className="text-lg font-light text-gray-900 mb-6 tracking-tight">Overview</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-25/50 rounded-2xl p-6 border border-gray-50/50">
              <div className="text-3xl font-light text-gray-900 mb-2">{visiblePoints}</div>
              <div className="text-xs text-gray-400 uppercase tracking-widest font-light">Visible Points</div>
            </div>
            <div className="bg-gray-25/50 rounded-2xl p-6 border border-gray-50/50">
              <div className="text-3xl font-light text-gray-900 mb-2">{activeFilters.length}</div>
              <div className="text-xs text-gray-400 uppercase tracking-widest font-light">Active Filters</div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-light text-gray-900 tracking-tight">Data Types</h3>
            {activeFilters.length < locationTypes.length && (
              <button
                onClick={() => onFilterChange(locationTypes.map(item => item.type))}
                className="text-xs text-gray-500 hover:text-gray-700 font-medium tracking-wide cursor-pointer"
              >
                Show All
              </button>
            )}
          </div>
          <div className="space-y-3">
            {locationTypes.map((item) => (
              <button
                key={item.type}
                onClick={() => toggleFilter(item.type)}
                className={`w-full flex items-center justify-between p-4 rounded-2xl border transition-all duration-300 ${
                  activeFilters.includes(item.type)
                    ? "bg-black text-white border-black shadow-lg"
                    : "bg-white/50 hover:bg-gray-25/50 border-gray-100/50 text-gray-700"
                } cursor-pointer`}
              >
                <div className="flex items-center space-x-4">
                  <div
                    className={`w-2 h-2 rounded-full ${activeFilters.includes(item.type) ? "bg-white" : item.color}`}
                  ></div>
                  <span className="font-light tracking-wide">{item.label}</span>
                </div>
                <div
                  className={`text-sm font-light ${
                    activeFilters.includes(item.type) ? "text-white/70" : "text-gray-400"
                  }`}
                >
                  {item.count}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div>
          <h3 className="text-lg font-light text-gray-900 mb-6 tracking-tight">Recent Activity</h3>
          <div className="space-y-4">
            {recentLocations.length > 0 ? (
              recentLocations.map((location, idx) => {
                const theme = getThemeColors(location.type);
                return (
                  <button
                    key={idx}
                    onClick={() => onLocationSelect(location)}
                    className="w-full bg-white/50 rounded-2xl p-5 border border-gray-100/50 hover:bg-white/70 transition-all duration-200 text-left cursor-pointer"
                  >
                    <div className="flex items-start space-x-4">
                      <div 
                        className="w-2 h-2 rounded-full flex-shrink-0 mt-2"
                        style={{ backgroundColor: theme.primary }}
                      ></div>
                      <div className="min-w-0">
                        <div className="font-light text-gray-900 text-sm leading-tight tracking-tight truncate">
                          {location.name}
                        </div>
                        <div className="text-xs text-gray-400 mt-1 capitalize font-light tracking-wide">
                          {location.type.replace("_", " ")}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="bg-white/50 rounded-2xl p-5 border border-gray-100/50">
                <div className="text-center">
                  <div className="text-gray-400 text-sm font-light tracking-wide">
                    Click on map markers to see recent activity
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function HomePage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [filteredLocations, setFilteredLocations] = useState<Location[]>([]);
  const [activeFilters, setActiveFilters] = useState<string[]>(['event', 'news', 'reddit', '311_service']); // Start with all active
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null);
  const [recentLocations, setRecentLocations] = useState<Location[]>([]); // Track last 3 clicked locations
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [useLiveCoordinates, setUseLiveCoordinates] = useState(false);
  const [userLocation, setUserLocation] = useState<{lat: number, lng: number} | null>(null);
  const [currentCity, setCurrentCity] = useState("Toronto");
  const [isFetching, setIsFetching] = useState(false);
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);

  // Your exact location coordinates
  const TORONTO_LAT = 43.6469;  
  const TORONTO_LNG = -79.3775;
  const RADIUS_KM = 8; // Adjust this value to change boundary size

  // Get user's current location
  const getUserLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation({ lat: latitude, lng: longitude });
          console.log('User location obtained:', { lat: latitude, lng: longitude });
        },
        (error) => {
          console.error('Error getting user location:', error);
          setUseLiveCoordinates(false);
        }
      );
    } else {
      console.log('Geolocation not supported');
      setUseLiveCoordinates(false);
    }
  };

  // Get current coordinates based on toggle
  const getCurrentCoordinates = () => {
    if (useLiveCoordinates && userLocation) {
      return userLocation;
    }
    return { lat: TORONTO_LAT, lng: TORONTO_LNG };
  };

  // Update filtered locations when locations or filters change
  useEffect(() => {
    if (activeFilters.length === 0) {
      setFilteredLocations([]); // Show nothing when no filters are active
    } else {
      const filtered = locations.filter(location => activeFilters.includes(location.type));
      setFilteredLocations(filtered);
    }
  }, [locations, activeFilters]);

  // Update map markers when filtered locations change
  useEffect(() => {
    addMarkersToMap(filteredLocations);
  }, [filteredLocations]);

  // Get user location when component mounts
  useEffect(() => {
    getUserLocation();
  }, []);

  // Update when coordinates change
  useEffect(() => {
    const coords = getCurrentCoordinates();
    console.log('📍 Current coordinates:', { lat: coords.lat, lng: coords.lng });
    console.log('📍 Live coordinates enabled:', useLiveCoordinates);
    console.log('📍 User location:', userLocation);
    fetchLocations(coords.lat, coords.lng);
    if (map.current) {
      console.log('🗺️ Attempting to center map on:', [coords.lng, coords.lat]);
      // Remove existing constraints if using live coordinates
      if (useLiveCoordinates) {
        console.log('🗺️ Removing map constraints for live coordinates...');
        try {
          // Remove bounds constraints
          (map.current as any).setMaxBounds(null);
          // Remove zoom constraints  
          (map.current as any).setMaxZoom(null);
        } catch (e) {
          console.log('Could not remove constraints:', e);
        }
      }
      
      // Use flyTo for smoother and more reliable centering
      map.current.flyTo({
        center: [coords.lng, coords.lat],
        zoom: 16.2, // More zoomed out to see the area
        duration: 2000
      });
      
      // Add constraints for both Toronto and live coordinates
      addMapConstraints(coords.lat, coords.lng);
    }
  }, [useLiveCoordinates, userLocation]);

  const handleFilterChange = (filters: string[]) => {
    setActiveFilters(filters);
  };

  // Add location to recent history when clicked
  const addToRecent = (location: Location) => {
    setRecentLocations(prev => {
      // Remove if already exists (to avoid duplicates)
      const filtered = prev.filter(loc => 
        loc.lat !== location.lat || loc.lng !== location.lng || loc.name !== location.name
      );
      // Add to beginning and keep only last 3
      const newRecent = [location, ...filtered].slice(0, 3);
      return newRecent;
    });
  };

  useEffect(() => {
    // Use current coordinates as the center
    const coords = getCurrentCoordinates();
    console.log('Initializing map with coordinates:', coords);
    fetchLocations(coords.lat, coords.lng);
    initializeMap(coords.lng, coords.lat);
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

          // TEMPORARILY DISABLED - Add map constraints to keep view within 10km radius
          // addMapConstraints(lat, lng);
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
    
    // Set a higher max zoom level to allow more zooming in
    map.current.setMaxZoom(20);
    
    // Add center point marker
    const centerMarkerEl = document.createElement('div');
    centerMarkerEl.className = 'center-marker';
    centerMarkerEl.innerHTML = `
      <div style="
        width: 8px;
        height: 8px;
        background: linear-gradient(135deg, #000 0%, #333 100%);
        border: 3px solid rgba(255,255,255,0.95);
        border-radius: 50%;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15), 0 1px 3px rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
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
    if (isFetching) {
      console.log('🚫 Skipping API call - already fetching');
      return;
    }
    try {
      setIsFetching(true);
      setLoading(true);
      console.log('🔄 Starting API call, loading screen should be visible');
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
      setCurrentCity(data[data.length - 1]?.city || "Toronto");
      console.log('✅ API call completed, setting loading to false');
      setLoading(false);
      setIsFetching(false);
      // Filtered locations will be updated automatically by the useEffect
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
      setLoading(false);
      setIsFetching(false);
    }
  };

  const addMarkersToMap = (locations: Location[]) => {
    if (!map.current) return

    console.log("Adding markers for locations:", locations)

    const existingMarkers = document.querySelectorAll(".mapboxgl-marker:not(.center-marker)")
    existingMarkers.forEach((marker) => marker.remove())

    locations.forEach((location, idx) => {
      const lat = Number(location.lat)
      const lng = Number(location.lng)

      if (isNaN(lat) || isNaN(lng)) {
        console.error(`Invalid coordinates for ${location.name}: lat=${location.lat}, lng=${location.lng}`)
        return
      }

      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        console.error(`Coordinates out of range for ${location.name}: lat=${lat}, lng=${lng}`)
        return
      }

      const theme = getThemeColors(location.type)
      // Create a simple colored circle marker
      const markerEl = document.createElement('div');
      markerEl.style.width = '16px';
      markerEl.style.height = '16px';
      markerEl.style.background = `radial-gradient(circle at 30% 30%, #ffffff 0%, ${getMarkerColor(location.type)} 40%, ${getMarkerColor(location.type)} 100%)`;
      markerEl.style.border = 'none';
      markerEl.style.borderRadius = '50%';
      markerEl.style.boxShadow = `0 0 20px ${getMarkerColor(location.type)}80, 0 0 40px ${getMarkerColor(location.type)}60, 0 4px 8px rgba(0,0,0,0.4), inset 0 2px 4px rgba(255,255,255,0.8), inset 0 -2px 4px rgba(0,0,0,0.3)`;
      markerEl.style.cursor = 'pointer';
      markerEl.style.zIndex = '1000';

      const marker = new mapboxgl.Marker({
        element: markerEl,
        anchor: 'center'
      })
        .setLngLat([lng, lat])
        .addTo(map.current!)

      markerEl.addEventListener('click', (e) => {
        e.stopPropagation()
        setSelectedLocation(location)
        addToRecent(location)  // ✅ Add this line to track recent activity
      })
    })
  }

  const getMarkerColor = (type: string) => {
    const theme = getThemeColors(type)
    return theme.primary
  };

  if (error) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-gray-25">
        <div className="text-center max-w-md mx-auto p-12">
          <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-8 border border-gray-100">
            <svg
              className="w-6 h-6 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          <h1 className="text-xl font-light text-gray-900 mb-3 tracking-tight">Connection Error</h1>
          <p className="text-gray-500 mb-8 font-light leading-relaxed">{error}</p>
          <button
            onClick={() => fetchLocations(TORONTO_LAT, TORONTO_LNG)}
            className="px-8 py-4 bg-black text-white rounded-2xl hover:bg-gray-800 transition-all duration-300 font-light tracking-wide cursor-pointer"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen relative bg-gray-25">
      <Sidebar 
        isOpen={sidebarOpen} 
        onToggle={() => setSidebarOpen(!sidebarOpen)} 
        locations={locations} 
        activeFilters={activeFilters} 
        onFilterChange={handleFilterChange} 
        recentLocations={recentLocations} 
        onLocationSelect={setSelectedLocation}
        useLiveCoordinates={useLiveCoordinates}
        onToggleLiveCoordinates={() => {
          setUseLiveCoordinates(!useLiveCoordinates);
          setLoading(true); // Show loading immediately when toggle is switched
        }}
        currentCity={currentCity}
      />

      {/* Map Container - adjusted to account for sidebar being open by default */}
      <div className={`h-full w-full transition-all duration-700 ease-out ${sidebarOpen ? "ml-96" : "ml-0"}`}>
        {loading && (
          <div className="absolute inset-0 z-50 bg-white/95 backdrop-blur-sm flex items-center justify-center">
            <div className="text-center">
              <div className="mb-12">
                <div className="relative w-8 h-8 mx-auto">
                  <div className="absolute inset-0 border border-gray-100 rounded-full"></div>
                  <div className="absolute inset-0 border border-black rounded-full border-t-transparent animate-spin"></div>
                </div>
              </div>

              <div className="text-gray-900 text-lg font-light mb-3 tracking-tight">Loading</div>
              <div className="text-gray-400 text-sm font-light tracking-wide">Discovering local insights</div>
            </div>
          </div>
        )}

        <div ref={mapContainer} className="h-full w-full" />

        {!sidebarOpen && (
          <div className="absolute top-8 left-8 z-10">
            <button
              onClick={() => setSidebarOpen(true)}
              className="w-12 h-12 bg-white/90 backdrop-blur-xl hover:bg-white/95 rounded-2xl flex items-center justify-center text-gray-600 hover:text-gray-900 transition-all duration-300 border border-gray-100/50 shadow-lg group cursor-pointer"
            >
              <svg
                className="w-4 h-4 transition-transform duration-300 group-hover:scale-110"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>
          </div>
        )}
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
