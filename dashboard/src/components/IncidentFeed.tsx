import { useState } from 'react';
import { Camera, MapPin, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import type { Incident } from '../types';

interface Props {
  incidents: Incident[];
  selectedIncidentId?: string;
  onSelectIncident: (incident: Incident) => void;
}

export const IncidentFeed = ({ incidents, selectedIncidentId, onSelectIncident }: Props) => {
  const [activeTab, setActiveTab] = useState<'verified' | 'manual'>('verified');

  const verified = incidents.filter(i => i.trust_score >= 75);
  const manual = incidents.filter(i => i.trust_score < 75);

  const displayList = activeTab === 'verified' ? verified : manual;

  return (
    <div className="flex flex-col h-full bg-slate-900 overflow-hidden">
      {/* TABS */}
      <div className="flex border-b border-slate-700 bg-slate-800">
        <button 
          onClick={() => setActiveTab('verified')}
          className={`flex-1 py-3 text-sm font-semibold transition-colors ${activeTab === 'verified' ? 'text-emerald-400 border-b-2 border-emerald-400 bg-emerald-900/10' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'}`}
        >
          Verified Alerts ({verified.length})
        </button>
        <button 
          onClick={() => setActiveTab('manual')}
          className={`flex-1 py-3 text-sm font-semibold transition-colors ${activeTab === 'manual' ? 'text-amber-400 border-b-2 border-amber-400 bg-amber-900/10' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'}`}
        >
          Manual Review ({manual.length})
        </button>
      </div>

      {/* LIST */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {displayList.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-slate-500">
            <CheckCircle2 size={32} className="mb-2 opacity-50" />
            <p>No incidents in this queue.</p>
          </div>
        ) : (
          displayList.map(inc => {
            const isSelected = selectedIncidentId === inc.id;
            const scoreColor = inc.trust_score >= 75 ? 'bg-emerald-500' : inc.trust_score >= 50 ? 'bg-amber-500' : 'bg-red-500';
            const textScoreColor = inc.trust_score >= 75 ? 'text-emerald-400' : inc.trust_score >= 50 ? 'text-amber-400' : 'text-red-400';
            
            return (
              <div 
                key={inc.id}
                onClick={() => onSelectIncident(inc)}
                className={`p-4 rounded-lg border transition-all cursor-pointer ${isSelected ? 'bg-slate-800 border-indigo-500 shadow-md shadow-indigo-900/20' : 'bg-slate-800/50 border-slate-700 hover:border-slate-500 hover:bg-slate-800'}`}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-sm tracking-wide text-slate-200 flex items-center gap-2">
                    {inc.trust_score >= 75 ? <AlertTriangle size={16} className="text-emerald-500" /> : <AlertTriangle size={16} className="text-amber-500" />}
                    {inc.id} - {inc.type.replace('_', ' ').toUpperCase()}
                  </h3>
                  <span className="text-xs text-slate-500 font-mono">{new Date(inc.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                </div>

                {/* TRUST SCORE BAR */}
                <div className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Forensic Trust</span>
                    <span className={`font-bold ${textScoreColor}`}>{inc.trust_score.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden">
                    <div className={`h-full ${scoreColor} transition-all duration-500`} style={{ width: `${inc.trust_score}%` }}></div>
                  </div>
                </div>

                {/* BADGES */}
                <div className="flex space-x-3 text-xs">
                  <div className={`flex items-center space-x-1 px-2 py-1 rounded ${inc.exif_match ? 'bg-emerald-900/30 text-emerald-300' : 'bg-slate-700/50 text-slate-400'}`}>
                    <Camera size={12} />
                    <span>EXIF</span>
                    {inc.exif_match ? <CheckCircle2 size={12} className="ml-1 text-emerald-500" /> : <XCircle size={12} className="ml-1 text-slate-500" />}
                  </div>
                  <div className={`flex items-center space-x-1 px-2 py-1 rounded ${inc.telemetry_match ? 'bg-emerald-900/30 text-emerald-300' : 'bg-slate-700/50 text-slate-400'}`}>
                    <MapPin size={12} />
                    <span>Telemetry</span>
                    {inc.telemetry_match ? <CheckCircle2 size={12} className="ml-1 text-emerald-500" /> : <XCircle size={12} className="ml-1 text-slate-500" />}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  );
};
