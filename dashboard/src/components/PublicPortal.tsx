import React, { useState, useEffect } from 'react';
import MobileReporter from './MobileReporter';
import { MessageCircle, Award, Star, TrendingUp, X, Mic, Smartphone } from 'lucide-react';

export const PublicPortal = () => {
  const [chatOpen, setChatOpen] = useState(false);
  
  return (
    <div className="h-full w-full bg-slate-100 flex items-center justify-center relative overflow-hidden">
      
      {/* Background Decor */}
      <div className="absolute top-0 left-0 w-full h-64 bg-emerald-600/10 rounded-b-[100px] z-0"></div>

      <div className="flex w-full max-w-6xl mx-auto h-[90%] gap-8 z-10 p-4">
        
        {/* Left Column: Gamification */}
        <div className="hidden lg:flex flex-1 flex-col gap-6 justify-center">
          <div className="bg-white rounded-2xl p-6 shadow-xl border border-slate-200">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                <Award className="text-emerald-600 w-8 h-8" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-slate-800">Eco Guardian</h2>
                <p className="text-slate-500 font-medium">Level 4 Citizen</p>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <div className="text-sm text-slate-500 mb-1">Reward Points</div>
                <div className="text-2xl font-bold text-emerald-600 flex items-center gap-1">
                  <Star className="w-5 h-5 fill-emerald-500" /> 1,250
                </div>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                <div className="text-sm text-slate-500 mb-1">Verified Reports</div>
                <div className="text-2xl font-bold text-indigo-600 flex items-center gap-1">
                  <ShieldCheckIcon className="w-5 h-5" /> 12
                </div>
              </div>
            </div>

            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-2 opacity-10">
                <TrendingUp className="w-24 h-24 text-emerald-600" />
              </div>
              <h3 className="font-bold text-emerald-800 mb-2 relative z-10">Real-World Impact</h3>
              <p className="text-emerald-700 text-sm leading-relaxed relative z-10">
                "Your report last week directly deployed a mist cannon at Maple St. and improved local AQI by <span className="font-bold text-emerald-900 bg-emerald-200 px-1 rounded">15%</span>!"
              </p>
            </div>
          </div>
        </div>

        {/* Center: Mobile Simulator */}
        <div className="shrink-0 w-full max-w-md h-full flex flex-col justify-center relative">
          <div className="absolute -inset-4 bg-emerald-500/10 rounded-[3rem] blur-xl -z-10"></div>
          <div className="h-[800px] w-full rounded-[2.5rem] overflow-hidden shadow-2xl border-[8px] border-slate-800 bg-slate-950 relative">
            {/* Notch */}
            <div className="absolute top-0 inset-x-0 h-6 flex justify-center z-50">
              <div className="w-32 h-6 bg-slate-800 rounded-b-2xl"></div>
            </div>
            
            {/* Embedded Mobile Reporter component, overriding its h-[100dvh] constraint using a wrapper if necessary, 
                but since it's a direct child it will fill the container. */}
            <div className="w-full h-full pt-6 bg-slate-950 relative overflow-y-auto">
               <MobileReporter />
            </div>
          </div>
        </div>

        {/* Right Column: Information/Spacer to balance layout */}
        <div className="hidden lg:flex flex-1 flex-col justify-center">
           <div className="bg-white rounded-2xl p-6 shadow-xl border border-slate-200 text-center">
             <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
               <Smartphone className="w-10 h-10 text-indigo-600" />
             </div>
             <h3 className="text-xl font-bold text-slate-800 mb-2">Citizen App Simulator</h3>
             <p className="text-slate-600 mb-6">
               This is a high-fidelity preview of the public-facing mobile interface. Citizens use this minimal, hardware-focused UI to submit verified telemetry directly to the Command Center.
             </p>
           </div>
        </div>

      </div>

      {/* Floating Chatbot Widget */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
        
        {chatOpen && (
          <div className="bg-white w-[350px] rounded-2xl shadow-2xl border border-slate-200 mb-4 overflow-hidden flex flex-col animate-in slide-in-from-bottom-5 duration-300">
            <div className="bg-emerald-600 p-4 flex justify-between items-center text-white">
              <div>
                <h3 className="font-bold">CleanAir Sahayak</h3>
                <p className="text-xs text-emerald-200">Voice Assistant (Hinglish)</p>
              </div>
              <button onClick={() => setChatOpen(false)} className="hover:bg-emerald-700 p-1 rounded-full"><X size={20}/></button>
            </div>
            
            <div className="p-4 h-80 bg-slate-50 overflow-y-auto space-y-4 flex flex-col">
              
              <div className="flex gap-2">
                <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center shrink-0">
                  <Mic size={16} className="text-emerald-600" />
                </div>
                <div className="bg-white p-3 rounded-2xl rounded-tl-sm shadow-sm border border-slate-100 text-sm text-slate-700">
                  <p>Namaste! Aapke area mein pollution ki report karne ke liye mic button dabayein, ya photo bhejein. <br/><br/><i>"Bataiye, kya problem hai?"</i></p>
                </div>
              </div>

              <div className="flex gap-2 flex-row-reverse">
                <div className="bg-emerald-500 p-3 rounded-2xl rounded-tr-sm shadow-sm text-sm text-white max-w-[80%]">
                  <p>Yahan kachra jal raha hai, bohot dhuaan hai.</p>
                </div>
              </div>

              <div className="flex gap-2">
                <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center shrink-0">
                  <Mic size={16} className="text-emerald-600" />
                </div>
                <div className="bg-white p-3 rounded-2xl rounded-tl-sm shadow-sm border border-slate-100 text-sm text-slate-700">
                  <p>Shukriya. Humne location detect kar li hai. Kya aap ek photo attach kar sakte hain confirmation ke liye?</p>
                </div>
              </div>

            </div>

            <div className="p-3 bg-white border-t border-slate-100 flex items-center gap-2">
              <button className="p-3 bg-emerald-100 text-emerald-600 rounded-full hover:bg-emerald-200 transition-colors">
                <Mic size={20} />
              </button>
              <input type="text" placeholder="Type a message..." className="flex-1 bg-slate-100 rounded-full px-4 py-2 text-sm outline-none focus:ring-2 ring-emerald-500/50" disabled />
            </div>
          </div>
        )}

        <button 
          onClick={() => setChatOpen(!chatOpen)}
          className="w-16 h-16 bg-emerald-600 rounded-full shadow-2xl flex items-center justify-center text-white hover:bg-emerald-500 transition-transform hover:scale-105"
        >
          {chatOpen ? <X size={28} /> : <MessageCircle size={28} />}
        </button>
      </div>
    </div>
  );
};

// Helper icon
const ShieldCheckIcon = (props: any) => (
  <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    <path d="m9 12 2 2 4-4" />
  </svg>
)
