import React, { useState, useEffect } from 'react';
import { WifiOff, AlertTriangle, RefreshCw } from 'lucide-react';
import syncManager from '../offline/syncManager';
import { getPendingCount } from '../offline/syncQueue';

export default function OfflineBanner() {
  const [isOnline, setIsOnline] = useState(syncManager.isOnline);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    const update = async () => {
      setPendingCount(await getPendingCount());
    };
    update();

    const unsubscribe = syncManager.subscribe((event) => {
      if (event.type === 'STATUS_CHANGED') {
        setIsOnline(event.isOnline);
      }
      update();
    });

    return () => unsubscribe();
  }, []);

  if (isOnline && pendingCount === 0) return null;

  return (
    <aside aria-label="Offline status and synchronization" className={`py-2 px-4 text-xs font-medium border-b flex items-center justify-between transition ${
      !isOnline
        ? 'bg-amber-950/80 border-amber-800 text-amber-200'
        : 'bg-emerald-950/80 border-emerald-800 text-emerald-200'
    }`}>
      <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {!isOnline ? (
            <>
              <WifiOff className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                <strong>Disconnected Mode:</strong> You are currently offline. All reports and inventory updates are being safely committed to your local browser store (IndexedDB).
              </span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>
                <strong>Connection Restored:</strong> You have {pendingCount} offline update{pendingCount === 1 ? '' : 's'} waiting to synchronize with the central coordination hub.
              </span>
            </>
          )}
        </div>

        {pendingCount > 0 && isOnline && (
          <button
            onClick={() => syncManager.triggerSync()}
            className="ml-4 shrink-0 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-3 py-1 rounded text-xs flex items-center space-x-1"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Sync {pendingCount} Items Now</span>
          </button>
        )}
      </div>
    </aside>
  );
}
