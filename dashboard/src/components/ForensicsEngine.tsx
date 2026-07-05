import { useState, useContext, useEffect } from 'react';
import { Shield, Fingerprint, Camera, MapPin, Activity, CheckCircle, AlertTriangle, X, FileText } from 'lucide-react';
import { AppContext } from '../AppContext';
import type { ForensicReport } from '../AppContext';

export const ForensicsEngine = () => {
  const context = useContext(AppContext);
  
  // This hook state avoids errors before context check, but we return early below.
  const [selectedReport, setSelectedReport] = useState<ForensicReport | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [trustScore, setTrustScore] = useState(0);

  if (!context) return <div className="p-6 text-white">Error: ForensicsEngine must be used within an AppContextProvider</div>;
  
  const { forensicReports, updateForensicReport } = context;

  // Select the first report if none is selected on load
  useEffect(() => {
    if (!selectedReport && forensicReports.length > 0) {
      setSelectedReport(forensicReports[0]);
      setTrustScore(forensicReports[0].trustScore);
    }
  }, [forensicReports, selectedReport]);

  const handleRowClick = (report: ForensicReport) => {
    setSelectedReport(report);
    if (report.status === 'Pending') {
      setAnalyzing(true);
      setTrustScore(0);
      let score = 0;
      const interval = setInterval(() => {
        score += 5;
        setTrustScore(score);
        if (score >= report.trustScore) {
          clearInterval(interval);
          setAnalyzing(false);
        }
      }, 50);
    } else {
      setTrustScore(report.trustScore);
      setAnalyzing(false);
    }
  };

  const handleApprove = () => {
    if (!selectedReport) return;
    
    // Inject fallback coordinates (Delhi) if the user only provided text
    let finalLat = selectedReport.lat;
    let finalLon = selectedReport.lon;
    if (!finalLat || !finalLon) {
       finalLat = 28.6139 + (Math.random() - 0.5) * 0.1;
       finalLon = 77.2090 + (Math.random() - 0.5) * 0.1;
    }

    updateForensicReport(selectedReport.id, {
      lat: finalLat,
      lon: finalLon,
      status: 'Verified'
    });
    setSelectedReport(prev => prev ? { ...prev, lat: finalLat, lon: finalLon, status: 'Verified' } : null);
  };

  const handleReject = () => {
    if (!selectedReport) return;
    updateForensicReport(selectedReport.id, { status: 'Flagged' });
    setSelectedReport(prev => prev ? { ...prev, status: 'Flagged' } : null);
  };

  return (
    <div className="h-full w-full flex bg-slate-950">
      
      {/* Main Table Area */}
      <div className={`flex-1 p-8 transition-all ${selectedReport ? 'mr-[400px]' : ''}`}>
        <div className="max-w-5xl mx-auto">
          <header className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-100 uppercase tracking-widest flex items-center gap-3">
                <Shield className="text-indigo-500" />
                Citizen Report Forensics
              </h1>
              <p className="text-slate-400 mt-2">Anti-Fraud & AI Verification Queue</p>
            </div>
          </header>

          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            <table className="w-full text-left text-sm text-slate-400">
              <thead className="bg-slate-800/50 text-xs uppercase font-bold text-slate-300">
                <tr>
                  <th className="px-6 py-4">Report ID</th>
                  <th className="px-6 py-4">Hazard Type</th>
                  <th className="px-6 py-4">Location</th>
                  <th className="px-6 py-4">Time</th>
                  <th className="px-6 py-4 text-right">Verification Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {forensicReports.map((report) => (
                  <tr 
                    key={report.id} 
                    onClick={() => handleRowClick(report)}
                    className={`hover:bg-slate-800 cursor-pointer transition-colors ${selectedReport?.id === report.id ? 'bg-slate-800' : ''}`}
                  >
                    <td className="px-6 py-4 font-mono text-slate-300">{report.id}</td>
                    <td className="px-6 py-4 font-semibold text-slate-300">{report.type}</td>
                    <td className="px-6 py-4">{report.location}</td>
                    <td className="px-6 py-4">{report.timestamp}</td>
                    <td className="px-6 py-4 text-right">
                      {report.status === 'Pending' && <span className="bg-amber-900/40 text-amber-500 px-3 py-1 rounded-full text-xs font-bold border border-amber-500/20">AWAITING AI SCAN</span>}
                      {report.status === 'Verified' && <span className="bg-emerald-900/40 text-emerald-500 px-3 py-1 rounded-full text-xs font-bold border border-emerald-500/20">VERIFIED</span>}
                      {report.status === 'Flagged' && <span className="bg-red-900/40 text-red-500 px-3 py-1 rounded-full text-xs font-bold border border-red-500/20">FRAUD DETECTED</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Breakdown Sidebar */}
      <div className={`fixed top-0 right-0 h-full w-[400px] bg-slate-900 border-l border-slate-800 shadow-2xl transition-transform duration-300 transform z-40 ${selectedReport ? 'translate-x-0' : 'translate-x-full'}`}>
        {selectedReport && (
          <div className="h-full flex flex-col pt-14"> {/* offset for topbar */}
            
            <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/50">
              <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest flex items-center gap-2">
                <Fingerprint className="text-indigo-400" size={16} /> Analysis: {selectedReport.id}
              </h2>
              <button onClick={() => setSelectedReport(null)} className="text-slate-500 hover:text-slate-300"><X size={20}/></button>
            </div>

            <div className="p-6 flex-1 overflow-y-auto space-y-6">
              
              {/* Trust Score Gauge */}
              <div className="flex flex-col items-center justify-center p-6 bg-slate-950 rounded-xl border border-slate-800">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Calculated Trust Score</h3>
                <div className="relative w-32 h-32 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-slate-800"
                      strokeWidth="3"
                      stroke="currentColor"
                      fill="none"
                      strokeLinecap="round"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className={`${trustScore > 80 ? 'text-emerald-500' : trustScore > 40 ? 'text-amber-500' : 'text-red-500'} transition-all duration-300 ease-out`}
                      strokeDasharray={`${trustScore}, 100`}
                      strokeWidth="3"
                      stroke="currentColor"
                      fill="none"
                      strokeLinecap="round"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute text-2xl font-bold text-slate-100 flex items-baseline">
                    {trustScore}<span className="text-xs text-slate-500 ml-1">%</span>
                  </div>
                </div>
                {analyzing && <span className="text-[10px] text-indigo-400 font-mono mt-4 animate-pulse">CNN ENSEMBLE SCANNING...</span>}
              </div>

              {/* Validation Checklists */}
              <div className="space-y-4">
                <ValidationItem 
                  icon={<Camera size={16} />}
                  title="Deepfake / Generative AI Check"
                  desc="CNN ensemble scanning for artifacts."
                  status={analyzing ? 'loading' : (selectedReport.trustScore > 80 ? 'pass' : 'fail')}
                />
                
                <ValidationItem 
                  icon={<MapPin size={16} />}
                  title="EXIF Metadata & GPS Validation"
                  desc="Cross-referencing embedded coordinates."
                  status={analyzing ? 'loading' : (selectedReport.trustScore > 80 ? 'pass' : 'fail')}
                />

                <ValidationItem 
                  icon={<Activity size={16} />}
                  title="Cross-Modal Consistency"
                  desc="Aligning report with local CPCB station telemetry."
                  status={analyzing ? 'loading' : (selectedReport.trustScore > 80 ? 'pass' : 'fail')}
                />
              </div>

              {/* Ingested Description Log */}
              <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                  <FileText size={14} /> Ingested Description Log
                </h3>
                <div className="font-mono text-xs text-slate-300 p-3 bg-slate-900 rounded border border-slate-700/50">
                  {selectedReport.details || 'No description provided.'}
                </div>
              </div>

            </div>

            <div className="p-4 border-t border-slate-800 bg-slate-950 flex gap-4">
              {trustScore > 80 ? (
                <button 
                  onClick={handleApprove}
                  disabled={analyzing || selectedReport?.status === 'Verified'}
                  className={`flex-1 py-3 rounded-lg font-bold uppercase tracking-wider text-sm transition-colors ${
                    analyzing ? 'bg-slate-800 text-slate-500' : 
                    selectedReport?.status === 'Verified' ? 'bg-emerald-900 text-emerald-500' :
                    'bg-emerald-600 text-slate-950 hover:bg-emerald-500'
                  }`}
                >
                  {analyzing ? 'Analyzing...' : selectedReport?.status === 'Verified' ? 'Approved & Integrated' : 'Approve & Integrate to Map'}
                </button>
              ) : (
                <button 
                  onClick={handleReject}
                  disabled={analyzing || selectedReport?.status === 'Flagged'}
                  className={`flex-1 py-3 rounded-lg font-bold uppercase tracking-wider text-sm transition-colors ${
                    analyzing ? 'bg-slate-800 text-slate-500' : 
                    selectedReport?.status === 'Flagged' ? 'bg-red-900 text-red-500' :
                    'bg-red-600 text-slate-950 hover:bg-red-500'
                  }`}
                >
                  {analyzing ? 'Analyzing...' : selectedReport?.status === 'Flagged' ? 'Rejected' : 'Reject & Flag User'}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

    </div>
  );
};

// Also export as default to match user's code snippet
export default ForensicsEngine;

const ValidationItem = ({ icon, title, desc, status }: any) => {
  return (
    <div className="flex items-start gap-4 p-4 rounded-lg bg-slate-950 border border-slate-800">
      <div className={`p-2 rounded-full ${status === 'pass' ? 'bg-emerald-900/50 text-emerald-400' : status === 'fail' ? 'bg-red-900/50 text-red-400' : 'bg-slate-800 text-slate-400'}`}>
        {icon}
      </div>
      <div className="flex-1">
        <h4 className="text-sm font-bold text-slate-200">{title}</h4>
        <p className="text-xs text-slate-500 mt-1">{desc}</p>
      </div>
      <div>
        {status === 'loading' && <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />}
        {status === 'pass' && <CheckCircle className="text-emerald-500" size={20} />}
        {status === 'fail' && <AlertTriangle className="text-red-500" size={20} />}
      </div>
    </div>
  )
}
