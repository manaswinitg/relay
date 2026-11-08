import Dexie from 'dexie';

// Initialize the local IndexedDB database for RELAY Edge Client
export const db = new Dexie('RelayOfflineDatabase');

db.version(1).stores({
  shelters: 'id, client_assigned_uuid, status, version, updated_at',
  reports: 'id, client_assigned_uuid, category, urgency, status, version, updated_at',
  inventory: 'id, shelter_id, resource_type_id, version',
  resourceTypes: 'id, code, category',
  syncQueue: '++local_id, mutation_id, entity_type, action, status, timestamp',
  metadata: 'key'
});

export default db;
