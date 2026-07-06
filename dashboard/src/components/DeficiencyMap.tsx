import { useState, useEffect, useRef, useCallback } from 'react';
import { Map, useMap } from '@vis.gl/react-google-maps';
import { BarChart3, TrendingUp, Users, IndianRupee, AlertTriangle, Loader2, RefreshCw } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Approximate GeoJSON-style polygon boundaries for the 13 Delhi districts
const DISTRICT_BOUNDARIES: Record<string, { lat: number; lng: number }[]> = {
  central: [
    { lat: 28.655, lng: 77.190 }, { lat: 28.660, lng: 77.220 },
    { lat: 28.645, lng: 77.235 }, { lat: 28.625, lng: 77.230 },
    { lat: 28.615, lng: 77.210 }, { lat: 28.620, lng: 77.185 },
  ],
  central_north: [
    { lat: 28.700, lng: 77.110 }, { lat: 28.710, lng: 77.170 },
    { lat: 28.695, lng: 77.200 }, { lat: 28.675, lng: 77.195 },
    { lat: 28.665, lng: 77.150 }, { lat: 28.680, lng: 77.110 },
  ],
  east: [
    { lat: 28.670, lng: 77.280 }, { lat: 28.680, lng: 77.330 },
    { lat: 28.650, lng: 77.340 }, { lat: 28.620, lng: 77.320 },
    { lat: 28.615, lng: 77.280 }, { lat: 28.640, lng: 77.270 },
  ],
  new_delhi: [
    { lat: 28.640, lng: 77.195 }, { lat: 28.645, lng: 77.230 },
    { lat: 28.625, lng: 77.250 }, { lat: 28.600, lng: 77.245 },
    { lat: 28.590, lng: 77.220 }, { lat: 28.605, lng: 77.190 },
  ],
  north: [
    { lat: 28.770, lng: 77.080 }, { lat: 28.780, lng: 77.150 },
    { lat: 28.750, lng: 77.180 }, { lat: 28.720, lng: 77.170 },
    { lat: 28.715, lng: 77.120 }, { lat: 28.740, lng: 77.080 },
  ],
  north_east: [
    { lat: 28.730, lng: 77.220 }, { lat: 28.740, lng: 77.280 },
    { lat: 28.715, lng: 77.300 }, { lat: 28.695, lng: 77.280 },
    { lat: 28.690, lng: 77.240 }, { lat: 28.710, lng: 77.215 },
  ],
  north_west: [
    { lat: 28.720, lng: 77.020 }, { lat: 28.730, lng: 77.080 },
    { lat: 28.710, lng: 77.110 }, { lat: 28.680, lng: 77.100 },
    { lat: 28.670, lng: 77.060 }, { lat: 28.690, lng: 77.020 },
  ],
  old_delhi: [
    { lat: 28.670, lng: 77.200 }, { lat: 28.680, lng: 77.235 },
    { lat: 28.665, lng: 77.250 }, { lat: 28.650, lng: 77.240 },
    { lat: 28.648, lng: 77.210 }, { lat: 28.658, lng: 77.195 },
  ],
  outer_north: [
    { lat: 28.830, lng: 77.050 }, { lat: 28.840, lng: 77.120 },
    { lat: 28.815, lng: 77.150 }, { lat: 28.790, lng: 77.130 },
    { lat: 28.785, lng: 77.080 }, { lat: 28.805, lng: 77.045 },
  ],
  south: [
    { lat: 28.570, lng: 77.170 }, { lat: 28.575, lng: 77.230 },
    { lat: 28.545, lng: 77.245 }, { lat: 28.520, lng: 77.225 },
    { lat: 28.515, lng: 77.190 }, { lat: 28.540, lng: 77.165 },
  ],
  south_east: [
    { lat: 28.580, lng: 77.240 }, { lat: 28.585, lng: 77.290 },
    { lat: 28.555, lng: 77.300 }, { lat: 28.530, lng: 77.285 },
    { lat: 28.525, lng: 77.250 }, { lat: 28.555, lng: 77.235 },
  ],
  south_west: [
    { lat: 28.590, lng: 77.020 }, { lat: 28.600, lng: 77.090 },
    { lat: 28.570, lng: 77.120 }, { lat: 28.540, lng: 77.110 },
    { lat: 28.520, lng: 77.060 }, { lat: 28.555, lng: 77.015 },
  ],
  west: [
    { lat: 28.700, lng: 77.010 }, { lat: 28.710, lng: 77.060 },
    { lat: 28.695, lng: 77.090 }, { lat: 28.670, lng: 77.080 },
    { lat: 28.660, lng: 77.040 }, { lat: 28.675, lng: 77.010 },
  ],
};

