import React, { useState } from 'react';
import { BrainCircuit, Wrench, Siren, Radio, PhoneCall, CheckCircle2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useAppContext } from '../AppContext';

const FORECAST_DATA = Array.from({length: 24}, (_, i) => ({
  hour: `+${i}h`,
  pm25: Math.max(10, 310 - i * 12.5) // Rapid decay simulating mitigation
}));

export const AdminCommandCenter = () => {
  const [deployState, setDeployState] = useState<'idle' | 'deploying' | 'deployed'>('idle');
  const [alertState, setAlertState] = useState<'idle' | 'sending' | 'sent'>('idle');
  const [ivrState, setIvrState] = useState<'idle' | 'triggering' | 'triggered'>('idle');

  const { setGlobalAlert } = useAppContext();

  const handleDeploy = () => {
    setDeployState('deploying');
    setTimeout(() => {
      setDeployState('deployed');
      setGlobalAlert("⚠️ Command directive executed: Dispatched 1 Fire Crew + 2 Mist Cannons to Maple St. ETA 12 mins.");
    }, 1500);
  };

  const handleAlerts = () => {
    setAlertState('sending');
    setTimeout(() => {
      setAlertState('sent');
      setGlobalAlert("⚠️ Broadcasting Mobile Advisory: Pushed hazard notification to 8,402 active devices in Sector 4.");
    }, 1500);
  };

  const handleIVR = () => {
    setIvrState('triggering');
    setTimeout(() => {
      setIvrState('triggered');
      setGlobalAlert("⚠️ Dispatching automated IVR alert call to 412 residents in affected grid zone...");
    }, 1500);
  };

  return (
    <div className="h-full w-full p-8 overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto space-y-6">
        
        <header className="mb-8">
          <h1 className="text-2xl font-bold text-slate-100 uppercase tracking-widest flex items-center gap-3">
            <Siren className="text-red-500" />
            Active Crisis Response
          </h1>
          <p className="text-slate-400 mt-2">Managing Incident INC-001 (Maple St. Grid)</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* XAI Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-6">
              <BrainCircuit className="text-indigo-400" size={18} />
              Explainable AI (SHAP) Attribution
            </h2>
            
            <div className="space-y-4">
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-300 font-semibold">Garbage Burning</span>
                  <span className="text-red-400 font-bold">45%</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 rounded-full" style={{ width: '45%' }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-300 font-semibold">Calm Wind (Stagnation)</span>
                  <span className="text-amber-400 font-bold">30%</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: '30%' }} />
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-300 font-semibold">Industrial Plume (Adjacent)</span>
                  <span className="text-indigo-400 font-bold">25%</span>
                </div>
                <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full" style={{ width: '25%' }} />
                </div>
              </div>
            </div>

            <p className="mt-6 text-sm text-slate-500 bg-slate-950 p-3 rounded-lg border border-slate-800">
              <strong className="text-slate-300">AI Conclusion:</strong> High PM2.5 spike is driven primarily by an illegal garbage burning event, exacerbated by zero wind dispersion in the sector.
            </p>
          </div>

          {/* Prescriptive Dispatch */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-6">
              <Wrench className="text-emerald-400" size={18} />
              Prescriptive Deployment Plan
            </h2>
            
            <div className="bg-emerald-950/30 border border-emerald-500/30 p-4 rounded-lg mb-6 flex-1">
              <p className="text-emerald-100 text-lg mb-4">
                Garbage fire detected at Maple St. Predicted AQI = <span className="font-bold text-red-400">310</span> in 2h.
              </p>
              
              <div className="mb-4">
                <span className="text-xs font-bold text-emerald-500 uppercase tracking-wider">Recommended Deployment:</span>
                <ul className="mt-2 space-y-2">
                  <li className="flex items-center text-emerald-200 bg-emerald-900/40 px-3 py-2 rounded-lg">
                    <span className="font-bold mr-3 text-emerald-400">1x</span> Fire Suppression Crew
                  </li>
                  <li className="flex items-center text-emerald-200 bg-emerald-900/40 px-3 py-2 rounded-lg">
                    <span className="font-bold mr-3 text-emerald-400">2x</span> Mobile Mist Cannons
                  </li>
                </ul>
              </div>
              
              <div className="bg-emerald-900/60 p-3 rounded-lg border border-emerald-500/20 text-emerald-300 font-medium text-sm flex justify-between items-center">
                <span>Expected PM2.5 Reduction:</span>
                <span className="text-xl font-bold text-emerald-400">- 25%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Dispatch Action Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6">Command Directives (Execute)</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button 
              onClick={handleDeploy}
              disabled={deployState !== 'idle'}
              className={`p-4 rounded-xl flex items-center justify-center gap-3 font-bold transition-all ${
                deployState === 'idle' ? 'bg-emerald-600 hover:bg-emerald-500 text-slate-950' :
                deployState === 'deploying' ? 'bg-emerald-900 text-emerald-500' : 'bg-slate-800 text-emerald-500 border border-emerald-500/30'
              }`}
            >
              {deployState === 'idle' ? <><Wrench /> Deploy Crew</> :
               deployState === 'deploying' ? 'Deploying...' : <><CheckCircle2 /> Crew Dispatched</>}
            </button>

            <button 
              onClick={handleAlerts}
              disabled={alertState !== 'idle'}
              className={`p-4 rounded-xl flex items-center justify-center gap-3 font-bold transition-all ${
                alertState === 'idle' ? 'bg-amber-600 hover:bg-amber-500 text-slate-950' :
                alertState === 'sending' ? 'bg-amber-900 text-amber-500' : 'bg-slate-800 text-amber-500 border border-amber-500/30'
              }`}
            >
              {alertState === 'idle' ? <><Radio /> Send Mobile Advisory Alerts</> :
               alertState === 'sending' ? 'Broadcasting...' : <><CheckCircle2 /> Alerts Sent</>}
            </button>

            <button 
              onClick={handleIVR}
              disabled={ivrState !== 'idle'}
              className={`p-4 rounded-xl flex items-center justify-center gap-3 font-bold transition-all ${
                ivrState === 'idle' ? 'bg-indigo-600 hover:bg-indigo-500 text-slate-950' :
                ivrState === 'triggering' ? 'bg-indigo-900 text-indigo-500' : 'bg-slate-800 text-indigo-500 border border-indigo-500/30'
              }`}
            >
              {ivrState === 'idle' ? <><PhoneCall /> Trigger IVR Automated Calls</> :
               ivrState === 'triggering' ? 'Calling...' : <><CheckCircle2 /> Calls Triggered</>}
            </button>
          </div>
        </div>

        {/* 24H Mitigation Chart */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl h-64">
           <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6">24H Simulated Mitigation Trajectory</h2>
           <ResponsiveContainer width="100%" height="100%">
              <LineChart data={FORECAST_DATA} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="hour" stroke="#475569" fontSize={12} tickMargin={10} />
                <YAxis stroke="#475569" fontSize={12} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                  itemStyle={{ color: '#10b981' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="pm25" 
                  name="Projected PM2.5"
                  stroke="#10b981" 
                  strokeWidth={3}
                  dot={false}
                  activeDot={{ r: 6, fill: '#10b981', stroke: '#0f172a', strokeWidth: 2 }} 
                />
              </LineChart>
            </ResponsiveContainer>
        </div>

      </div>
    </div>
  );
};
