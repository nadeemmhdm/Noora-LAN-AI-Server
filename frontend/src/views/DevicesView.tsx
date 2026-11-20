import React, { useState, useEffect } from 'react';
import { DeviceItem } from '../types';
import { api } from '../services/api';

export const DevicesView: React.FC = () => {
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const data = await api.getDevices();
      setDevices(data);
    } catch (e: any) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleBlock = async (device: DeviceItem) => {
    try {
      if (device.is_blocked) {
        await api.unblockDevice(device.ip_address);
      } else {
        if (!window.confirm(`Are you sure you want to block IP ${device.ip_address}? It will be rejected on all endpoints.`)) return;
        await api.blockDevice(device.ip_address);
      }
      fetchDevices();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <i className="bx bx-devices text-indigo-400"></i>
            Observed Connected Devices
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Devices on your local Wi-Fi / LAN that have communicated with Noora AI Server.
          </p>
        </div>

        <button
          onClick={fetchDevices}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-all active:scale-95"
        >
          <i className={`bx bx-refresh text-base ${loading ? 'animate-spin' : ''}`}></i>
          <span>Refresh</span>
        </button>
      </div>

      {/* Devices Table */}
      <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3.5 px-4">Device IP</th>
              <th className="py-3.5 px-4">Hostname</th>
              <th className="py-3.5 px-4">Observed Status</th>
              <th className="py-3.5 px-4">Requests</th>
              <th className="py-3.5 px-4">Last Seen</th>
              <th className="py-3.5 px-4">Last Key Used</th>
              <th className="py-3.5 px-4 text-right">Access Control</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {devices.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  No client devices have sent requests yet. Connect a client device on the same Wi-Fi using your LAN Base URL.
                </td>
              </tr>
            ) : (
              devices.map((d) => (
                <tr key={d.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-semibold text-white">{d.ip_address}</td>
                  <td className="py-3.5 px-4 text-slate-400">{d.hostname || 'Unknown'}</td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                      d.is_blocked
                        ? 'bg-rose-500/20 text-rose-400'
                        : d.observed_status === 'Active'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-slate-700 text-slate-400'
                    }`}>
                      {d.is_blocked ? 'Blocked' : d.observed_status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-indigo-400 font-medium">{d.request_count}</td>
                  <td className="py-3.5 px-4 text-slate-400">{formatDate(d.last_seen)}</td>
                  <td className="py-3.5 px-4 text-slate-400">{d.last_api_key_name || 'None'}</td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleToggleBlock(d)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        d.is_blocked
                          ? 'bg-emerald-600/30 text-emerald-300 hover:bg-emerald-600/50'
                          : 'bg-rose-600/20 text-rose-300 hover:bg-rose-600/40'
                      }`}
                    >
                      {d.is_blocked ? 'Unblock IP' : 'Block IP'}
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
