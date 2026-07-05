import { useState, useEffect } from 'react';
import { Map, AdvancedMarker } from '@vis.gl/react-google-maps';
import { ShieldAlert, Server, Activity } from 'lucide-react';
import { IncidentFeed } from './IncidentFeed';
import { ActionPanel } from './ActionPanel';
import type { Station, Incident } from '../types';

const INITIAL_VIEW_STATE = {
  lng: 77.2090,
  lat: 28.6139,
  zoom: 10,
};

// Mock fallback data generators
const mockStations: Station[] = [
  { id: 'S1', name: 'Mandir Marg', lat: 28.6364, lon: 77.2010, current_pm25: 45, forecast_24h: Array.from({length: 24}, (_, i) => Math.max(10, 45 - i*1.5)) },
  { id: 'S2', name: 'Anand Vihar', lat: 28.6476, lon: 77.3158, current_pm25: 120, forecast_24h: Array.from({length: 24}, (_, i) => Math.max(20, 120 - i*3)) },
  { id: 'S3', name: 'Punjabi Bagh', lat: 28.6740, lon: 77.1310, current_pm25: 85, forecast_24h: Array.from({length: 24}, (_, i) => Math.max(15, 85 - i*2)) },
];

const mockIncidents: Incident[] = [
  {
    id: "INC-001",
    type: "localized_fire",
    lat: 28.6400,
    lon: 77.2100,
    trust_score: 92.5,
    exif_match: true,
    telemetry_match: true,
    explanation: "High PM2.5 forecast is driven by: Detected garbage burning (+45%), Calm wind velocity (+30%), and adjacent industrial plume (+25%).",
    command: "Dispatch rapid response unit to (28.6400, 77.2100).",
    expected_reduction: "Expected 25% PM2.5 reduction within 2 hours.",
    resources: [{ type: "Fire Crew", quantity: 1 }, { type: "Mist Cannon", quantity: 2 }],
    timestamp: new Date(Date.now() - 15 * 60000).toISOString()
  },
  {
    id: "INC-002",
    type: "vehicular_congestion",
    lat: 28.6500,
    lon: 77.3000,
    trust_score: 60.0,
    exif_match: false,
    telemetry_match: false,
    explanation: "Elevated NO2 forecast driven by unverified traffic standstill.",
    command: "Deploy field inspector for manual verification.",
    expected_reduction: "N/A",
    resources: [{ type: "Field Inspector", quantity: 1 }],
    timestamp: new Date(Date.now() - 45 * 60000).toISOString()
  }
];

export const DashboardContainer = () => {
  const [mockMode, setMockMode] = useState(true);
  const [stations, setStations] = useState<Station[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (mockMode) {
        setStations(mockStations);
        setIncidents(mockIncidents);
        return;
      }
      try {
        // Fetch Live Data (Expected endpoints)
        const [stRes, incRes] = await Promise.all([
          fetch('http://localhost:8000/api/forecast/live').then(r => r.json()).catch(() => mockStations),
          fetch('http://localhost:8000/api/incidents/recent').then(r => r.json()).catch(() => mockIncidents)
        ]);
        setStations(stRes);
        setIncidents(incRes);
      } catch (err) {
        console.error('Failed to fetch from API, falling back to mock.', err);
        setStations(mockStations);
        setIncidents(mockIncidents);
      }
    };
    
    fetchData();
    const interval = setInterval(fetchData, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, [mockMode]);

  const verifiedIncidents = incidents.filter(i => i.trust_score >= 75);

  return (
    <div className="flex h-screen w-full bg-slate-900 text-slate-50 overflow-hidden font-sans">
      
      {/* LEFT SIDEBAR: INCIDENT QUEUE */}
      <div className="w-1/3 min-w-[400px] border-r border-slate-700 flex flex-col bg-slate-900 z-10 shadow-xl">
        <div className="p-4 border-b border-slate-700 bg-slate-800 flex justify-between items-center">
          <div className="flex items-center space-x-2 text-emerald-400">
            <ShieldAlert size={24} />
            <h1 className="font-bold text-lg tracking-wide uppercase">Command Center</h1>
          </div>
          <button 
            onClick={() => setMockMode(!mockMode)}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${mockMode ? 'bg-indigo-900/50 text-indigo-300 border border-indigo-500/30' : 'bg-emerald-900/50 text-emerald-300 border border-emerald-500/30'}`}
          >
            {mockMode ? <Activity size={14} /> : <Server size={14} />}
            <span>{mockMode ? 'Mock Mode' : 'Live Data'}</span>
          </button>
        </div>
        
        <IncidentFeed 
          incidents={incidents} 
          selectedIncidentId={selectedIncident?.id} 
          onSelectIncident={setSelectedIncident} 
        />
      </div>

      {/* RIGHT CONTENT: MAP & ACTION PANEL */}
      <div className="flex-1 flex flex-col relative">
        <div className="flex-1 relative">
          <Map 
            mapId="DEMO_MAP_ID"
            defaultCenter={INITIAL_VIEW_STATE}
            defaultZoom={INITIAL_VIEW_STATE.zoom}
            gestureHandling={'greedy'}
            disableDefaultUI={true}
            colorScheme={'DARK'}
          >
            {stations.map(station => (
              <AdvancedMarker
                key={station.id}
                position={{lat: station.lat, lng: station.lon}}
                title={`${station.name} - PM2.5: ${station.current_pm25}`}
              >
                <div className={`w-4 h-4 rounded-full ${station.current_pm25 < 50 ? 'bg-emerald-500' : station.current_pm25 < 100 ? 'bg-amber-500' : 'bg-red-500'} shadow-lg border border-white/50 opacity-80`} />
              </AdvancedMarker>
            ))}
            {verifiedIncidents.map(incident => (
              <AdvancedMarker
                key={incident.id}
                position={{lat: incident.lat, lng: incident.lon}}
                title={`Incident: ${incident.type}`}
              >
                 <div className="w-8 h-8 rounded-full border-4 border-red-500 bg-red-500/30 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.8)]" />
              </AdvancedMarker>
            ))}
          </Map>
        </div>
        
        {/* EXPANDABLE BOTTOM ACTION PANEL */}
        {selectedIncident && (
          <div className="absolute bottom-0 w-full z-20">
             <ActionPanel 
                incident={selectedIncident} 
                onClose={() => setSelectedIncident(null)} 
                stations={stations}
             />
          </div>
        )}
      </div>
    </div>
  );
};
