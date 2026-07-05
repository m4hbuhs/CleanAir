import { useState } from 'react';
import { MasterLayout } from './components/MasterLayout';
import { PollutionMap } from './components/PollutionMap';
import { AdminCommandCenter } from './components/AdminCommandCenter';
import ForensicsEngine from './components/ForensicsEngine';
import { PublicPortal } from './components/PublicPortal';
import { AppContextProvider } from './AppContext';
import { APIProvider } from '@vis.gl/react-google-maps';

export default function App() {
  const [activeView, setActiveView] = useState('map');

  return (
    <APIProvider apiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "AIzaSyD8zKcncg2dhMYpPvIGGUpbUF8CjPnDPhE"}>
      <AppContextProvider>
        <MasterLayout activeView={activeView} setActiveView={setActiveView}>
          {activeView === 'map' && <PollutionMap />}
          {activeView === 'command' && <AdminCommandCenter />}
          {activeView === 'forensics' && <ForensicsEngine />}
          {activeView === 'portal' && <PublicPortal />}
        </MasterLayout>
      </AppContextProvider>
    </APIProvider>
  )
}
