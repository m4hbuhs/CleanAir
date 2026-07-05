import { createContext, useState, ReactNode, useContext } from 'react';

// Explicitly exported type definition for cross-view ingestion
export interface ForensicReport {
  id: string;
  type: 'Photo' | 'Voice' | 'Keyword';
  location: string;
  lat?: number;
  lon?: number;
  aqi?: number | null;
  timestamp: string;
  status: 'Pending' | 'Verified' | 'Flagged';
  trustScore: number;
  details: string;
}

export interface AppContextType {
  globalAlert: string;
  setGlobalAlert: (msg: string) => void;
  forensicReports: ForensicReport[];
  addForensicReport: (report: ForensicReport) => void;
  updateForensicReport: (id: string, updates: Partial<ForensicReport>) => void;
  latestReport: ForensicReport | null;
}

export const AppContext = createContext<AppContextType | undefined>(undefined);

const INITIAL_REPORTS: ForensicReport[] = [];

export const AppContextProvider = ({ children }: { children: ReactNode }) => {
  const [globalAlert, setGlobalAlert] = useState<string>(
    "SYSTEM ALERT: CPCB Real-Time APIs synced smoothly. Hyperlocal models tracking stable patterns."
  );
  const [forensicReports, setForensicReports] = useState<ForensicReport[]>(INITIAL_REPORTS);
  const [latestReport, setLatestReport] = useState<ForensicReport | null>(null);

  const addForensicReport = (report: ForensicReport) => {
    setForensicReports(prev => [report, ...prev]);
    setLatestReport(report);
  };

  const updateForensicReport = (id: string, updates: Partial<ForensicReport>) => {
    setForensicReports(prev => prev.map(report => report.id === id ? { ...report, ...updates } : report));
    setLatestReport(prev => prev?.id === id ? { ...prev, ...updates } : prev);
  };

  return (
    <AppContext.Provider value={{ globalAlert, setGlobalAlert, forensicReports, addForensicReport, updateForensicReport, latestReport }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppContextProvider');
  }
  return context;
};
