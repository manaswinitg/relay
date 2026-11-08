import React, { useState, useEffect } from 'react';
import { Shield, Wifi, WifiOff, RefreshCw, User, LogOut } from 'lucide-react';
import syncManager from '../offline/syncManager';
import { getPendingCount } from '../offline/syncQueue';

export default function Navbar({ activePage, setActivePage, user, onLogout }) {
  const [isOnline, setIsOnline] = useState(syncManager.isOnline);
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    const updateQueueCount = async () => {
      const count = await getPendingCount();
      setPendingCount(count);
    };

    updateQueueCount();

    const unsubscribe = syncManager.subscribe((event) => {
      if (event.type === 'STATUS_CHANGED') {
        setIsOnline(event.isOnline);
      } else if (event.type === 'SYNC_STARTED') {
        setIsSyncing(true);
      } else if (event.type === 'SYNC_COMPLETED' || event.type === 'SYNC_FAILED') {
        setIsSyncing(false);
        updateQueueCount();
      }
    });

    const interval = setInterval(updateQueueCount, 3000);
    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, []);

  const handleManualSync = () => {
    syncManager.triggerSync();
  };

  return (
    <header className="bg-slate-900 text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo & Brand */}
          <div 
            className="flex items-center space-x-3 cursor-pointer"
            onClick={() => setActivePage('home')}
          >
            <div className="bg-emerald-500 p-2 rounded-lg text-slate-950 font-bold">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="font-extrabold tracking-wider text-xl flex items-center space-x-2">
                <span>RELAY</span>
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded font-mono border border-emerald-500/30">
                  OFFLINE-FIRST
                </span>
              </div>
              <p className="text-xs text-slate-400">Emergency Resource Coordination</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex space-x-1">
            <button
              onClick={() => setActivePage('home')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                activePage === 'home' ? 'bg-slate-800 text-emerald-400' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActivePage('shelters')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                activePage === 'shelters' ? 'bg-slate-800 text-emerald-400' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              Map & Shelters
            </button>
            <button
              onClick={() => setActivePage('report')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                activePage === 'report' ? 'bg-red-950/80 text-red-300 border border-red-800/40' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              Report Emergency
            </button>
            <button
              onClick={() => setActivePage('coordinator')}
              className={`px-3 py-2 rounded-md text-sm font-medium transition ${
                activePage === 'coordinator' ? 'bg-slate-800 text-emerald-400' : 'text-slate-300 hover:bg-slate-800'
              }`}
            >
              Coordinator Hub
            </button>
          </nav>

          {/* Network Indicator & Queue Status */}
          <div className="flex items-center space-x-3">
            {/* Online / Offline Pill */}
            <div
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                isOnline
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : 'bg-amber-950 text-amber-300 border border-amber-800 animate-pulse-subtle'
              }`}
            >
              {isOnline ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                  <span>ONLINE</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-amber-400" />
                  <span>OFFLINE MODE</span>
                </>
              )}
            </div>

            {/* Sync Queue Badge & Trigger */}
            <button
              onClick={handleManualSync}
              disabled={isSyncing || !isOnline}
              title="Click to sync local queue with central server"
              className={`flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium border transition ${
                pendingCount > 0
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              } ${isSyncing ? 'opacity-70 cursor-not-allowed' : ''}`}
            >
              <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin text-emerald-400' : ''}`} />
              <span>{pendingCount} Queued</span>
            </button>

            {/* User Profile / Auth */}
            {user ? (
              <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
                <span className="text-xs text-slate-300 hidden sm:inline">{user.full_name.split(' ')[0]} ({user.role})</span>
                <button
                  onClick={onLogout}
                  title="Logout"
                  className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setActivePage('login')}
                className="text-xs bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 rounded-md font-medium text-slate-200 border border-slate-700 flex items-center space-x-1"
              >
                <User className="w-3.5 h-3.5" />
                <span>Sign In</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
