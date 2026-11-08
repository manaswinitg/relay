import React, { useState, useEffect } from 'react';
import { MapPin, Phone, Users, Package, Plus, Minus, Filter, AlertCircle, RefreshCw } from 'lucide-react';
import MapView from '../components/MapView';
import db from '../offline/db';
import { enqueueMutation } from '../offline/syncQueue';
import syncManager from '../offline/syncManager';

export default function SheltersPage({ user }) {
  const [shelters, setShelters] = useState([]);
  const [inventories, setInventories] = useState([]);
  const [resourceTypes, setResourceTypes] = useState([]);
  const [selectedShelter, setSelectedShelter] = useState(null);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [deltaModal, setDeltaModal] = useState({ isOpen: false, shelter: null, resourceType: null });
  const [deltaAmount, setDeltaAmount] = useState(10);
  const [deltaSuccessMessage, setDeltaSuccessMessage] = useState('');

  const loadData = async () => {
    try {
      const s = await db.shelters.toArray();
      const inv = await db.inventory.toArray();
      const rt = await db.resourceTypes.toArray();

      setShelters(s);
      setInventories(inv);
      setResourceTypes(rt);
      if (s.length > 0 && !selectedShelter) {
        setSelectedShelter(s[0]);
      }
    } catch (err) {
      console.error('Failed to load local shelter data:', err);
    }
  };

  useEffect(() => {
    loadData();
    const unsub = syncManager.subscribe((ev) => {
      if (ev.type === 'SYNC_COMPLETED') loadData();
    });
    return () => unsub();
  }, []);

  const filteredShelters = shelters.filter(s => {
    if (filterStatus === 'ALL') return true;
    return s.status === filterStatus;
  });

  const getShelterInventory = (shelterId) => {
    const items = inventories.filter(i => i.shelter_id === shelterId);
    return items.map(i => {
      const rt = resourceTypes.find(r => r.id === i.resource_type_id);
      return {
        ...i,
        code: rt ? rt.code : 'UNKNOWN',
        name: rt ? rt.name : 'Unknown Item',
        unit: rt ? rt.unit : 'UNITS'
      };
    });
  };

  const handleApplyDelta = async (sign) => {
    if (!deltaModal.shelter || !deltaModal.resourceType) return;
    const finalDelta = sign * Math.abs(Number(deltaAmount));

    try {
      // 1. Enqueue mutation locally (Tier 2 Commutative Delta)
      await enqueueMutation({
        entity_type: 'INVENTORY',
        action: 'DELTA',
        base_version: deltaModal.resourceType.version || 1,
        payload: {
          shelter_id: deltaModal.shelter.id,
          resource_type_code: deltaModal.resourceType.code,
          delta: finalDelta
        }
      });

      // 2. Optimistically update local IndexedDB inventory
      const existingInv = await db.inventory.where({
        shelter_id: deltaModal.shelter.id,
        resource_type_id: deltaModal.resourceType.resource_type_id
      }).first();

      if (existingInv) {
        const newQty = Math.max(0, existingInv.quantity + finalDelta);
        await db.inventory.update(existingInv.id, {
          quantity: newQty,
          version: (existingInv.version || 1) + 1
        });
      }

      setDeltaSuccessMessage(`Logged ${finalDelta > 0 ? '+' : ''}${finalDelta} ${deltaModal.resourceType.unit} for ${deltaModal.shelter.name}. Enqueued for sync!`);
      setTimeout(() => setDeltaSuccessMessage(''), 4000);
      setDeltaModal({ isOpen: false, shelter: null, resourceType: null });
      await loadData();

      // Trigger background sync if online
      if (syncManager.isOnline) {
        syncManager.triggerSync();
      }
    } catch (err) {
      alert('Error recording local inventory delta: ' + err.message);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-2xl font-black text-slate-900 flex items-center space-x-2">
            <MapPin className="w-6 h-6 text-emerald-600" />
            <span>Shelters & Relief Centers</span>
          </h1>
          <p className="text-sm text-slate-500">
            Real-time occupancy and supplies available offline. Volunteer changes are commutatively reconciled.
          </p>
        </div>

        {/* Filter Badges */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-400" />
          {['ALL', 'OPEN', 'FULL', 'EVACUATING'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                filterStatus === st
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {deltaSuccessMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm flex items-center space-x-2">
          <RefreshCw className="w-4 h-4 text-emerald-600 animate-spin" />
          <span>{deltaSuccessMessage}</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Map */}
        <div className="lg:col-span-7 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm h-[560px]">
          <MapView
            shelters={filteredShelters}
            selectedCoords={selectedShelter ? { latitude: selectedShelter.latitude, longitude: selectedShelter.longitude } : null}
            center={selectedShelter ? [selectedShelter.latitude, selectedShelter.longitude] : [37.7749, -122.4194]}
          />
        </div>

        {/* Right: Shelter Cards */}
        <div className="lg:col-span-5 space-y-4 max-h-[560px] overflow-y-auto pr-1">
          {filteredShelters.length === 0 ? (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-400">
              No shelters matching current filter.
            </div>
          ) : (
            filteredShelters.map((s) => {
              const occupancyPct = s.total_capacity > 0 ? Math.round((s.current_occupancy / s.total_capacity) * 100) : 0;
              const shelterInv = getShelterInventory(s.id);

              return (
                <div
                  key={s.id || s.client_assigned_uuid}
                  onClick={() => setSelectedShelter(s)}
                  className={`bg-white p-5 rounded-2xl border transition cursor-pointer space-y-3 ${
                    selectedShelter?.id === s.id
                      ? 'border-emerald-500 ring-2 ring-emerald-500/20 shadow-md'
                      : 'border-slate-200 hover:border-slate-300 shadow-sm'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-bold text-slate-900 text-base">{s.name}</h3>
                      <p className="text-xs text-slate-500 flex items-center space-x-1 mt-0.5">
                        <MapPin className="w-3 h-3 text-slate-400 shrink-0" />
                        <span>{s.address}</span>
                      </p>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                      s.status === 'OPEN' ? 'bg-emerald-100 text-emerald-800' :
                      s.status === 'FULL' ? 'bg-amber-100 text-amber-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {s.status}
                    </span>
                  </div>

                  {/* Capacity Bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-slate-600 font-medium">
                      <span>Occupancy: {s.current_occupancy} / {s.total_capacity} beds</span>
                      <span>{occupancyPct}%</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          occupancyPct >= 100 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, occupancyPct)}%` }}
                      />
                    </div>
                  </div>

                  {/* Supply Inventory Badges */}
                  <div className="pt-2 border-t border-slate-100">
                    <div className="text-xs font-bold text-slate-700 mb-2 flex items-center justify-between">
                      <span className="flex items-center space-x-1">
                        <Package className="w-3.5 h-3.5 text-slate-400" />
                        <span>On-Site Emergency Supplies:</span>
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {shelterInv.map((inv) => (
                        <div
                          key={inv.id}
                          className="p-2 rounded-lg bg-slate-50 border border-slate-100 flex items-center justify-between text-xs"
                        >
                          <div>
                            <div className="font-medium text-slate-800 text-[11px] truncate max-w-[120px]">{inv.name}</div>
                            <div className="font-bold text-slate-900">{inv.quantity} <span className="text-[10px] text-slate-500 font-normal">{inv.unit}</span></div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeltaModal({ isOpen: true, shelter: s, resourceType: inv });
                            }}
                            title="Log supply update (delta)"
                            className="p-1 rounded bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold"
                          >
                            &plusmn;
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Delta Update Modal */}
      {deltaModal.isOpen && (
        <div className="fixed inset-0 bg-slate-950/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-black text-slate-900">
              Log Commutative Supply Delta
            </h3>
            <p className="text-xs text-slate-500">
              Record incoming supplies or distributions at <strong>{deltaModal.shelter?.name}</strong> for <strong>{deltaModal.resourceType?.name}</strong>.
            </p>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700">Quantity Amount ({deltaModal.resourceType?.unit})</label>
              <input
                type="number"
                min="1"
                value={deltaAmount}
                onChange={(e) => setDeltaAmount(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-lg font-bold"
              />
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2">
              <button
                onClick={() => handleApplyDelta(-1)}
                className="bg-amber-600 hover:bg-amber-500 text-white font-bold py-2.5 rounded-xl flex items-center justify-center space-x-1 text-sm"
              >
                <Minus className="w-4 h-4" />
                <span>Distribute (-{deltaAmount})</span>
              </button>
              <button
                onClick={() => handleApplyDelta(1)}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl flex items-center justify-center space-x-1 text-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Received (+{deltaAmount})</span>
              </button>
            </div>

            <button
              onClick={() => setDeltaModal({ isOpen: false, shelter: null, resourceType: null })}
              className="w-full text-xs text-slate-500 hover:text-slate-800 pt-2 font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
