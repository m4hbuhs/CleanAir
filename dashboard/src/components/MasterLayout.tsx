import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Map, ShieldAlert, Smartphone, Globe, Bell, MessageCircle, Tv, X } from 'lucide-react';
import { useAppContext } from '../AppContext';

interface Props {
  children: React.ReactNode;
  activeView: string;
  setActiveView: (view: string) => void;
}

export const MasterLayout: React.FC<Props> = ({ children, activeView, setActiveView }) => {
  const { globalAlert, latestReport } = useAppContext();

  // Notification Engine States
  const [showWhatsApp, setShowWhatsApp] = useState(false);
  const [showNews, setShowNews] = useState(false);
  const [whatsappContent, setWhatsappContent] = useState('');
  const [newsContent, setNewsContent] = useState('');

  useEffect(() => {
    if (latestReport) {
      // Trigger WhatsApp Notification after 2 seconds
      setWhatsappContent(`RWA Group: Avoid ${latestReport.location}. High AQI due to incident!`);
      setTimeout(() => setShowWhatsApp(true), 2000);

      // Trigger News Alert after 5 seconds
      setNewsContent(`Live News: Localized pollution spike detected at ${latestReport.location}. Rapid response teams dispatched.`);
      setTimeout(() => setShowNews(true), 5000);

      // Auto-hide
      setTimeout(() => setShowWhatsApp(false), 8000);
      setTimeout(() => setShowNews(false), 12000);
    }
  }, [latestReport]);

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-50 overflow-hidden font-sans">
      
      {/* Global Navigation Sidebar */}
      <div className="w-20 flex flex-col items-center py-6 bg-slate-900 border-r border-slate-800 shrink-0 z-50 shadow-2xl">
        <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center mb-10 border border-emerald-500/30">
          <Globe className="text-emerald-400 w-7 h-7" />
        </div>
        
        <nav className="flex flex-col space-y-6 w-full px-3">
          <NavItem 
            icon={<Map size={24} />} 
            label="Map" 
            isActive={activeView === 'map'} 
            onClick={() => setActiveView('map')} 
          />
          <NavItem 
            icon={<LayoutDashboard size={24} />} 
            label="Command Center" 
            isActive={activeView === 'command'} 
            onClick={() => setActiveView('command')} 
          />
          <NavItem 
            icon={<ShieldAlert size={24} />} 
            label="Forensics" 
            isActive={activeView === 'forensics'} 
            onClick={() => setActiveView('forensics')} 
          />
          <div className="my-2 border-b border-slate-800 w-8 mx-auto" />
          <NavItem 
            icon={<Smartphone size={24} />} 
            label="Public Portal" 
            isActive={activeView === 'portal'} 
            onClick={() => setActiveView('portal')} 
            highlight
          />
        </nav>
      </div>

      <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-slate-950">
        
        {/* Global Top Bar */}
        <header className="h-14 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6 z-40 shadow-sm shrink-0">
          {/* Alerts Marquee */}
          <div className="flex-1 overflow-hidden flex items-center space-x-3 mr-6">
            <Bell size={16} className="text-amber-400 shrink-0 animate-pulse" />
            <div className="text-xs text-amber-400/90 whitespace-nowrap overflow-hidden flex-1">
              {/* Reset animation on text change by keying on globalAlert */}
              <span key={globalAlert} className="inline-block animate-[marquee_20s_linear_infinite]">
                {globalAlert}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-6 shrink-0">
            {/* Language Toggle */}
            <div className="flex items-center space-x-2 text-xs font-medium text-slate-400 bg-slate-950 px-3 py-1.5 rounded-full border border-slate-800">
              <button className="text-emerald-400 font-bold">EN</button>
              <span className="text-slate-700">|</span>
              <button className="hover:text-slate-200">HI</button>
              <span className="text-slate-700">|</span>
              <button className="hover:text-slate-200">TA</button>
              <span className="text-slate-700">|</span>
              <button className="hover:text-slate-200">Hinglish</button>
            </div>

            {/* System Health */}
            <div className="flex items-center space-x-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-widest">Systems Nominal</span>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-hidden relative">
          {children}

          {/* Global Notification Overlay Engine */}
          <div className="absolute top-20 right-6 z-50 flex flex-col gap-4 pointer-events-none">
            
            {/* WhatsApp Mock Notification */}
            <div className={`pointer-events-auto bg-slate-800/95 backdrop-blur-md border-l-4 border-emerald-500 rounded-lg shadow-2xl p-4 w-80 transform transition-all duration-500 flex items-start gap-3
              ${showWhatsApp ? 'translate-x-0 opacity-100' : 'translate-x-[120%] opacity-0'}`}
            >
              <div className="bg-emerald-500/20 p-2 rounded-full shrink-0">
                <MessageCircle className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <h4 className="text-xs font-bold text-slate-200">WhatsApp</h4>
                  <span className="text-[10px] text-slate-500">Just now</span>
                </div>
                <p className="text-xs text-slate-300 leading-snug">{whatsappContent}</p>
              </div>
              <button onClick={() => setShowWhatsApp(false)} className="text-slate-500 hover:text-slate-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Live News Alert */}
            <div className={`pointer-events-auto bg-slate-950/95 backdrop-blur-md border border-red-500/30 rounded-lg shadow-2xl p-4 w-80 transform transition-all duration-500 flex items-start gap-3
              ${showNews ? 'translate-x-0 opacity-100' : 'translate-x-[120%] opacity-0'}`}
            >
              <div className="bg-red-500/20 p-2 rounded-full shrink-0 animate-pulse">
                <Tv className="w-5 h-5 text-red-400" />
              </div>
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <h4 className="text-xs font-bold text-red-400 uppercase tracking-wider">BREAKING NEWS</h4>
                  <span className="text-[10px] text-slate-500">Live</span>
                </div>
                <p className="text-xs text-slate-300 leading-snug">{newsContent}</p>
              </div>
              <button onClick={() => setShowNews(false)} className="text-slate-500 hover:text-slate-300">
                <X className="w-4 h-4" />
              </button>
            </div>
            
          </div>
        </main>
      </div>
    </div>
  );
};

const NavItem = ({ icon, label, isActive, onClick, highlight = false }: any) => {
  return (
    <button 
      onClick={onClick}
      className={`w-full aspect-square rounded-xl flex flex-col items-center justify-center transition-all group relative
        ${isActive 
          ? (highlight ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 shadow-[0_0_15px_rgba(99,102,241,0.2)]' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.15)]') 
          : 'text-slate-500 hover:bg-slate-800 hover:text-slate-300 border border-transparent'
        }`}
      title={label}
    >
      {icon}
      <span className="text-[10px] mt-1 font-semibold opacity-0 group-hover:opacity-100 absolute -bottom-6 whitespace-nowrap bg-slate-800 px-2 py-1 rounded shadow-lg z-50">
        {label}
      </span>
    </button>
  );
};
