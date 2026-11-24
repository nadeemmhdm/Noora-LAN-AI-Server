import React from 'react';
import type { ServerStatus } from '../types';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  status: ServerStatus | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab, status }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'bx-grid-alt' },
    { id: 'playground', label: 'Chat Playground', icon: 'bx-chat' },
    { id: 'training', label: 'AI Training', icon: 'bx-book-reader' },
    { id: 'platforms', label: 'Connect Platforms', icon: 'bx-broadcast' },
    { id: 'models', label: 'Models', icon: 'bx-chip' },
    { id: 'apikeys', label: 'API Keys', icon: 'bx-key' },
    { id: 'devices', label: 'Connected Devices', icon: 'bx-devices' },
    { id: 'logs', label: 'Usage & Logs', icon: 'bx-line-chart' },
    { id: 'settings', label: 'Settings', icon: 'bx-slider-alt' },
    { id: 'about', label: 'About', icon: 'bx-info-circle' },
  ];

  const getStatusColor = (s?: string) => {
    switch (s) {
      case 'ONLINE': return 'bg-emerald-500 shadow-emerald-500/50';
      case 'STARTING': return 'bg-amber-500 animate-pulse shadow-amber-500/50';
      case 'STOPPING': return 'bg-amber-600 animate-pulse';
      case 'ERROR': return 'bg-rose-500 shadow-rose-500/50';
      default: return 'bg-slate-500';
    }
  };

  return (
    <aside className="w-64 bg-slate-900/90 border-r border-slate-800/80 flex flex-col justify-between select-none z-20 backdrop-blur-xl shrink-0">
      <div className="overflow-y-auto">
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-800/60">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/30 text-white text-2xl font-bold">
              <i className="bx bx-bot"></i>
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                Noora AI
                <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                  LAN
                </span>
              </h1>
              <p className="text-xs text-slate-400">Local AI Server</p>
            </div>
          </div>

          {/* Server Status Pill */}
          <div className="mt-3.5 px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className={`w-2.5 h-2.5 rounded-full shadow-md ${getStatusColor(status?.status)}`}></span>
              <span className="text-xs font-medium text-slate-300">
                {status?.status || 'OFFLINE'}
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {status?.lan_ip ? `${status.lan_ip}:${status.port}` : '127.0.0.1:8080'}
            </span>
          </div>
        </div>

        {/* Navigation links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-md shadow-indigo-600/30 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <i className={`bx ${item.icon} text-lg ${isActive ? 'text-white' : 'text-slate-400'}`}></i>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Branding */}
      <div className="p-4 border-t border-slate-800/60 bg-slate-950/40">
        <div className="px-3 py-2 rounded-lg bg-slate-900/60 border border-slate-800/50 text-center">
          <p className="text-[11px] text-slate-400">
            Engineered by <span className="font-semibold text-indigo-400">Nadeem</span>
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">CPU Inference • Auto-Hardware Config</p>
        </div>
      </div>
    </aside>
  );
};
