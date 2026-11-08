import React, { useState, useEffect } from 'react';
import { Shield, AlertTriangle, CheckCircle, XCircle, Sliders, RefreshCw, BarChart2, Layers, Cpu, Check, AlertCircle } from 'lucide-react';
import api from '../api/client';
import db from '../offline/db';
import syncManager from '../offline/syncManager';

export default function CoordinatorDashboard({ user, setActivePage }) {
  const [activeTab, setActiveTab] = useState('incidents'); // incidents, conflicts, shelters, ml
  const [reports, setReports] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [shelters, setShelters] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [mlMetrics, setMlMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedConflict, setSelectedConflict] = useState(null);
  const [manualPayloadStr, setManualPayloadStr] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    try {
      // 1. Fetch reports from backend (or fallback to IndexedDB)
      try {
        const res = await api.get('/reports?limit=50');
        setReports(res.data);
      } catch {
        setReports(await db.reports.toArray());
      }

      // 2. Fetch Shelters
      try {
        const sRes = await api.get('/shelters');
        setShelters(sRes.data);
      } catch {
        setShelters(await db.shelters.toArray());
      }

      // 3. Fetch Quarantined Conflicts if online and coordinator
      if (user && syncManager.isOnline) {
        try {
          const cRes = await api.get('/sync/conflicts');
          setConflicts(cRes.data);
        } catch (err) {
          console.warn('Could not load conflicts:', err);
        }

        try {
          const aRes = await api.get('/sync/audit-logs?limit=20');
          setAuditLogs(aRes.data);
        } catch {}

        try {
          const mRes = await api.get('/ml/metrics');
          setMlMetrics(mRes.data);
        } catch {}
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const unsub = syncManager.subscribe((ev) => {
      if (ev.type === 'SYNC_COMPLETED') loadData();
    });
    return () => unsub();
  }, [user]);

  const handleUpdateReportStatus = async (report, newStatus) => {
    try {
      if (syncManager.isOnline) {
        await api.patch(`/reports/${report.id}`, {
          status: newStatus,
          base_version: report.version
        });
      }
      // Update local IndexedDB
      await db.reports.update(report.id, {
        status: newStatus,
        version: (report.version || 1) + 1
      });

      setActionSuccess(`Report ${report.id.slice(0, 8)} updated to ${newStatus}.`);
      setTimeout(() => setActionSuccess(''), 3000);
      loadData();
    } catch (err) {
      alert('Failed to update report: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleResolveConflict = async (conflictId, resolutionType) => {
    try {
      let manualPayload = null;
      if (resolutionType === 'MANUAL_MERGE') {
        try {
          manualPayload = JSON.parse(manualPayloadStr);
        } catch {
          alert('Invalid JSON in manual payload.');
          return;
        }
      }

      await api.post(`/sync/conflicts/${conflictId}/resolve`, {
        resolution: resolutionType,
        manual_payload: manualPayload,
        resolution_notes: resolutionNotes || `Adjudicated by coordinator ${user?.full_name}`
      });

      setActionSuccess(`Conflict ${conflictId.slice(0, 8)} resolved via ${resolutionType}. Authoritative state updated.`);
      setTimeout(() => setActionSuccess(''), 4000);
      setSelectedConflict(null);
      setResolutionNotes('');
      setManualPayloadStr('');
      loadData();
    } catch (err) {
      alert('Failed to resolve conflict: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (!user) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center space-y-4">
        <Shield className="w-16 h-16 text-slate-400 mx-auto" />
        <h2 className="text-2xl font-black text-slate-900">Coordinator Authentication Required</h2>
        <p className="text-sm text-slate-500">
          The Coordinator Operations Hub provides human-in-the-loop conflict resolution, shelter capacity control, and triage oversight.
        </p>
        <button
          onClick={() => setActivePage('login')}
          className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-6 py-3 rounded-xl text-sm"
        >
          Sign In to Access Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner */}
      <div className="bg-slate-900 text-white p-6 rounded-2xl shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Shield className="w-6 h-6 text-emerald-400" />
            <h1 className="text-2xl font-black">Disaster Operations Coordinator Hub</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Logged in as <strong>{user.full_name}</strong> ({user.role}) • {user.email}
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-800 p-1 rounded-xl text-xs font-bold space-x-1">
          <button
            onClick={() => setActiveTab('incidents')}
            className={`px-3 py-2 rounded-lg transition ${activeTab === 'incidents' ? 'bg-emerald-500 text-slate-950' : 'text-slate-300 hover:text-white'}`}
          >
            Incident Feed ({reports.length})
          </button>
          <button
            onClick={() => setActiveTab('conflicts')}
            className={`px-3 py-2 rounded-lg transition relative ${activeTab === 'conflicts' ? 'bg-amber-500 text-slate-950' : 'text-slate-300 hover:text-white'}`}
          >
            <span>Quarantined Conflicts</span>
            {conflicts.length > 0 && (
              <span className="ml-1.5 px-1.5 py-0.2 rounded-full bg-red-600 text-white text-[10px]">
                {conflicts.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('shelters')}
            className={`px-3 py-2 rounded-lg transition ${activeTab === 'shelters' ? 'bg-emerald-500 text-slate-950' : 'text-slate-300 hover:text-white'}`}
          >
            Shelter Controls
          </button>
          <button
            onClick={() => setActiveTab('ml')}
            className={`px-3 py-2 rounded-lg transition ${activeTab === 'ml' ? 'bg-emerald-500 text-slate-950' : 'text-slate-300 hover:text-white'}`}
          >
            AI Evaluation
          </button>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm flex items-center space-x-2">
          <CheckCircle className="w-5 h-5 text-emerald-600" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Tab 1: Incident Feed */}
      {activeTab === 'incidents' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex justify-between items-center border-b pb-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Incoming Field Distress Calls</h2>
              <p className="text-xs text-slate-500">Triage crowdsourced and volunteer incident reports.</p>
            </div>
            <button onClick={loadData} className="p-2 hover:bg-slate-100 rounded-lg text-slate-600">
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          <div className="space-y-3">
            {reports.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-sm">No incident reports logged.</div>
            ) : (
              reports.map((r) => (
                <div key={r.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold ${
                        r.urgency === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                        r.urgency === 'HIGH' ? 'bg-amber-100 text-amber-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {r.urgency}
                      </span>
                      <span className="text-xs font-bold text-slate-700 uppercase bg-slate-200 px-2 py-0.5 rounded">
                        {r.category}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                        r.status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-800' :
                        r.status === 'RESOLVED' ? 'bg-slate-200 text-slate-600' :
                        'bg-amber-100 text-amber-800'
                      }`}>
                        {r.status}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono">v{r.version}</span>
                    </div>

                    <p className="text-sm font-medium text-slate-900">{r.raw_text}</p>
                    <div className="text-xs text-slate-500 flex flex-wrap gap-x-4">
                      {r.reporter_name && <span>Reporter: <strong>{r.reporter_name}</strong></span>}
                      {r.contact_info && <span>Contact: <strong>{r.contact_info}</strong></span>}
                      <span>GPS: {r.latitude}, {r.longitude}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 shrink-0">
                    {r.status !== 'VERIFIED' && (
                      <button
                        onClick={() => handleUpdateReportStatus(r, 'VERIFIED')}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold"
                      >
                        Verify Incident
                      </button>
                    )}
                    {r.status !== 'RESOLVED' && (
                      <button
                        onClick={() => handleUpdateReportStatus(r, 'RESOLVED')}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-bold"
                      >
                        Mark Resolved
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Quarantined Conflicts (Distributed Systems Highlight) */}
      {activeTab === 'conflicts' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="border-b pb-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              <span>Quarantined Distributed Conflicts</span>
            </h2>
            <p className="text-xs text-slate-500">
              When concurrent offline volunteers make incompatible edits to mutable records, RELAY quarantines them rather than executing destructive Last-Write-Wins overwrites.
            </p>
          </div>

          {conflicts.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-sm">
              <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-2" />
              No pending conflicts! All distributed nodes are currently synchronized and consistent.
            </div>
          ) : (
            <div className="space-y-4">
              {conflicts.map((c) => (
                <div key={c.id} className="p-5 rounded-2xl border-2 border-amber-200 bg-amber-50/50 space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="text-xs font-mono bg-amber-200 text-amber-900 px-2 py-0.5 rounded font-bold">
                        {c.entity_type} ID: {c.entity_id}
                      </span>
                      <div className="text-xs text-slate-600 mt-1">
                        Reported by device <strong>{c.client_device_id}</strong> • Base v{c.client_base_version} vs Server Current v{c.server_current_version}
                      </div>
                    </div>
                    <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2.5 py-1 rounded-full border border-amber-300">
                      {c.resolution_status}
                    </span>
                  </div>

                  {/* 2-Way Payload Diff Visualizer */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-white p-3 rounded-xl border border-slate-200 space-y-1">
                      <div className="text-xs font-bold text-blue-700 flex items-center justify-between">
                        <span>Client Staged Payload (v{c.client_base_version})</span>
                      </div>
                      <pre className="text-[11px] bg-slate-50 p-2 rounded overflow-x-auto text-slate-800 font-mono">
                        {JSON.stringify(c.client_payload, null, 2)}
                      </pre>
                    </div>

                    <div className="bg-white p-3 rounded-xl border border-slate-200 space-y-1">
                      <div className="text-xs font-bold text-slate-700 flex items-center justify-between">
                        <span>Server Authoritative State (v{c.server_current_version})</span>
                      </div>
                      <pre className="text-[11px] bg-slate-50 p-2 rounded overflow-x-auto text-slate-800 font-mono">
                        {JSON.stringify(c.server_payload, null, 2)}
                      </pre>
                    </div>
                  </div>

                  {/* Resolution Controls */}
                  <div className="pt-2 border-t border-amber-200/60 flex flex-wrap gap-2 items-center justify-between">
                    <input
                      type="text"
                      placeholder="Optional coordinator adjudication notes..."
                      value={selectedConflict === c.id ? resolutionNotes : ''}
                      onChange={(e) => {
                        setSelectedConflict(c.id);
                        setResolutionNotes(e.target.value);
                      }}
                      className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs flex-1 min-w-[200px]"
                    />

                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleResolveConflict(c.id, 'ACCEPT_CLIENT')}
                        className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg"
                      >
                        Accept Client Update
                      </button>
                      <button
                        onClick={() => handleResolveConflict(c.id, 'ACCEPT_SERVER')}
                        className="bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg"
                      >
                        Keep Server State
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Shelter Management */}
      {activeTab === 'shelters' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="border-b pb-3">
            <h2 className="text-lg font-bold text-slate-900">Shelter Facility Controls</h2>
            <p className="text-xs text-slate-500">Update total capacity, operational status, or initiate evacuation protocols.</p>
          </div>

          <div className="space-y-4">
            {shelters.map((s) => (
              <div key={s.id} className="p-4 rounded-xl border border-slate-100 bg-slate-50 flex items-center justify-between gap-4">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">{s.name}</h3>
                  <p className="text-xs text-slate-500">{s.address} • Occupancy: {s.current_occupancy} / {s.total_capacity}</p>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-bold ${
                    s.status === 'OPEN' ? 'bg-emerald-100 text-emerald-800' :
                    s.status === 'FULL' ? 'bg-amber-100 text-amber-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {s.status} (v{s.version})
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: AI Model Evaluation */}
      {activeTab === 'ml' && mlMetrics && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
          <div className="border-b pb-3">
            <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-emerald-600" />
              <span>Lightweight Emergency NLP Classifier Evaluation</span>
            </h2>
            <p className="text-xs text-slate-500">
              Model performance metrics evaluated on emergency incident text for MS CS portfolio presentation.
            </p>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
              <div className="text-xs text-emerald-700 font-bold">Category Macro F1</div>
              <div className="text-2xl font-black text-emerald-950 mt-1">{mlMetrics.category_metrics.macro_f1_score}</div>
            </div>
            <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
              <div className="text-xs text-blue-700 font-bold">Critical Urgency Recall</div>
              <div className="text-2xl font-black text-blue-950 mt-1">{mlMetrics.urgency_metrics.critical_recall}</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-xl border border-purple-100">
              <div className="text-xs text-purple-700 font-bold">Inference Latency</div>
              <div className="text-2xl font-black text-purple-950 mt-1">{mlMetrics.inference_latency_ms} ms</div>
            </div>
            <div className="p-4 bg-amber-50 rounded-xl border border-amber-100">
              <div className="text-xs text-amber-700 font-bold">Training Samples</div>
              <div className="text-2xl font-black text-amber-950 mt-1">{mlMetrics.training_samples_count}</div>
            </div>
          </div>

          {/* Per-Class Breakdown */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Per-Category F1-Score</h4>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {Object.entries(mlMetrics.category_metrics.per_class_f1).map(([cat, score]) => (
                <div key={cat} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-center">
                  <div className="text-[11px] font-bold text-slate-600">{cat}</div>
                  <div className="text-base font-extrabold text-slate-900">{score}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Limitations and Defense */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-2">
            <div className="font-bold text-slate-800">Academic Limitations & Design Justifications:</div>
            <ul className="list-disc pl-4 space-y-1">
              {mlMetrics.limitations.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
