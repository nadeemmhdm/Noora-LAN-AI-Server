import React, { useState, useEffect } from 'react';
import { RequestLogItem, SystemLogItem } from '../types';
import { api } from '../services/api';

export const LogsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'requests' | 'system'>('requests');
  const [requestLogs, setRequestLogs] = useState<RequestLogItem[]>([]);
  const [systemLogs, setSystemLogs] = useState<SystemLogItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      if (activeTab === 'requests') {
        const data = await api.getRequestLogs(100);
        setRequestLogs(data.items);
        setTotalCount(data.total);
      } else {
        const data = await api.getSystemLogs(100);
        setSystemLogs(data);
      }
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [activeTab]);

  const handleClearLogs = async () => {
    if (!window.confirm('Are you sure you want to clear all audit and system logs?')) return;
    try {
      await api.clearLogs();
      fetchLogs();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  const getStatusBadge = (code: number) => {
    if (code >= 200 && code < 300) {
      return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">{code} OK</span>;
    } else if (code === 401 || code === 403) {
      return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400">{code} AUTH</span>;
    } else if (code === 429) {
      return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-400">{code} RATE</span>;
    } else {
      return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400">{code} ERR</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <i className="bx bx-line-chart text-indigo-400"></i>
            Usage & Audit Telemetry
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Real-time inference logs, latency metrics, and API request history.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="p-1 rounded-xl bg-slate-900 border border-slate-800 flex space-x-1">
            <button
              onClick={() => setActiveTab('requests')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'requests' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              API Requests
            </button>
            <button
              onClick={() => setActiveTab('system')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'system' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              System Events
            </button>
          </div>

          <button
            onClick={handleClearLogs}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-rose-400 transition-all text-base border border-slate-700"
            title="Clear all logs"
          >
            <i className="bx bx-trash"></i>
          </button>
        </div>
      </div>

      {/* Requests View */}
      {activeTab === 'requests' ? (
        <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Time</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Client IP</th>
                <th className="py-3.5 px-4">Endpoint</th>
                <th className="py-3.5 px-4">Latency</th>
                <th className="py-3.5 px-4">Tokens</th>
                <th className="py-3.5 px-4">Key Label</th>
                <th className="py-3.5 px-4">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {requestLogs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No API request telemetry recorded yet.
                  </td>
                </tr>
              ) : (
                requestLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-400">{formatDate(log.timestamp)}</td>
                    <td className="py-3 px-4">{getStatusBadge(log.status_code)}</td>
                    <td className="py-3 px-4 font-mono text-slate-300">{log.client_ip}</td>
                    <td className="py-3 px-4 font-mono text-indigo-400">
                      <span className="font-semibold text-slate-500 mr-1">{log.method}</span>
                      {log.endpoint}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">{log.latency_ms} ms</td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {log.tokens_prompt + log.tokens_completion > 0 ? `${log.tokens_prompt + log.tokens_completion}` : '-'}
                    </td>
                    <td className="py-3 px-4 text-slate-400">{log.api_key_name || 'Unauthenticated'}</td>
                    <td className="py-3 px-4 text-slate-500 max-w-xs truncate">{log.error_message || 'OK'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* System Logs View */
        <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
          <div className="p-4 bg-slate-900/60 font-mono text-xs space-y-2 max-h-[500px] overflow-y-auto">
            {systemLogs.length === 0 ? (
              <p className="text-slate-500 py-6 text-center">No system events logged.</p>
            ) : (
              systemLogs.map((l) => (
                <div key={l.id} className="flex items-start space-x-3 text-slate-300">
                  <span className="text-slate-500 select-none">[{formatDate(l.timestamp)}]</span>
                  <span className={`font-bold select-none ${
                    l.level === 'ERROR' ? 'text-rose-400' : l.level === 'WARNING' ? 'text-amber-400' : 'text-indigo-400'
                  }`}>
                    [{l.level}]
                  </span>
                  <span className="text-slate-400 select-none font-semibold">[{l.source}]</span>
                  <span className="flex-1">{l.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
