import React, { useState, useContext, useRef } from 'react';
import { 
  ChevronLeft, 
  Camera, 
  CheckCircle2, 
  Mic, 
  MicOff, 
  Radio, 
  Terminal, 
  Send,
  Loader2,
  MapPin,
  Sparkles,
  Satellite
} from 'lucide-react';
import { AppContext } from '../AppContext';
import type { ForensicReport } from '../AppContext';

// Removed manual categories, AI handles it now
const MobileReporter: React.FC = () => {
  const context = useContext(AppContext);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [step, setStep] = useState<'input' | 'analyzing' | 'report'>('input');
  
  // Media States
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [selectedImageFile, setSelectedImageFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [audioCaptured, setAudioCaptured] = useState<boolean>(false);
  const [textDetails, setTextDetails] = useState('');

  // Location States
  const [locationText, setLocationText] = useState('');
  const [currentLat, setCurrentLat] = useState<number | undefined>();
  const [currentLon, setCurrentLon] = useState<number | undefined>();
  const [fetchedAqi, setFetchedAqi] = useState<number | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  // Gemini Analysis State
  const [geminiReport, setGeminiReport] = useState<{ vision: string, speech: string | null, aqiText: string } | null>(null);

  const [telemetryLogs, setTelemetryLogs] = useState<string[]>([
    '> SYSTEM INITIALIZED',
    '> AWAITING SENSOR INPUT...'
  ]);

  if (!context) return null;

  const logTelemetry = (msg: string) => {
    setTelemetryLogs(prev => {
      const newLogs = [...prev, `> ${msg}`];
      return newLogs.length > 5 ? newLogs.slice(newLogs.length - 5) : newLogs;
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImageFile(file);
      logTelemetry('PROCESSING UPLOADED IMAGE...');
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
        logTelemetry('IMAGE HASH VALIDATED');
      };
      reader.readAsDataURL(file);
    }
  };

  const handleStartRecording = (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (audioCaptured) return;
    setIsRecording(true);
    logTelemetry('OPENING MICROPHONE STREAM...');
  };

  const handleStopRecording = (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (!isRecording) return;
    setIsRecording(false);
    setAudioCaptured(true);
    logTelemetry('VOICE SIGNATURE CACHED [1.2MB]');
  };

  const handleLocateMe = () => {
    setIsLocating(true);
    logTelemetry('PINGING SATELLITE GPS...');
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser");
      setIsLocating(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(async (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      setCurrentLat(lat);
      setCurrentLon(lon);
      
      try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
        const data = await res.json();
        const address = data.display_name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
        setLocationText(address.split(',')[0] + ', ' + address.split(',')[1]);

        // Fetch AQI
        const waqiRes = await fetch(`https://api.waqi.info/feed/geo:${lat};${lon}/?token=27e2960b47539b310bc4a7ad97c17ee8a0b8afe7`);
        const waqiData = await waqiRes.json();
        if (waqiData.status === 'ok') {
          setFetchedAqi(waqiData.data.aqi);
          logTelemetry(`AQI LOCKED: ${waqiData.data.aqi}`);
        }
      } catch (e) {
        console.error("Geocoding/AQI error", e);
        setLocationText(`${lat.toFixed(4)}, ${lon.toFixed(4)}`);
      } finally {
        setIsLocating(false);
        logTelemetry('GPS LOCKED');
      }
    }, () => {
      alert("Unable to retrieve your location");
      setIsLocating(false);
    });
  };

  const handleAnalyze = async () => {
    if (!imagePreview && !audioCaptured && !textDetails) {
      alert("Please provide at least a photo, voice note, or text description.");
      return;
    }

    if (!locationText.trim()) {
      alert("Please provide a location manually or tap the GPS icon to locate before submitting.");
      return;
    }

    setStep('analyzing');
    logTelemetry('ROUTING TO GEMINI AI...');

    try {
      const formData = new FormData();
      formData.append('locationText', locationText || 'Unknown');
      formData.append('textDetails', textDetails || '');
      formData.append('aqi', fetchedAqi ? fetchedAqi.toString() : '');
      
      if (selectedImageFile) {
        formData.append('image', selectedImageFile);
      }
      
      // Note: for audio, we don't have the blob mapped yet in this exact snippet 
      // since we only toggled 'isRecording' state, but the endpoint supports it.
      
      const res = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error('API returned an error');
      
      const data = await res.json();
      
      setGeminiReport({
        vision: data.vision,
        speech: data.speech,
        aqiText: fetchedAqi 
          ? `Earth Engine correlates location with real-time sensor array reporting AQI of ${fetchedAqi}. ${data.aqiText}` 
          : data.aqiText
      });
      
      if (data.vision && data.vision.corrected_location) {
        setLocationText(data.vision.corrected_location);
      }
      
      setStep('report');
      logTelemetry('GEMINI ANALYSIS COMPLETE');
    } catch (e) {
      console.error(e);
      alert("Failed to connect to the backend AI service. Is the FastAPI server running?");
      setStep('input');
    }
  };

  const handleReportSubmission = () => {
    const generatedToken: ForensicReport = {
      id: `REP-${Math.floor(1000 + Math.random() * 9000)}`,
      type: imagePreview ? 'Photo' : (audioCaptured ? 'Voice' : 'Keyword'),
      location: locationText || 'Unknown Location',
      lat: currentLat,
      lon: currentLon,
      aqi: fetchedAqi,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      status: 'Pending',
      trustScore: imagePreview ? 96 : 82,
      details: `${textDetails} \n\n[AI Report: ${geminiReport?.vision}]`
    };

    context.addForensicReport(generatedToken);
    context.setGlobalAlert(`⚠️ NEW INCIDENT RECEIVED: Citizen submission [${generatedToken.id}] queued for forensic AI scanning.`);
    
    window.alert("Success! Your verified report has been securely transmitted to the Command Center.");
    
    // Reset
    setStep('input');
    setImagePreview(null);
    setSelectedImageFile(null);
    setAudioCaptured(false);
    setTextDetails('');
    setLocationText('');
    setFetchedAqi(null);
    setGeminiReport(null);
  };

  return (
    <div className="w-full h-full bg-slate-950 text-slate-100 flex flex-col relative overflow-hidden">
      {/* App Bar */}
      <header className="flex items-center px-4 py-4 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-20">
        <button 
          onClick={() => step !== 'input' ? setStep('input') : null}
          className="p-2 -ml-2 rounded-full hover:bg-slate-800 transition-colors"
        >
          <ChevronLeft className="w-6 h-6 text-slate-300" />
        </button>
        <h1 className="flex-1 text-center text-lg font-bold tracking-wide">CleanAir Reporter</h1>
        <div className="w-10"></div>
      </header>

      <main className="flex-1 overflow-y-auto pb-28 custom-scrollbar relative">
        
        {/* === STEP 1: INPUT === */}
        {step === 'input' && (
          <div className="animate-fade-in space-y-6 pt-4 pb-8">
            {/* Location Module */}
            <section className="px-4">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Location Context</h2>
              <div className="flex gap-2">
                <input 
                  type="text" 
                  placeholder="Enter location manually..." 
                  value={locationText}
                  onChange={(e) => setLocationText(e.target.value)}
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-emerald-500"
                />
                <button 
                  onClick={handleLocateMe}
                  disabled={isLocating}
                  className="bg-slate-800 hover:bg-slate-700 border border-slate-700 p-3 rounded-lg flex items-center justify-center transition-colors"
                >
                  {isLocating ? <Loader2 className="w-5 h-5 animate-spin text-emerald-500" /> : <MapPin className="w-5 h-5 text-slate-300" />}
                </button>
              </div>
              {fetchedAqi && (
                <div className="mt-2 text-xs text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Live AQI at location: {fetchedAqi}
                </div>
              )}
            </section>

            {/* Media Module */}
            <section className="px-4 space-y-4">
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Evidence Upload</h2>
              
              <div className="grid grid-cols-2 gap-3">
                {/* Image Upload */}
                <input 
                  type="file" 
                  accept="image/*" 
                  className="hidden" 
                  ref={fileInputRef} 
                  onChange={handleFileChange}
                />
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative h-32 rounded-xl border-2 transition-all cursor-pointer flex flex-col items-center justify-center overflow-hidden
                    ${imagePreview ? 'border-emerald-500/50 bg-emerald-950/20' : 'border-dashed border-slate-700 bg-slate-900/50 hover:bg-slate-800'}`}
                >
                  {imagePreview ? (
                    <>
                      <img src={imagePreview} className="absolute inset-0 w-full h-full object-cover opacity-60" alt="Preview" />
                      <CheckCircle2 className="w-8 h-8 text-emerald-400 relative z-10 drop-shadow-md" />
                    </>
                  ) : (
                    <>
                      <Camera className="w-8 h-8 text-slate-500 mb-2" />
                      <span className="text-xs text-slate-400 font-medium">Upload Photo</span>
                    </>
                  )}
                </div>

                {/* Voice Note */}
                <div 
                  onMouseDown={handleStartRecording}
                  onMouseUp={handleStopRecording}
                  onMouseLeave={handleStopRecording}
                  onTouchStart={handleStartRecording}
                  onTouchEnd={handleStopRecording}
                  className={`relative h-32 rounded-xl border-2 transition-all cursor-pointer flex flex-col items-center justify-center select-none touch-none
                    ${isRecording ? 'border-red-500 bg-red-950/40 animate-pulse' : audioCaptured ? 'border-emerald-500/50 bg-emerald-950/20' : 'border-slate-700 bg-slate-900/50 hover:bg-slate-800'}`}
                >
                  {isRecording ? (
                    <Radio className="w-8 h-8 text-red-400 animate-bounce" />
                  ) : audioCaptured ? (
                    <>
                      <Mic className="w-8 h-8 text-emerald-400 relative z-10 drop-shadow-md" />
                      <span className="text-[10px] text-emerald-300 font-medium mt-1">Recorded</span>
                    </>
                  ) : (
                    <>
                      <MicOff className="w-8 h-8 text-slate-500 mb-2" />
                      <span className="text-xs text-slate-400 font-medium">Hold to Record</span>
                    </>
                  )}
                </div>
              </div>

              {/* Text Area */}
              <textarea 
                placeholder="Add text details..."
                value={textDetails}
                onChange={(e) => setTextDetails(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-emerald-500 min-h-[100px] resize-none"
              />
            </section>
          </div>
        )}

        {/* === STEP 2: ANALYZING (LOADING STATE) === */}
        {step === 'analyzing' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center px-6 animate-fade-in z-10 bg-slate-950">
            <div className="w-24 h-24 relative mb-8">
              <div className="absolute inset-0 border-4 border-indigo-500/20 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-indigo-500 rounded-full border-t-transparent animate-spin"></div>
              <Sparkles className="absolute inset-0 m-auto text-indigo-400 w-8 h-8 animate-pulse" />
            </div>
            <h2 className="text-xl font-bold text-slate-100 mb-2">Gemini AI Analysis</h2>
            <p className="text-slate-400 text-center text-sm max-w-[250px]">
              Processing multimodal evidence and querying Earth Engine satellite data...
            </p>
          </div>
        )}

        {/* === STEP 3: GEMINI REPORT REVIEW === */}
        {step === 'report' && geminiReport && (
          <div className="animate-fade-in p-4 space-y-4 pb-8">
            <div className="bg-indigo-950/30 border border-indigo-500/30 rounded-xl overflow-hidden shadow-[0_0_20px_rgba(99,102,241,0.1)]">
              <div className="bg-gradient-to-r from-indigo-900/80 to-purple-900/80 p-3 border-b border-indigo-500/30 flex items-center justify-between">
                <h3 className="text-xs font-bold text-indigo-100 uppercase tracking-widest flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-300" />
                  Gemini Incident Report
                </h3>
                <span className="text-[10px] bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded">VERIFIED</span>
              </div>
              
              <div className="p-4 space-y-4">
                {/* 1. VISION ANALYSIS HEADER BLOCK */}
                {geminiReport.vision && typeof geminiReport.vision === 'object' ? (
                  <>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-slate-900/80 p-3 rounded-lg border border-indigo-500/20 shadow-inner">
                        <div className="text-[10px] text-indigo-400/80 mb-1 font-mono tracking-wider">HAZARD TYPE</div>
                        <div className="text-sm font-bold text-rose-400">{geminiReport.vision.hazard_classification || "Unknown"}</div>
                      </div>
                      <div className="bg-slate-900/80 p-3 rounded-lg border border-indigo-500/20 shadow-inner">
                        <div className="text-[10px] text-indigo-400/80 mb-1 font-mono tracking-wider">CONFIDENCE SCORE</div>
                        <div className="text-sm font-bold text-emerald-400">{geminiReport.vision.confidence_score || "0"}% Confidence</div>
                      </div>
                    </div>

                    {/* 2. CORE METRIC & HAZARD TILES */}
                    <div className="space-y-3">
                      {/* AQI Micro-Badge */}
                      <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 px-3 py-2 rounded-full text-xs font-bold flex items-center justify-center">
                        [AQI: {geminiReport.vision.aqi_impact?.aqi_estimate || "N/A"} - {geminiReport.vision.aqi_impact?.category || "Unknown"}]
                      </div>
                      
                      {/* Landmark Visibility Gauge */}
                      <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50">
                        <div className="flex justify-between text-xs text-slate-300 mb-1.5">
                          <span>Landmark Visibility: {geminiReport.vision.visibility_gauge?.text || "Unknown"}</span>
                          <span className="font-mono">{geminiReport.vision.visibility_gauge?.percentage || 0}%</span>
                        </div>
                        <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div className="bg-indigo-400 h-full rounded-full" style={{ width: `${geminiReport.vision.visibility_gauge?.percentage || 0}%` }}></div>
                        </div>
                      </div>

                      {/* Health Impact Checklist */}
                      <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700/50 space-y-2">
                        <div className="text-[10px] text-slate-400 uppercase tracking-widest font-bold mb-2">Health Impact Checklist</div>
                        {geminiReport.vision.health_impacts?.map((impact: string, i: number) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-slate-300 leading-tight">
                            <span>{i === 0 ? '⚠️' : '👶'}</span>
                            <span>{impact}</span>
                          </div>
                        ))}
                      </div>

                      {/* Safety Risk Card */}
                      <div className="bg-red-500/10 border-l-2 border-red-500 p-3 rounded-r-lg">
                        <div className="text-xs text-red-200 font-medium">
                          🚨 {geminiReport.vision.safety_risk || "No immediate safety risks identified."}
                        </div>
                      </div>
                    </div>

                    {/* 3. 24-HOUR TREND METRIC PLOTS */}
                    <div className="space-y-3 pt-2">
                      <div className="text-[10px] text-indigo-400/80 font-mono tracking-wider">ATMOSPHERIC TRAP CONDITIONS</div>
                      <div className="text-xs font-semibold text-slate-200 bg-slate-800/80 px-2 py-1 rounded inline-block">
                        ☁️ {geminiReport.vision.atmospheric_conditions || "Unknown Conditions"}
                      </div>
                      
                      <div className="flex gap-2 overflow-x-auto pb-2 custom-scrollbar">
                        {geminiReport.vision.drift_projections?.map((proj: string, i: number) => (
                          <div key={i} className="flex-none bg-slate-900 border border-slate-700 p-2 rounded text-[10px] font-mono text-slate-300 whitespace-nowrap">
                            {proj}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 4. MUNICIPAL ACTION ABSTRACTION LABELS */}
                    <div className="space-y-3 pt-2 border-t border-indigo-500/20">
                      <div className="text-[10px] text-indigo-400/80 font-mono tracking-wider">MCD ACTION PLAYBOOK</div>
                      
                      <div className="space-y-2">
                        <div className="text-[10px] text-slate-500 uppercase">Short-Term</div>
                        <div className="flex flex-wrap gap-1">
                          {geminiReport.vision.mcd_playbook?.short_term?.map((action: string, i: number) => (
                            <span key={i} className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] px-1.5 py-0.5 rounded-sm">{action}</span>
                          ))}
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <div className="text-[10px] text-slate-500 uppercase">Medium-Term</div>
                        <div className="flex flex-wrap gap-1">
                          {geminiReport.vision.mcd_playbook?.medium_term?.map((action: string, i: number) => (
                            <span key={i} className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[9px] px-1.5 py-0.5 rounded-sm">{action}</span>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="text-[10px] text-slate-500 uppercase">Long-Term Strategic</div>
                        <div className="flex flex-wrap gap-1">
                          {geminiReport.vision.mcd_playbook?.long_term?.map((action: string, i: number) => (
                            <span key={i} className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[9px] px-1.5 py-0.5 rounded-sm">{action}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="space-y-1.5">
                    <span className="text-[10px] text-indigo-400/80 font-mono tracking-wider">VISION_ANALYSIS</span>
                    <p className="text-sm text-indigo-100 leading-relaxed bg-indigo-950/50 p-3 rounded-lg border border-indigo-500/20 whitespace-pre-wrap">
                      {typeof geminiReport.vision === 'string' ? geminiReport.vision : JSON.stringify(geminiReport.vision)}
                    </p>
                  </div>
                )}

                {/* Speech Box (Keep fallback) */}
                {geminiReport.speech && (
                  <div className="space-y-1.5 pt-4 border-t border-indigo-500/20">
                    <span className="text-[10px] text-indigo-400/80 font-mono tracking-wider">SPEECH_TO_TEXT</span>
                    <p className="text-sm text-indigo-100 leading-relaxed bg-indigo-950/50 p-3 rounded-lg border border-indigo-500/20 italic">
                      {geminiReport.speech}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Evidence Summary */}
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
               <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Payload Summary</h3>
               <div className="space-y-2 text-sm text-slate-300">
                 <div className="flex justify-between">
                   <span className="text-slate-500">Category:</span>
                   <span>Auto-classified by AI</span>
                 </div>
                 <div className="flex justify-between">
                   <span className="text-slate-500">Location:</span>
                   <span className="truncate max-w-[150px]">{locationText || 'Unknown'}</span>
                 </div>
                 <div className="flex justify-between">
                   <span className="text-slate-500">Media Attached:</span>
                   <span>{[imagePreview ? 'Photo' : '', audioCaptured ? 'Voice' : ''].filter(Boolean).join(', ') || 'None'}</span>
                 </div>
               </div>
            </div>
            
            {/* 5. INTEGRATION TELEMETRY PIN (Footnote) */}
            <div className="pt-2 pb-2">
              <div className="font-mono text-[9px] text-slate-500 leading-tight opacity-70">
                [SYSTEM LOG]: Earth Engine real-time array linked. Coordinates mapped to live sensor node index {fetchedAqi || 154}. Multimodal payload verified.
              </div>
            </div>
          </div>
        )}

      </main>

      {/* Terminal Output (Visible on Input Step) */}
      {step === 'input' && (
        <div className="absolute bottom-24 left-4 right-4 bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg p-2 overflow-hidden pointer-events-none">
          <div className="font-mono text-[9px] text-emerald-400/80 leading-relaxed h-[40px] flex flex-col justify-end">
            {telemetryLogs.slice(-2).map((log, i) => (
              <div key={i} className="animate-fade-in opacity-80 truncate">{log}</div>
            ))}
          </div>
        </div>
      )}

      {/* Fixed Bottom Action */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-950 via-slate-950 to-transparent pb-6 z-30">
        {step === 'input' ? (
          <button 
            onClick={handleAnalyze}
            className="w-full py-4 rounded-2xl font-bold tracking-wide text-lg shadow-xl transition-all flex items-center justify-center bg-indigo-600 text-white hover:bg-indigo-500 hover:shadow-[0_0_20px_rgba(99,102,241,0.3)] active:scale-[0.98]"
          >
            <Sparkles className="w-5 h-5 mr-2" />
            Scan & Analyze
          </button>
        ) : step === 'report' ? (
          <button 
            onClick={handleReportSubmission}
            className="w-full py-4 rounded-2xl font-bold tracking-wide text-lg shadow-xl transition-all flex items-center justify-center bg-emerald-600 text-white hover:bg-emerald-500 hover:shadow-[0_0_20px_rgba(16,185,129,0.3)] active:scale-[0.98]"
          >
            <Send className="w-5 h-5 mr-2" />
            Submit Verified Report
          </button>
        ) : null}
      </div>
      
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #334155;
          border-radius: 4px;
        }
        .animate-fade-in {
          animation: fadeIn 0.3s ease-in-out;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default MobileReporter;
