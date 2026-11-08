import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import OfflineBanner from './components/OfflineBanner';
import HomePage from './pages/HomePage';
import SheltersPage from './pages/SheltersPage';
import ReportEmergencyPage from './pages/ReportEmergencyPage';
import CoordinatorDashboard from './pages/CoordinatorDashboard';
import LoginPage from './pages/LoginPage';
import syncManager from './offline/syncManager';

export default function App() {
  const [activePage, setActivePage] = useState('home');
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check local storage for authenticated user profile
    const storedUser = localStorage.getItem('relay_user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {}
    }

    // Trigger initial pull sync
    if (syncManager.isOnline) {
      syncManager.triggerSync();
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('relay_token');
    localStorage.removeItem('relay_user');
    setUser(null);
    setActivePage('home');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      <Navbar
        activePage={activePage}
        setActivePage={setActivePage}
        user={user}
        onLogout={handleLogout}
      />
      <OfflineBanner />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {activePage === 'home' && <HomePage setActivePage={setActivePage} />}
        {activePage === 'shelters' && <SheltersPage user={user} />}
        {activePage === 'report' && <ReportEmergencyPage setActivePage={setActivePage} />}
        {activePage === 'coordinator' && <CoordinatorDashboard user={user} setActivePage={setActivePage} />}
        {activePage === 'login' && (
          <LoginPage
            onLoginSuccess={(loggedUser) => setUser(loggedUser)}
            setActivePage={setActivePage}
          />
        )}
      </main>

      <footer className="border-t border-slate-200 bg-white py-6 mt-12 text-center text-xs text-slate-500 space-y-2">
        <div className="max-w-7xl mx-auto px-4">
          <p className="font-semibold text-slate-700">
            RELAY — Research Prototype for Distributed Disaster Coordination & Offline-First Resilience
          </p>
          <p className="text-slate-400">
            Simulated emergency data for academic demonstration. Built with FastAPI, SQLite/PostgreSQL, React, IndexedDB, and Scikit-Learn.
          </p>
        </div>
      </footer>
    </div>
  );
}