interface DistrictScore {
  district_id: string;
  score: number;
  grade: string;
  report_count: number;
  population_density: number;
  total_population: number;
  budget_total_lakhs: number;
  breakdown: {
    report_pressure: number;
    density_pressure: number;
    budget_adequacy: number;
  };
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#DC2626';    // red-600
  if (score >= 60) return '#EA580C';    // orange-600
  if (score >= 40) return '#D97706';    // amber-600
  if (score >= 20) return '#65A30D';    // lime-600
  return '#16A34A';                      // green-600
}

function getScoreOpacity(score: number): number {
  return 0.25 + (score / 100) * 0.45;
}

function formatDistrict(id: string): string {
  return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// Renders google.maps.Polygon instances on the map
const DistrictPolygon = ({
  paths,
  fillColor,
  fillOpacity,
  isSelected,
  onClick,
  onMouseOver,
  onMouseOut,
}: {
  paths: { lat: number; lng: number }[];
  fillColor: string;
  fillOpacity: number;
  isSelected?: boolean;
  onClick?: () => void;
  onMouseOver?: () => void;
  onMouseOut?: () => void;
}) => {
  const map = useMap();
  const polygonRef = useRef<google.maps.Polygon | null>(null);

  useEffect(() => {
    if (!map) return;
    
    const activeStrokeWeight = isSelected ? 4 : 2;
    const activeStrokeColor = isSelected ? '#34D399' : '#FFFFFF';
    const activeOpacity = isSelected ? fillOpacity + 0.3 : fillOpacity;

    polygonRef.current = new google.maps.Polygon({
      paths,
      fillColor,
      fillOpacity: activeOpacity,
      strokeColor: activeStrokeColor,
      strokeWeight: activeStrokeWeight,
      strokeOpacity: 0.9,
      map,
    });

    const listeners: google.maps.MapsEventListener[] = [];
    if (onClick) listeners.push(polygonRef.current.addListener('click', onClick));
    
    if (onMouseOver) {
      listeners.push(polygonRef.current.addListener('mouseover', () => {
        if (!isSelected) {
          polygonRef.current?.setOptions({ strokeWeight: 3, strokeColor: '#F0F0F0', fillOpacity: fillOpacity + 0.15 });
        }
        onMouseOver();
      }));
    }
    
    if (onMouseOut) {
      listeners.push(polygonRef.current.addListener('mouseout', () => {
        if (!isSelected) {
          polygonRef.current?.setOptions({ strokeWeight: activeStrokeWeight, strokeColor: activeStrokeColor, fillOpacity: activeOpacity });
        }
        onMouseOut();
      }));
    }
    
    return () => {
      listeners.forEach(l => google.maps.event.removeListener(l));
      polygonRef.current?.setMap(null);
    };
  }, [map, fillColor, fillOpacity, isSelected]);

  return null;
};

// Helper for robust string normalization to match backend IDs to GeoJSON feature names
const normalizeId = (id: string) => {
  if (!id) return '';
  return id
    .toLowerCase()
    .replace(/[^\w\s]/gi, '')
    .replace(/\s+/g, '_')
    .replace(/_delhi$/, ''); // Optional: handles 'north_west_delhi' vs 'north_west' if needed
};

export const DeficiencyMap = () => {
  const [districts, setDistricts] = useState<DistrictScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictScore | null>(null);
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>('');

  const fetchScores = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/deficiency-map`);
      const data = await res.json();
      setDistricts(data.districts || []);
      setDataSource(data.source || 'unknown');
    } catch (e) {
      console.error('Failed to fetch deficiency scores', e);
      setDistricts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchScores(); }, [fetchScores]);

  const avgScore = districts.length > 0
    ? (districts.reduce((sum, d) => sum + d.score, 0) / districts.length).toFixed(1)
    : '0';

  const maxDistrict = districts.length > 0
    ? districts.reduce((max, d) => d.score > max.score ? d : max)
    : null;

  return (
    <div className="w-full h-full relative">
      <Map
        mapId="DEFICIENCY_MAP_ID"
        defaultCenter={{ lat: 28.6139, lng: 77.1500 }}
        defaultZoom={11}
        gestureHandling={'greedy'}
        disableDefaultUI={true}
        colorScheme={'DARK'}
      >
        {districts.map(d => {
          // Robust token matching
          const normalizedInputId = normalizeId(d.district_id);
          const matchedKey = Object.keys(DISTRICT_BOUNDARIES).find(
            key => normalizeId(key) === normalizedInputId
          );
          
          const paths = matchedKey ? DISTRICT_BOUNDARIES[matchedKey as keyof typeof DISTRICT_BOUNDARIES] : undefined;
          
          if (!paths) return null;
          return (
            <DistrictPolygon
              key={d.district_id}
              paths={paths}
              fillColor={getScoreColor(d.score)}
              fillOpacity={getScoreOpacity(d.score)}
              isSelected={selectedDistrict?.district_id === d.district_id}
              onClick={() => setSelectedDistrict(d)}
              onMouseOver={() => setHoveredDistrict(d.district_id)}
              onMouseOut={() => setHoveredDistrict(null)}
            />
          );
        })}
      </Map>

      {/* Header Badge */}
      <div className="absolute top-6 left-6 z-20 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-xl shadow-2xl px-5 py-3 flex items-center gap-3">
        <div className="w-10 h-10 bg-gradient-to-br from-rose-500 to-orange-500 rounded-lg flex items-center justify-center shadow-lg">
          <BarChart3 className="text-white" size={22} />
        </div>
        <div>
          <h2 className="text-sm font-bold text-slate-100">Infrastructure Deficiency Map</h2>
          <p className="text-[10px] text-slate-400">
            {dataSource === 'mock' ? 'Demo Data' : 'Live Firestore'} · {districts.length} Districts
          </p>
        </div>
        <button
          onClick={fetchScores}
          disabled={loading}
          className="ml-4 p-2 text-slate-400 hover:text-emerald-400 transition-colors rounded-lg hover:bg-slate-800"
          title="Refresh Scores"
        >
          <RefreshCw className={`${loading ? 'animate-spin' : ''}`} size={16} />
        </button>
      </div>

      {/* Legend */}
      <div className="absolute bottom-6 left-6 z-20 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-xl shadow-2xl p-4 w-56">
        <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Deficiency Scale</h4>
        <div className="space-y-2">
          {[
            { label: 'Critical (80–100)', color: '#DC2626' },
            { label: 'Severe (60–79)', color: '#EA580C' },
            { label: 'Moderate (40–59)', color: '#D97706' },
            { label: 'Adequate (20–39)', color: '#65A30D' },
            { label: 'Well-Funded (0–19)', color: '#16A34A' },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <div className="w-4 h-3 rounded-sm" style={{ backgroundColor: item.color, opacity: 0.8 }} />
              <span className="text-[11px] text-slate-300">{item.label}</span>
            </div>
          ))}
        </div>

        {/* Quick stats */}
        <div className="mt-4 pt-3 border-t border-slate-800 space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-[10px] text-slate-500">City Average</span>
            <span className="text-sm font-bold text-slate-200">{avgScore}</span>
          </div>
          {maxDistrict && (
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-slate-500">Worst District</span>
              <span className="text-[11px] font-semibold text-red-400">{formatDistrict(maxDistrict.district_id)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Hover tooltip */}
      {hoveredDistrict && !selectedDistrict && (
        <div className="absolute top-20 right-6 z-20 bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-lg shadow-xl px-4 py-3 animate-fade-in">
          <p className="text-sm font-semibold text-slate-100">{formatDistrict(hoveredDistrict)}</p>
          {(() => {
            const d = districts.find(x => x.district_id === hoveredDistrict);
            if (!d) return null;
            return (
              <div className="flex items-center gap-2 mt-1">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getScoreColor(d.score) }} />
                <span className="text-xs text-slate-300">Score: <strong>{d.score}</strong> ({d.grade})</span>
              </div>
            );
          })()}
        </div>
      )}

      {/* Detail Panel */}
      <div className="absolute top-6 right-6 w-[380px] max-h-[calc(100%-3rem)] overflow-y-auto custom-scrollbar bg-slate-900/95 backdrop-blur-md border border-slate-700 rounded-xl shadow-2xl p-5 z-20 animate-fade-in">
        {!selectedDistrict ? (
          <div className="flex flex-col items-center justify-center h-48 text-center opacity-70">
            <BarChart3 className="text-slate-400 mb-4" size={32} />
            <p className="text-sm font-medium text-slate-300">
              Click a district on the map to view infrastructure analytics.
            </p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex justify-between items-start mb-5">
              <div>
                <h3 className="text-lg font-bold text-slate-100">{formatDistrict(selectedDistrict.district_id)}</h3>
                <p className="text-xs text-slate-400 mt-0.5">Infrastructure Deficiency Analysis</p>
              </div>
              <button onClick={() => setSelectedDistrict(null)} className="text-slate-500 hover:text-slate-300 text-lg transition-colors">✕</button>
            </div>

            {/* Score Ring */}
            <div className="flex items-center gap-5 mb-6 p-4 rounded-xl border border-slate-800 bg-slate-950">
              <div className="relative w-20 h-20 shrink-0">
                <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="#1e293b" strokeWidth="3" />
                  <circle
                    cx="18" cy="18" r="15.9" fill="none"
                    stroke={getScoreColor(selectedDistrict.score)}
                    strokeWidth="3"
                    strokeDasharray={`${selectedDistrict.score}, 100`}
                    strokeLinecap="round"
                    className="transition-all duration-1000"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-xl font-black text-slate-100">{selectedDistrict.score}</span>
                </div>
              </div>
              <div>
                <span
                  className="text-sm font-bold px-3 py-1 rounded-full"
                  style={{
                    backgroundColor: getScoreColor(selectedDistrict.score) + '20',
                    color: getScoreColor(selectedDistrict.score),
                    border: `1px solid ${getScoreColor(selectedDistrict.score)}40`
                  }}
                >
                  {selectedDistrict.grade}
                </span>
                <p className="text-[10px] text-slate-500 mt-2">
                  Higher scores indicate greater infrastructure deficiency relative to citizen demand.
                </p>
              </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 gap-3 mb-5">
              <MetricCard icon={<AlertTriangle size={14} />} label="Reports (30d)" value={String(selectedDistrict.report_count)} color="text-amber-400" />
              <MetricCard icon={<Users size={14} />} label="Pop. Density" value={`${selectedDistrict.population_density.toLocaleString()}/km²`} color="text-blue-400" />
              <MetricCard 
                icon={<IndianRupee size={14} />} 
                label="Budget" 
                value={new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(selectedDistrict.budget_total_lakhs * 100000)} 
                color="text-emerald-400" 
              />
              <MetricCard icon={<TrendingUp size={14} />} label="Population" value={selectedDistrict.total_population.toLocaleString()} color="text-purple-400" />
            </div>

            {/* Breakdown Bars */}
            <div className="space-y-3 p-4 rounded-xl border border-slate-800 bg-slate-950">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Score Breakdown</h4>
              <BreakdownBar label="Report Pressure" value={selectedDistrict.breakdown.report_pressure} weight="45%" color="#EF4444" />
              <BreakdownBar label="Density Pressure" value={selectedDistrict.breakdown.density_pressure} weight="30%" color="#F59E0B" />
              <BreakdownBar label="Budget Adequacy" value={selectedDistrict.breakdown.budget_adequacy} weight="−25%" color="#22C55E" inverted />
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 text-[9px] text-slate-600 text-center">
              Score = 0.45 × Reports + 0.30 × Density − 0.25 × Budget
            </div>
          </>
        )}
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 z-30 bg-slate-950/60 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="animate-spin text-emerald-400" size={32} />
            <span className="text-sm text-slate-300 font-mono">Loading district scores...</span>
          </div>
        </div>
      )}
    </div>
  );
};

// --- Sub-components ---

const MetricCard = ({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) => (
  <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
    <div className={`flex items-center gap-1.5 mb-1 ${color}`}>
      {icon}
      <span className="text-[10px] font-semibold uppercase tracking-wider">{label}</span>
    </div>
    <p className="text-lg font-bold text-slate-100">{value}</p>
  </div>
);

const BreakdownBar = ({ label, value, weight, color, inverted }: { label: string; value: number; weight: string; color: string; inverted?: boolean }) => (
  <div>
    <div className="flex justify-between items-center mb-1">
      <span className="text-[11px] text-slate-300">{label}</span>
      <span className="text-[10px] text-slate-500 font-mono">w={weight} · {(value * 100).toFixed(0)}%</span>
    </div>
    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{
          width: `${value * 100}%`,
          backgroundColor: color,
          opacity: inverted ? 0.6 : 0.85,
        }}
      />
    </div>
  </div>
);

export default DeficiencyMap;
