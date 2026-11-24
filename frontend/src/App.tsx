import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './views/DashboardView';
import { PlaygroundView } from './views/PlaygroundView';
import { TrainingView } from './views/TrainingView';
import { PlatformsView } from './views/PlatformsView';
import { ModelsView } from './views/ModelsView';
import { ApiKeysView } from './views/ApiKeysView';
import { DevicesView } from './views/DevicesView';
import { LogsView } from './views/LogsView';
import { SettingsView } from './views/SettingsView';
import { AboutView } from './views/AboutView';
import type { ServerStatus, ApiKeyItem, ModelItem } from './types';
import { api } from './services/api';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [models, setModels] = useState<ModelItem[]>([]);

  const refreshStatus = async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
    } catch {
      // Offline or network error
    }
  };

  const refreshKeys = async () => {
    try {
      const data = await api.getKeys();
      setKeys(data);
    } catch {
      // ignore
    }
  };

  const refreshModels = async () => {
    try {
      const data = await api.getModels();
      setModels(data);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    refreshStatus();
    refreshKeys();
    refreshModels();
    const interval = setInterval(refreshStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 font-sans text-slate-100">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        status={status}
      />

      {/* Main Workspace */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950/20">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-slate-800/80 px-8 flex items-center justify-between backdrop-blur-md bg-slate-950/40 z-10 select-none">
          <div className="flex items-center space-x-3">
            <span className="text-sm font-bold text-white capitalize">
              {currentTab === 'playground' ? 'Chat Playground' : currentTab === 'training' ? 'AI Training & Knowledge' : currentTab === 'platforms' ? 'Connect Platforms' : currentTab}
            </span>
            <span className="text-slate-600">•</span>
            <span className="text-xs text-slate-400 font-mono">
              LAN Host: {status?.lan_ip || '127.0.0.1'}
            </span>
          </div>

          <div className="flex items-center space-x-4">
            {/* Quick Status Pill */}
            <div className="flex items-center space-x-2 text-xs font-semibold px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800">
              <span className={`w-2 h-2 rounded-full ${
                status?.status === 'ONLINE' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'
              }`}></span>
              <span className={status?.status === 'ONLINE' ? 'text-emerald-400' : 'text-slate-400'}>
                {status?.status || 'OFFLINE'}
              </span>
            </div>

            {/* Hardware footprint tag */}
            <div className="hidden sm:flex items-center space-x-1.5 text-[11px] font-medium text-slate-400 bg-slate-900/60 px-2.5 py-1 rounded-lg border border-slate-800">
              <i className="bx bx-chip text-indigo-400"></i>
              <span>{status?.cpu_physical_cores || 4} Physical Cores • Auto-Config</span>
            </div>
          </div>
        </header>

        {/* Content Pane */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-6xl mx-auto">
            {currentTab === 'dashboard' && (
              <DashboardView
                status={status}
                refreshStatus={refreshStatus}
                keys={keys}
                setCurrentTab={setCurrentTab}
              />
            )}
            {currentTab === 'playground' && (
              <PlaygroundView
                status={status}
                models={models}
                keys={keys}
                refreshStatus={refreshStatus}
              />
            )}
            {currentTab === 'training' && (
              <TrainingView
                status={status}
              />
            )}
            {currentTab === 'platforms' && (
              <PlatformsView
                status={status}
              />
            )}
            {currentTab === 'models' && (
              <ModelsView
                status={status}
                refreshStatus={refreshStatus}
              />
            )}
            {currentTab === 'apikeys' && (
              <ApiKeysView
                keys={keys}
                refreshKeys={refreshKeys}
              />
            )}
            {currentTab === 'devices' && (
              <DevicesView />
            )}
            {currentTab === 'logs' && (
              <LogsView />
            )}
            {currentTab === 'settings' && (
              <SettingsView />
            )}
            {currentTab === 'about' && (
              <AboutView status={status} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default App;
