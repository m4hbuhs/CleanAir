import { X, BrainCircuit, ActivitySquare, Wrench } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { Incident, Station } from '../types';

interface Props {
  incident: Incident;
  onClose: () => void;
  stations: Station[];
}

export const ActionPanel = ({ incident, onClose, stations }: Props) => {
  // Find nearest station for the forecast decay curve
  let nearestStation = stations[0];
  let minDist = Infinity;
  stations.forEach(s => {
    const dist = Math.pow(s.lat - incident.lat, 2) + Math.pow(s.lon - incident.lon, 2);
    if (dist < minDist) {
      minDist = dist;
      nearestStation = s;
    }
  });

  const forecastData = nearestStation?.forecast_24h.map((val, idx) => ({
    hour: `+${idx}h`,
    pm25: Math.round(val)
  })) || [];

  return (
    <div className="bg-slate-800/95 backdrop-blur border-t border-slate-700 p-6 shadow-2xl relative animate-in slide-in-from-bottom-10 fade-in duration-300">
      <button 
        onClick={onClose}
        className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition-colors bg-slate-700/50 p-1.5 rounded-full"
      >
        <X size={20} />
      </button>

      <div className="flex items-center space-x-3 mb-6">
        <ActivitySquare className="text-indigo-400" size={28} />
        <h2 className="text-xl font-bold text-slate-100">
          Incident Analysis: {incident.id}
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* SHAP EXPLANATION */}
        <div className="col-span-1 space-y-3">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <BrainCircuit size={16} /> Explainable AI (SHAP)
          </h3>
          <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50 text-slate-300 text-sm leading-relaxed">
            {incident.explanation}
          </div>
        </div>

        {/* PRESCRIPTIVE COMMAND CARD */}
        <div className="col-span-1 space-y-3">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <Wrench size={16} /> Prescriptive Action
          </h3>
          <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-100 flex flex-col justify-between h-full">
            <div>
              <div className="text-sm font-bold text-emerald-400 mb-1">COMMAND DIRECTIVE:</div>
              <div className="text-sm mb-4 font-medium">{incident.command}</div>
              
              <div className="text-xs text-emerald-400/80 mb-2 uppercase tracking-wide">Resources:</div>
              <ul className="space-y-1 mb-4">
                {incident.resources.map((r, i) => (
                  <li key={i} className="text-xs flex items-center bg-emerald-900/40 px-2 py-1 rounded w-max">
                    <span className="font-bold mr-2 text-emerald-300">{r.quantity}x</span> {r.type}
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="text-xs bg-emerald-900/60 px-3 py-2 rounded border border-emerald-700/50 text-emerald-200">
              <span className="font-bold">Impact:</span> {incident.expected_reduction}
            </div>
          </div>
        </div>

        {/* 24H PREDICTIVE CURVE */}
        <div className="col-span-1 space-y-3">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">
            24H Mitigation Trajectory
          </h3>
          <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-700/50 h-[180px] w-full">
            {forecastData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecastData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="hour" stroke="#64748b" fontSize={10} tickMargin={5} />
                  <YAxis stroke="#64748b" fontSize={10} domain={['dataMin - 10', 'auto']} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '6px', fontSize: '12px' }}
                    itemStyle={{ color: '#818cf8' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="pm25" 
                    name="PM2.5"
                    stroke="#818cf8" 
                    strokeWidth={3}
                    dot={false}
                    activeDot={{ r: 6, fill: '#6366f1', stroke: '#fff', strokeWidth: 2 }} 
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500 text-sm">
                No forecast data available
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
