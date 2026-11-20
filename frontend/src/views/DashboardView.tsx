import React, { useState, useEffect } from 'react';
import type { ServerStatus, ApiKeyItem } from '../types';
import { api } from '../services/api';

interface DashboardViewProps {
  status: ServerStatus | null;
  refreshStatus: () => void;
  keys: ApiKeyItem[];
  setCurrentTab: (tab: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ status, refreshStatus, keys, setCurrentTab }) => {
  const [loadingAction, setLoadingAction] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [activeRawKey, setActiveRawKey] = useState<string>('sk-local-noora-default-lan-key');
  const [testPrompt, setTestPrompt] = useState('Hello Noora! Introduce yourself in one sentence.');
  const [testResponse, setTestResponse] = useState('');
  const [testingInference, setTestingInference] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

  useEffect(() => {
    api.getActiveKeyInfo().then(data => {
      if (data?.raw_key) {
        setActiveRawKey(data.raw_key);
      }
    }).catch(() => {});
  }, [keys]);

  const handleAction = async (action: 'start' | 'stop' | 'restart') => {
    try {
      setLoadingAction(action);
      if (action === 'start') await api.startServer();
      else if (action === 'stop') await api.stopServer();
      else if (action === 'restart') await api.restartServer();
      setTimeout(refreshStatus, 1500);
    } catch (e: any) {
      alert(e.message || 'Action failed');
    } finally {
      setLoadingAction(null);
    }
  };

  const copyBaseUrl = () => {
    if (status?.api_base_url) {
      navigator.clipboard.writeText(status.api_base_url);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  const copyKey = () => {
    if (activeRawKey) {
      navigator.clipboard.writeText(activeRawKey);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const runTestPrompt = async () => {
    if (!testPrompt.trim()) return;
    setTestingInference(true);
    setTestError(null);
    setTestResponse('');

    try {
      if (status?.status !== 'ONLINE') {
        await api.startServer();
        refreshStatus();
      }

      const res = await fetch(`${status?.api_base_url || 'http://127.0.0.1:8080/v1'}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${activeRawKey}`
        },
        body: JSON.stringify({
          messages: [{ role: 'user', content: testPrompt }],
          max_tokens: 100,
          stream: false
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Inference request failed');
      }
      setTestResponse(data.choices?.[0]?.message?.content || 'No response generated.');
    } catch (err: any) {
      setTestError(err.message || 'Error communicating with AI server.');
    } finally {
      setTestingInference(false);
    }
  };

  const formatUptime = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return `${h}h ${m}m ${s}s`;
  };

  const isOnline = status?.status === 'ONLINE';

  return (
    <div className="space-y-6">
      {/* Top Banner / Controls */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <span className={`w-3.5 h-3.5 rounded-full ${
              isOnline ? 'bg-emerald-500 shadow-lg shadow-emerald-500/50' : 'bg-slate-500'
            }`}></span>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              AI Server {status?.status || 'OFFLINE'}
            </h2>
            <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-slate-800 text-slate-300 border border-slate-700">
              Active Model: {status?.active_model || 'Qwen 2.5 0.5B'}
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Running 100% locally on CPU with zero cloud dependencies. Accessible to any device on your Wi-Fi.
          </p>
        </div>

        {/* Server Action Controls */}
        <div className="flex items-center space-x-3">
          {!isOnline ? (
            <button
              onClick={() => handleAction('start')}
              disabled={loadingAction !== null}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white font-semibold text-sm shadow-lg shadow-emerald-600/30 hover:from-emerald-500 hover:to-teal-500 transition-all duration-200 active:scale-95 disabled:opacity-50"
            >
              <i className={`bx ${loadingAction === 'start' ? 'bx-loader-alt animate-spin' : 'bx-play'} text-lg`}></i>
              <span>{loadingAction === 'start' ? 'Starting Server...' : 'Start Server'}</span>
            </button>
          ) : (
            <>
              <button
                onClick={() => handleAction('stop')}
                disabled={loadingAction !== null}
                className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-rose-600/90 text-white font-semibold text-sm shadow-lg shadow-rose-600/30 hover:bg-rose-500 transition-all duration-200 active:scale-95 disabled:opacity-50"
              >
                <i className={`bx ${loadingAction === 'stop' ? 'bx-loader-alt animate-spin' : 'bx-stop'} text-lg`}></i>
                <span>{loadingAction === 'stop' ? 'Stopping...' : 'Stop Server'}</span>
              </button>
              <button
                onClick={() => handleAction('restart')}
                disabled={loadingAction !== null}
                className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-slate-800 text-slate-200 font-semibold text-sm border border-slate-700 hover:bg-slate-700 transition-all duration-200 active:scale-95 disabled:opacity-50"
              >
                <i className={`bx ${loadingAction === 'restart' ? 'bx-loader-alt animate-spin' : 'bx-refresh'} text-lg`}></i>
                <span>Restart</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Auto-Collected Connection Credentials Callout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Base URL */}
        <div className="glass-card p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/20 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-600/30 text-indigo-400 flex items-center justify-center text-xl">
              <i className="bx bx-network-chart"></i>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-400 block">LAN Base URL (Any Wi-Fi Device)</span>
              <p className="text-xs sm:text-sm font-mono text-slate-200">{status?.api_base_url || 'http://192.168.1.100:8080/v1'}</p>
            </div>
          </div>
          <button
            onClick={copyBaseUrl}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all shadow-md active:scale-95 whitespace-nowrap"
          >
            <i className={`bx ${copiedUrl ? 'bx-check' : 'bx-copy'}`}></i>
            <span>{copiedUrl ? 'Copied' : 'Copy'}</span>
          </button>
        </div>

        {/* Active Working Key */}
        <div className="glass-card p-4 rounded-xl border border-amber-500/30 bg-amber-950/10 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center text-xl">
              <i className="bx bx-key"></i>
            </div>
            <div>
              <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400 block">Active Working API Key</span>
              <p className="text-xs sm:text-sm font-mono text-amber-300 max-w-[200px] truncate select-all">{activeRawKey}</p>
            </div>
          </div>
          <button
            onClick={copyKey}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold transition-all shadow-md active:scale-95 whitespace-nowrap"
          >
            <i className={`bx ${copiedKey ? 'bx-check' : 'bx-copy'}`}></i>
            <span>{copiedKey ? 'Copied' : 'Copy Key'}</span>
          </button>
        </div>
      </div>

      {/* Auto-Detected Hardware & Processor Banner */}
      <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center space-x-2">
          <i className="bx bx-chip text-indigo-400 text-lg"></i>
          <span className="text-slate-400">Processor Auto-Detected:</span>
          <span className="font-semibold text-white">{status?.cpu_model || 'x86_64 CPU'}</span>
          <span className="text-slate-600">•</span>
          <span className="text-indigo-400 font-mono font-medium">
            {status?.cpu_physical_cores || 4} Physical Cores ({status?.cpu_logical_cores || 8} Threads)
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-400 font-mono text-[11px] font-semibold">
            Inference: {status?.threads_used || 4} Threads Active
          </span>
          <button
            onClick={() => setCurrentTab('platforms')}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold underline flex items-center gap-1"
          >
            <span>Platform Guides</span>
            <i className="bx bx-right-arrow-alt"></i>
          </button>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU utilization */}
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>CPU Utilization</span>
            <i className="bx bx-microchip text-lg text-indigo-400"></i>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-white">{status?.system_cpu_percent || 0}%</span>
            <span className="text-xs text-slate-400">System Load</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Engine Threads: <span className="text-slate-200 font-mono">{status?.threads_used || 4} Cores</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, status?.system_cpu_percent || 0)}%` }}
            ></div>
          </div>
        </div>

        {/* RAM utilization */}
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Memory (RAM)</span>
            <i className="bx bx-server text-lg text-indigo-400"></i>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-white">{status?.system_ram_percent || 0}%</span>
            <span className="text-xs text-slate-400">
              {(status?.system_ram_used_mb ? status.system_ram_used_mb / 1024 : 0).toFixed(1)}GB / {(status?.system_ram_total_mb ? status.system_ram_total_mb / 1024 : 4).toFixed(1)}GB
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Model Memory: <span className="text-slate-200 font-mono">{status?.engine_memory_mb || 0} MB</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className={`h-1.5 rounded-full transition-all duration-500 ${
                (status?.system_ram_percent || 0) > 85 ? 'bg-rose-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(100, status?.system_ram_percent || 0)}%` }}
            ></div>
          </div>
        </div>

        {/* Requests Telemetry */}
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>API Requests</span>
            <i className="bx bx-transfer-alt text-lg text-indigo-400"></i>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-white">{status?.total_requests || 0}</span>
            <span className="text-xs text-slate-400">Total calls</span>
          </div>
          <div className="mt-2 flex items-center space-x-3 text-xs">
            <span className="text-emerald-400 font-medium">✓ {status?.successful_requests || 0} succ</span>
            <span className="text-rose-400 font-medium">✕ {status?.failed_requests || 0} fail</span>
          </div>
        </div>

        {/* LAN Clients & Uptime */}
        <div className="glass-card p-5 rounded-2xl">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Active Clients</span>
            <i className="bx bx-devices text-lg text-indigo-400"></i>
          </div>
          <div className="mt-3 flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-white">{status?.active_clients || 0}</span>
            <span className="text-xs text-slate-400">Observed</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Uptime: <span className="text-slate-200 font-mono">{formatUptime(status?.uptime_seconds || 0)}</span>
          </div>
        </div>
      </div>

      {/* Built-in Quick Test Console with Direct Playground Shortcut */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <i className="bx bx-message-square-dots text-xl text-indigo-400"></i>
            <h3 className="text-base font-semibold text-white">Quick Test Inference</h3>
          </div>
          <button
            onClick={() => setCurrentTab('playground')}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center space-x-1"
          >
            <span>Open Full Chat Playground</span>
            <i className="bx bx-arrow-to-right"></i>
          </button>
        </div>

        <div className="space-y-3">
          <textarea
            value={testPrompt}
            onChange={(e) => setTestPrompt(e.target.value)}
            disabled={testingInference}
            placeholder="Type a test question for Noora..."
            rows={2}
            className="w-full glass-input rounded-xl p-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none resize-none"
          ></textarea>

          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Using Key: <code className="text-amber-400 font-mono">{activeRawKey}</code>
            </span>
            <button
              onClick={runTestPrompt}
              disabled={testingInference || !testPrompt.trim()}
              className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/30 transition-all active:scale-95 disabled:opacity-50"
            >
              <i className={`bx ${testingInference ? 'bx-loader-alt animate-spin' : 'bx-send'}`}></i>
              <span>{testingInference ? 'Generating...' : 'Send Prompt'}</span>
            </button>
          </div>
        </div>

        {testError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {testError}
          </div>
        )}

        {testResponse && (
          <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-slate-200 text-sm font-sans whitespace-pre-wrap leading-relaxed">
            <div className="flex items-center space-x-2 mb-2 text-xs font-semibold text-indigo-400">
              <i className="bx bx-bot"></i>
              <span>Noora AI Response:</span>
            </div>
            {testResponse}
          </div>
        )}
      </div>
    </div>
  );
};
