import React, { useState, useEffect } from 'react';
import { FirewallStatus } from '../types';
import { api } from '../services/api';

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [firewall, setFirewall] = useState<FirewallStatus | null>(null);
  const [interfaces, setInterfaces] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [fwLoading, setFwLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const fetchConfig = async () => {
    try {
      const [sData, fData, netData] = await Promise.all([
        api.getSettings(),
        api.getFirewallStatus(),
        api.getInterfaces()
      ]);
      setSettings(sData);
      setFirewall(fData);
      setInterfaces(netData.interfaces || []);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      const res = await api.updateSettings(settings);
      setMsg(res.message);
      setTimeout(() => setMsg(null), 3000);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleFirewall = async (action: 'add' | 'remove') => {
    try {
      setFwLoading(true);
      const res = await api.configureFirewall(action);
      setMsg(res.message);
      const fData = await api.getFirewallStatus();
      setFirewall(fData);
      setTimeout(() => setMsg(null), 4000);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setFwLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <i className="bx bx-slider-alt text-indigo-400"></i>
          Server & Hardware Settings
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Configure network ports, inference threads, and Windows security rules.
        </p>
      </div>

      {msg && (
        <div className="p-3.5 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-medium flex items-center space-x-2">
          <i className="bx bx-info-circle text-base"></i>
          <span>{msg}</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Network & Subnet Settings */}
        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <i className="bx bx-wifi text-indigo-400"></i>
            LAN Network Gateway
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">Server Port (LAN)</label>
              <input
                type="number"
                value={settings.server_port || '8080'}
                onChange={(e) => setSettings({ ...settings, server_port: e.target.value })}
                className="w-full glass-input px-3.5 py-2.5 rounded-xl text-xs text-slate-200 focus:outline-none"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">Default: 8080</span>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">Network Interface</label>
              <select
                value={settings.selected_interface || 'auto'}
                onChange={(e) => setSettings({ ...settings, selected_interface: e.target.value })}
                className="w-full glass-input px-3.5 py-2.5 rounded-xl text-xs text-slate-200 focus:outline-none"
              >
                <option value="auto">Auto-detect Active LAN Interface</option>
                {interfaces.map((iface, i) => (
                  <option key={i} value={iface.ip}>
                    {iface.name} ({iface.ip})
                  </option>
                ))}
              </select>
              <span className="text-[11px] text-slate-500 mt-1 block">Binds the API gateway strictly to this LAN IP.</span>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-between border-t border-slate-800">
            <div>
              <span className="text-xs font-semibold text-white block">Restrict to Private Subnet</span>
              <span className="text-[11px] text-slate-400">
                Reject non-LAN client IPs (RFC 1918) to prevent unauthorized public exposure.
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.lan_access_only === 'true'}
              onChange={(e) => setSettings({ ...settings, lan_access_only: e.target.checked ? 'true' : 'false' })}
              className="w-4 h-4 rounded text-indigo-600 focus:ring-0 bg-slate-900 border-slate-700 cursor-pointer"
            />
          </div>
        </div>

        {/* AI Inference CPU Parameters */}
        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <i className="bx bx-chip text-indigo-400"></i>
            CPU Inference Optimization (Intel i5 • 4GB RAM)
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">CPU Threads</label>
              <input
                type="number"
                min={1}
                max={8}
                value={settings.cpu_threads || '2'}
                onChange={(e) => setSettings({ ...settings, cpu_threads: e.target.value })}
                className="w-full glass-input px-3.5 py-2.5 rounded-xl text-xs text-slate-200 focus:outline-none"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">Recommended: 2 threads for Intel i5</span>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">Context Size (Tokens)</label>
              <input
                type="number"
                min={512}
                max={8192}
                step={512}
                value={settings.context_size || '2048'}
                onChange={(e) => setSettings({ ...settings, context_size: e.target.value })}
                className="w-full glass-input px-3.5 py-2.5 rounded-xl text-xs text-slate-200 focus:outline-none"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">2048 tokens keeps memory low (~200MB)</span>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">Max Tokens per Response</label>
              <input
                type="number"
                min={64}
                max={4096}
                value={settings.max_tokens || '2048'}
                onChange={(e) => setSettings({ ...settings, max_tokens: e.target.value })}
                className="w-full glass-input px-3.5 py-2.5 rounded-xl text-xs text-slate-200 focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Windows Firewall Management */}
        <div className="glass-card p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <i className="bx bx-shield text-indigo-400"></i>
            Windows Firewall Inbound Rule
          </h3>

          <p className="text-xs text-slate-400 leading-relaxed">
            To allow other devices on your Wi-Fi/LAN (such as iPhones, Android phones, or secondary laptops) to communicate with your server, an inbound rule allows incoming TCP packets on port {settings.server_port || '8080'}.
          </p>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className={`w-3 h-3 rounded-full ${firewall?.exists ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
              <div>
                <span className="text-xs font-bold text-white block">
                  Rule Status: {firewall?.exists ? 'Active & Configured' : 'Not Configured'}
                </span>
                <span className="text-[11px] text-slate-400">
                  Rule Name: Noora LAN AI Server (Port {settings.server_port || 8080})
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {!firewall?.exists ? (
                <button
                  type="button"
                  onClick={() => handleFirewall('add')}
                  disabled={fwLoading}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
                >
                  {fwLoading ? 'Configuring...' : 'Add Firewall Rule'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => handleFirewall('remove')}
                  disabled={fwLoading}
                  className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
                >
                  {fwLoading ? 'Removing...' : 'Remove Rule'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Submit Save */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 transition-all active:scale-95 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
};
