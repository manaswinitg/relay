import axios from 'axios';
import db from './db';
import { getPendingMutations, removeMutation, markMutationConflict, generateUUID } from './syncQueue';

class SyncManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.isSyncing = false;
    this.subscribers = new Set();
    this.deviceId = this.getOrCreateDeviceId();

    // Bind event listeners
    window.addEventListener('online', () => this.handleNetworkChange(true));
    window.addEventListener('offline', () => this.handleNetworkChange(false));

    // Periodic heartbeat to verify actual server reachability (beyond just Wi-Fi connection)
    setInterval(() => this.checkServerConnectivity(), 10000);
  }

  getOrCreateDeviceId() {
    let id = localStorage.getItem('relay_device_id');
    if (!id) {
      id = 'dev-' + generateUUID().slice(0, 8);
      localStorage.setItem('relay_device_id', id);
    }
    return id;
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify(event) {
    for (const callback of this.subscribers) {
      try {
        callback(event);
      } catch (err) {
        console.error('Subscriber callback error:', err);
      }
    }
  }

  async handleNetworkChange(online) {
    if (online) {
      const reachable = await this.checkServerConnectivity();
      if (reachable) {
        this.triggerSync();
      }
    } else {
      this.isOnline = false;
      this.notify({ type: 'STATUS_CHANGED', isOnline: false });
    }
  }

  async checkServerConnectivity() {
    try {
      const res = await axios.get('/health', { timeout: 3000 });
      const wasOffline = !this.isOnline;
      this.isOnline = res.status === 200;
      if (wasOffline && this.isOnline) {
        this.notify({ type: 'STATUS_CHANGED', isOnline: true });
        this.triggerSync();
      }
      return this.isOnline;
    } catch {
      if (this.isOnline) {
        this.isOnline = false;
        this.notify({ type: 'STATUS_CHANGED', isOnline: false });
      }
      return false;
    }
  }

  async triggerSync() {
    if (this.isSyncing) return;
    this.isSyncing = true;
    this.notify({ type: 'SYNC_STARTED' });

    try {
      // 1. DRAIN PENDING QUEUE (PUSH)
      const pending = await getPendingMutations();
      if (pending.length > 0) {
        const batchPayload = {
          device_id: this.deviceId,
          client_sent_at: new Date().toISOString(),
          batch: pending.map(p => ({
            mutation_id: p.mutation_id,
            entity_type: p.entity_type,
            action: p.action,
            base_version: p.base_version,
            payload: p.payload,
            client_timestamp: p.timestamp
          }))
        };

        const pushRes = await axios.post('/api/v1/sync/push', batchPayload);
        const { results } = pushRes.data;

        // Process mutation outcomes
        for (const res of results) {
          const match = pending.find(p => p.mutation_id === res.mutation_id);
          if (match) {
            if (res.status === 'APPLIED' || res.status === 'DUPLICATE_IGNORED') {
              await removeMutation(match.local_id);
            } else if (res.status === 'CONFLICT_ISOLATED') {
              await markMutationConflict(match.local_id, res.message);
            }
          }
        }
      }

      // 2. PULL LATEST STATE (PULL)
      const lastSyncMeta = await db.metadata.get('last_sync_timestamp');
      const sinceParam = lastSyncMeta ? `?since=${encodeURIComponent(lastSyncMeta.value)}` : '';
      const pullRes = await axios.get(`/api/v1/sync/pull${sinceParam}`);

      const { server_timestamp, shelters, reports, inventory, resource_types } = pullRes.data;

      // Update local IndexedDB caches in parallel
      await db.transaction('rw', [db.shelters, db.reports, db.inventory, db.resourceTypes, db.metadata], async () => {
        if (shelters?.length > 0) await db.shelters.bulkPut(shelters);
        if (reports?.length > 0) await db.reports.bulkPut(reports);
        if (inventory?.length > 0) await db.inventory.bulkPut(inventory);
        if (resource_types?.length > 0) await db.resourceTypes.bulkPut(resource_types);
        await db.metadata.put({ key: 'last_sync_timestamp', value: server_timestamp });
      });

      this.notify({ type: 'SYNC_COMPLETED', timestamp: server_timestamp });
    } catch (err) {
      console.warn('Sync attempt failed (transient disconnect or error):', err.message);
      this.notify({ type: 'SYNC_FAILED', error: err.message });
    } finally {
      this.isSyncing = false;
    }
  }
}

export const syncManager = new SyncManager();
export default syncManager;
