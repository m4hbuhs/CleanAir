import React, { useState } from 'react';
import { MasterLayout } from './components/MasterLayout';
import { PollutionMap } from './components/PollutionMap';
import { AdminCommandCenter } from './components/AdminCommandCenter';
import ForensicsEngine from './components/ForensicsEngine'; // Now default exported
import { PublicPortal } from './components/PublicPortal';
import { AppContextProvider } from './AppContext';

export default function App() {
  const [activeView, setActiveView] = useState('map');

  return (
    <AppContextProvider>
      <MasterLayout activeView={activeView} setActiveView={setActiveView}>
        {activeView === 'map' && <PollutionMap />}
        {activeView === 'command' && <AdminCommandCenter />}
        {activeView === 'forensics' && <ForensicsEngine />}
        {activeView === 'portal' && <PublicPortal />}
      </MasterLayout>
    </AppContextProvider>
  )
}
