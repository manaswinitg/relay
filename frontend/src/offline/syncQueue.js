import db from './db';

/**
 * Utility to generate a browser-native standard UUIDv4
 */
export function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Enqueue a mutation into the local persistent SyncQueue
 */
export async function enqueueMutation({ entity_type, action, payload, base_version = null }) {
  const mutation_id = generateUUID();
  const item = {
    mutation_id,
    entity_type: entity_type.toUpperCase(),
    action: action.toUpperCase(),
    base_version,
    payload,
    status: 'PENDING',
    timestamp: new Date().toISOString()
  };

  await db.syncQueue.add(item);
  return item;
}

/**
 * Get all pending mutations awaiting sync
 */
export async function getPendingMutations() {
  return await db.syncQueue.where('status').equals('PENDING').sortBy('local_id');
}

/**
 * Get count of pending items
 */
export async function getPendingCount() {
  return await db.syncQueue.where('status').equals('PENDING').count();
}

/**
 * Mark a mutation as APPLIED and remove from queue
 */
export async function removeMutation(local_id) {
  await db.syncQueue.delete(local_id);
}

/**
 * Mark a mutation as CONFLICT_ISOLATED
 */
export async function markMutationConflict(local_id, reason) {
  await db.syncQueue.update(local_id, {
    status: 'CONFLICT',
    conflict_reason: reason
  });
}
