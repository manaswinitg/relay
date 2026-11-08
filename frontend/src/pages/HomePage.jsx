import React, { useState, useEffect } from 'react';
import { Shield, MapPin, AlertCircle, RefreshCw, Radio, CheckCircle2, Users } from 'lucide-react';
import MapView from '../components/MapView';
import db from '../offline/db';
import syncManager from '../offline/syncManager';

export default function HomePage({ setActivePage }) {
  const [shelters, setShelters] = useState([]);
  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState({
    totalShelters: 0,
    openShelters: 0,
    totalReports: 0,
    criticalReports: 0
  });

  const loadData = async () => {
    try {
      const allShelters = await db.shelters.toArray();
      const allReports = await db.reports.toArray();

      setShelters(allShelters);
      setReports(allReports);

      setStats({
        totalShelters: allShelters.length,
        openShelters: allShelters.filter(s => s.status === 'OPEN').length,
        totalReports: allReports.length,
        criticalReports: allReports.filter(r => r.urgency === 'CRITICAL').length
      });
    } catch (err) {
      console.error('Error loading home data:', err);
    }
  };

  useEffect(() => {
    loadData();
    // Subscribe to syncManager to refresh when new data arrives
    const unsubscribe = syncManager.subscribe((event) => {
      if (event.type === 'SYNC_COMPLETED') {
        loadData();
      }
    });
    return () => unsubscribe();
  }, []);

  return (
    <div className="space-y-8 pb-12">
      {/* Hero Banner */}
      <section className="bg-gradient-to-r from-slate-900 via-slate-800 to-emerald-950 text-white rounded-2xl p-8 sm:p-12 shadow-xl border border-slate-800 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Radio className="w-96 h-96 text-emerald-400" />
        </div>
        <div className="max-w-3xl relative z-10 space-y-4">
          <div className="inline-flex items-center space-x-2 bg-emerald-500/20 text-emerald-300 px-3 py-1 rounded-full text-xs font-semibold border border-emerald-500/30">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            <span>Distributed Resilience • Store-and-Forward Topology</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight">
            Reliable Disaster Coordination When Networks Fail.
          </h1>
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed">
            RELAY guarantees continuous emergency reporting, shelter discovery, and resource tracking on disconnected edge devices — synchronizing automatically when connectivity returns without silent data loss.
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <button
              onClick={() => setActivePage('report')}
              className="bg-red-600 hover:bg-red-500 text-white font-bold px-5 py-3 rounded-xl shadow-lg shadow-red-900/40 flex items-center space-x-2 text-sm transition"
            >
              <AlertCircle className="w-4 h-4" />
              <span>Report Emergency Incident</span>
            </button>
            <button
              onClick={() => setActivePage('shelters')}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-5 py-3 rounded-xl shadow-lg shadow-emerald-900/40 flex items-center space-x-2 text-sm transition"
            >
              <MapPin className="w-4 h-4" />
              <span>Find Nearby Shelters</span>
            </button>
          </div>
        </div>
      </section>

      {/* Metrics Row */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{stats.openShelters} / {stats.totalShelters}</div>
            <div className="text-xs text-slate-500 font-medium">Open Shelters</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-red-50 text-red-600 rounded-lg">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{stats.criticalReports}</div>
            <div className="text-xs text-slate-500 font-medium">Critical Distress Calls</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">{stats.totalReports}</div>
            <div className="text-xs text-slate-500 font-medium">Total Reports Logged</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-amber-50 text-amber-600 rounded-lg">
            <RefreshCw className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-900">100%</div>
            <div className="text-xs text-slate-500 font-medium">Offline Operability</div>
          </div>
        </div>
      </section>

      {/* Map & Live Feed Layout */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Interactive Map Visualizer */}
        <div className="lg:col-span-2 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4 flex flex-col">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Geospatial Resource Distribution</h2>
              <p className="text-xs text-slate-500">Live coordinates of relief centers and localized citizen distress alerts.</p>
            </div>
            <button
              onClick={() => setActivePage('shelters')}
              className="text-xs font-semibold text-emerald-600 hover:text-emerald-700"
            >
              Expand Full Map &rarr;
            </button>
          </div>
          <div className="flex-1 min-h-[380px]">
            <MapView shelters={shelters} reports={reports} />
          </div>
        </div>

        {/* Live Incident Stream */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4 flex flex-col">
          <div className="flex justify-between items-center border-b pb-3">
            <h2 className="text-lg font-bold text-slate-900">Recent Reports</h2>
            <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
              IndexedDB Local
            </span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[380px] pr-1">
            {reports.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                No emergency reports recorded locally yet.
              </div>
            ) : (
              reports.slice(0, 6).map((report) => (
                <div
                  key={report.id || report.client_assigned_uuid}
                  className="p-3 rounded-xl border border-slate-100 bg-slate-50 hover:bg-slate-100/80 transition space-y-1.5"
                >
                  <div className="flex justify-between items-center text-xs">
                    <span className={`px-2 py-0.5 rounded-full font-bold ${
                      report.urgency === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                      report.urgency === 'HIGH' ? 'bg-amber-100 text-amber-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {report.urgency} • {report.category}
                    </span>
                    <span className="text-slate-400 font-mono text-[10px]">
                      v{report.version || 1}
                    </span>
                  </div>
                  <p className="text-xs text-slate-800 line-clamp-2">{report.raw_text}</p>
                  {report.ai_summary && (
                    <div className="text-[10px] text-emerald-700 bg-emerald-50/80 px-2 py-0.5 rounded border border-emerald-100">
                      AI Triage: {report.ai_summary}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
