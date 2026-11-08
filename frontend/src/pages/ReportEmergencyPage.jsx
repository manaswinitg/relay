import React, { useState, useEffect } from 'react';
import { AlertTriangle, Send, MapPin, Sparkles, CheckCircle2, ShieldAlert } from 'lucide-react';
import MapView from '../components/MapView';
import db from '../offline/db';
import { enqueueMutation, generateUUID } from '../offline/syncQueue';
import syncManager from '../offline/syncManager';
import api from '../api/client';

export default function ReportEmergencyPage({ setActivePage }) {
  const [formData, setFormData] = useState({
    reporter_name: '',
    contact_info: '',
    latitude: 37.7749,
    longitude: -122.4194,
    address_hint: '',
    category: 'OTHER',
    urgency: 'MEDIUM',
    raw_text: ''
  });

  const [aiPreview, setAiPreview] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedReport, setSubmittedReport] = useState(null);

  // Live AI triage preview when user types report text
  useEffect(() => {
    if (formData.raw_text.trim().length < 8) {
      setAiPreview(null);
      return;
    }

    const timer = setTimeout(async () => {
      // If online, call API; if offline, use client-side heuristic
      if (syncManager.isOnline) {
        try {
          const res = await api.post('/ml/classify', { text: formData.raw_text });
          setAiPreview(res.data);
          // Suggest predicted category and urgency
          if (formData.category === 'OTHER') {
            setFormData(prev => ({ ...prev, category: res.data.category, urgency: res.data.urgency }));
          }
        } catch {
          runOfflineHeuristic(formData.raw_text);
        }
      } else {
        runOfflineHeuristic(formData.raw_text);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [formData.raw_text]);

  const runOfflineHeuristic = (text) => {
    const lower = text.toLowerCase();
    let cat = 'OTHER';
    let urg = 'MEDIUM';
    if (/blood|wound|injured|insulin|doctor|unconscious|fever/.test(lower)) cat = 'MEDICAL';
    else if (/water|dehydrat|thirst|potable/.test(lower)) cat = 'WATER';
    else if (/food|starv|hungry|ration|meal/.test(lower)) cat = 'FOOD';
    else if (/roof|shelter|blanket|trapped|flood/.test(lower)) cat = 'SHELTER';
    else if (/wire|gas|explosion|fire|hazard/.test(lower)) cat = 'HAZARD';

    if (/critical|unconscious|immediate|trapped|dying/.test(lower)) urg = 'CRITICAL';
    else if (/high|urgent|danger/.test(lower)) urg = 'HIGH';

    setAiPreview({
      category: cat,
      urgency: urg,
      confidence: 0.85,
      keywords: ['local-heuristic', cat.toLowerCase()]
    });
  };

  const handleMapClick = (coords) => {
    setFormData(prev => ({
      ...prev,
      latitude: coords.latitude,
      longitude: coords.longitude
    }));
  };

  const handleGetCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setFormData(prev => ({
            ...prev,
            latitude: Number(pos.coords.latitude.toFixed(5)),
            longitude: Number(pos.coords.longitude.toFixed(5))
          }));
        },
        () => {
          alert('Could not access GPS. Please click on the map to set your location.');
        }
      );
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.raw_text.trim()) {
      alert('Please provide details of the emergency.');
      return;
    }

    setIsSubmitting(true);
    const clientUuid = generateUUID();
    const now = new Date().toISOString();

    const reportRecord = {
      id: clientUuid,
      client_assigned_uuid: clientUuid,
      reporter_name: formData.reporter_name || 'Anonymous Citizen',
      contact_info: formData.contact_info,
      latitude: formData.latitude,
      longitude: formData.longitude,
      address_hint: formData.address_hint,
      category: formData.category,
      urgency: formData.urgency,
      status: 'SUBMITTED',
      raw_text: formData.raw_text,
      ai_summary: aiPreview ? `Identified needs: ${aiPreview.keywords?.join(', ')}` : null,
      ai_confidence: aiPreview?.confidence || 0.8,
      version: 1,
      client_created_at: now,
      updated_at: now
    };

    try {
      // 1. Save directly into local IndexedDB
      await db.reports.put(reportRecord);

      // 2. Enqueue into persistent SyncQueue (Tier 1 Monotonic Ingestion)
      await enqueueMutation({
        entity_type: 'REPORT',
        action: 'CREATE',
        base_version: null,
        payload: reportRecord
      });

      setSubmittedReport(reportRecord);
      setIsSubmitting(false);

      // 3. Trigger immediate sync if connected
      if (syncManager.isOnline) {
        syncManager.triggerSync();
      }
    } catch (err) {
      setIsSubmitting(false);
      alert('Error storing report locally: ' + err.message);
    }
  };

  if (submittedReport) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 space-y-6 text-center">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-xl space-y-4">
          <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <h2 className="text-2xl font-black text-slate-900">Emergency Report Logged</h2>
          <p className="text-sm text-slate-600 leading-relaxed">
            Your distress call has been <strong>safely committed to device storage</strong> and enqueued for synchronization with the central disaster coordination network.
          </p>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 text-left text-xs space-y-2">
            <div><strong>Tracking Token:</strong> <span className="font-mono text-slate-500">{submittedReport.id}</span></div>
            <div><strong>Urgency Level:</strong> <span className="font-bold text-red-600">{submittedReport.urgency}</span></div>
            <div><strong>Category:</strong> <span className="font-bold text-slate-800">{submittedReport.category}</span></div>
            <div><strong>GPS Coordinates:</strong> {submittedReport.latitude}, {submittedReport.longitude}</div>
            <div><strong>Description:</strong> {submittedReport.raw_text}</div>
          </div>

          <div className="flex justify-center space-x-3 pt-4">
            <button
              onClick={() => {
                setSubmittedReport(null);
                setFormData({
                  reporter_name: '',
                  contact_info: '',
                  latitude: 37.7749,
                  longitude: -122.4194,
                  address_hint: '',
                  category: 'OTHER',
                  urgency: 'MEDIUM',
                  raw_text: ''
                });
              }}
              className="bg-slate-900 hover:bg-slate-800 text-white font-bold px-5 py-2.5 rounded-xl text-sm transition"
            >
              Submit Another Report
            </button>
            <button
              onClick={() => setActivePage('shelters')}
              className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-5 py-2.5 rounded-xl text-sm transition"
            >
              View Nearby Shelters
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div className="bg-red-50 border border-red-200 p-6 rounded-2xl flex items-start space-x-4">
        <ShieldAlert className="w-8 h-8 text-red-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h1 className="text-xl font-black text-red-950">Emergency Incident & Assistance Report</h1>
          <p className="text-xs text-red-800 leading-relaxed">
            Submit life-safety distress, supply shortages, or localized hazards. <strong>This form works 100% offline.</strong> If cellular towers are severed, your report is preserved locally and broadcasted the instant connectivity returns.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* Left: Input Form */}
        <form onSubmit={handleSubmit} className="md:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">What is happening? (Detailed Situation) *</label>
            <textarea
              required
              rows={4}
              value={formData.raw_text}
              onChange={(e) => setFormData({ ...formData, raw_text: e.target.value })}
              placeholder="E.g. Water is waist-deep on 4th street, elderly neighbor trapped on second floor with no drinking water or medication."
              className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-red-500 focus:outline-none"
            />
          </div>

          {/* Real-time AI Triage Card */}
          {aiPreview && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-emerald-900">
                <Sparkles className="w-4 h-4 text-emerald-600" />
                <span>AI Automated Triage Classification</span>
                <span className="text-[10px] bg-emerald-200/60 text-emerald-800 px-1.5 py-0.5 rounded">
                  {Math.round(aiPreview.confidence * 100)}% Confidence
                </span>
              </div>
              <div className="text-xs text-emerald-800">
                Predicted: <strong>{aiPreview.category}</strong> with <strong>{aiPreview.urgency}</strong> urgency.
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Category</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm"
              >
                <option value="MEDICAL">Medical Emergency</option>
                <option value="WATER">Water Shortage</option>
                <option value="FOOD">Food / Rations</option>
                <option value="SHELTER">Shelter / Evacuation</option>
                <option value="HAZARD">Hazard / Road Blockage</option>
                <option value="OTHER">Other Assistance</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Urgency Level</label>
              <select
                value={formData.urgency}
                onChange={(e) => setFormData({ ...formData, urgency: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm font-bold text-red-700"
              >
                <option value="CRITICAL">CRITICAL (Immediate Life Threat)</option>
                <option value="HIGH">HIGH (Urgent Assistance)</option>
                <option value="MEDIUM">MEDIUM (Needs Attention)</option>
                <option value="LOW">LOW (Informational)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Reporter Name (Optional)</label>
              <input
                type="text"
                value={formData.reporter_name}
                onChange={(e) => setFormData({ ...formData, reporter_name: e.target.value })}
                placeholder="Jane Doe"
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700">Contact / Phone (Optional)</label>
              <input
                type="text"
                value={formData.contact_info}
                onChange={(e) => setFormData({ ...formData, contact_info: e.target.value })}
                placeholder="+1 555-0199"
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-700">Address / Landmarks</label>
            <input
              type="text"
              value={formData.address_hint}
              onChange={(e) => setFormData({ ...formData, address_hint: e.target.value })}
              placeholder="Near corner of Market & 5th St, red brick building"
              className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm"
            />
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-red-600 hover:bg-red-500 text-white font-extrabold py-3.5 rounded-xl shadow-lg shadow-red-900/30 flex items-center justify-center space-x-2 text-sm transition"
            >
              <Send className="w-4 h-4" />
              <span>{isSubmitting ? 'Recording Locally...' : 'Broadcast Emergency Report'}</span>
            </button>
          </div>
        </form>

        {/* Right: Map Location Picker */}
        <div className="md:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3 flex flex-col">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Incident GPS Location</h3>
              <p className="text-[11px] text-slate-500">Click anywhere on the map to pin exact location.</p>
            </div>
            <button
              type="button"
              onClick={handleGetCurrentLocation}
              className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold px-2.5 py-1.5 rounded-lg flex items-center space-x-1"
            >
              <MapPin className="w-3 h-3 text-red-500" />
              <span>My GPS</span>
            </button>
          </div>

          <div className="flex-1 min-h-[300px]">
            <MapView
              selectedCoords={{ latitude: formData.latitude, longitude: formData.longitude }}
              onMapClick={handleMapClick}
              center={[formData.latitude, formData.longitude]}
              zoom={13}
            />
          </div>

          <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100 text-[11px] text-slate-600 font-mono text-center">
            Lat: {formData.latitude} | Lon: {formData.longitude}
          </div>
        </div>
      </div>
    </div>
  );
}
