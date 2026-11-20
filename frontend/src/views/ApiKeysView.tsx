import React, { useState } from 'react';
import type { ApiKeyItem } from '../types';
import { api } from '../services/api';

interface ApiKeysViewProps {
  keys: ApiKeyItem[];
  refreshKeys: () => void;
}

export const ApiKeysView: React.FC<ApiKeysViewProps> = ({ keys, refreshKeys }) => {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [rateLimitRpm, setRateLimitRpm] = useState(120);
  const [creating, setCreating] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    try {
      setCreating(true);
      const res = await api.createKey(newKeyName.trim(), rateLimitRpm);
      setNewlyCreatedKey(res.raw_key);
      setNewKeyName('');
      refreshKeys();
    } catch (err: any) {
      alert(err.message || 'Failed to create key');
    } finally {
      setCreating(false);
    }
  };

  const handleToggle = async (id: number) => {
    try {
      await api.toggleKey(id);
      refreshKeys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRevoke = async (id: number) => {
    if (!window.confirm('Are you sure you want to permanently revoke this API key? Any device using it will lose access immediately.')) return;
    try {
      await api.revokeKey(id);
      refreshKeys();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const copySecret = (keyText: string) => {
    navigator.clipboard.writeText(keyText);
    setCopiedKey(keyText);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const formatDate = (timestamp?: number | null) => {
    if (!timestamp) return 'Never';
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <i className="bx bx-key text-indigo-400"></i>
            API Key Management
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Authenticate incoming OpenAI-compatible requests from devices on your local network.
          </p>
        </div>

        <button
          onClick={() => {
            setNewlyCreatedKey(null);
            setIsCreateOpen(true);
          }}
          className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm shadow-md shadow-indigo-600/30 transition-all active:scale-95"
        >
          <i className="bx bx-plus text-lg"></i>
          <span>Generate New Key</span>
        </button>
      </div>

      {/* Secret Revelation Modal */}
      {newlyCreatedKey && (
        <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-4">
          <div className="flex items-center space-x-2 text-amber-400 text-sm font-bold">
            <i className="bx bx-shield-quarter text-xl"></i>
            <span>New API Key Generated</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Copy and paste this key into your client application (Chatbox, OpenWebUI, Python, etc.) to connect to Noora AI.
          </p>
          <div className="flex items-center space-x-2">
            <input
              type="text"
              readOnly
              value={newlyCreatedKey}
              className="w-full glass-input px-3.5 py-2.5 rounded-xl font-mono text-xs text-amber-300 select-all focus:outline-none"
            />
            <button
              onClick={() => copySecret(newlyCreatedKey)}
              className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs transition-all active:scale-95 flex items-center space-x-1 whitespace-nowrap"
            >
              <i className={`bx ${copiedKey === newlyCreatedKey ? 'bx-check' : 'bx-copy'}`}></i>
              <span>{copiedKey === newlyCreatedKey ? 'Copied!' : 'Copy Key'}</span>
            </button>
          </div>
          <button
            onClick={() => setNewlyCreatedKey(null)}
            className="text-xs text-slate-400 hover:text-slate-200 underline pt-1 block"
          >
            Done
          </button>
        </div>
      )}

      {/* Create Key Dialog */}
      {isCreateOpen && !newlyCreatedKey && (
        <form onSubmit={handleCreateKey} className="glass-panel p-6 rounded-2xl space-y-4 border border-indigo-500/40">
          <h3 className="text-base font-bold text-white">Create New API Key</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5">Key Name / Label</label>
              <input
                type="text"
                placeholder="e.g. My Phone, iPad Chatbox, Python Script"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                required
                className="w-full glass-input px-3.5 py-2.5 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1.5">Rate Limit (Requests / Minute)</label>
              <input
                type="number"
                min={5}
                max={600}
                value={rateLimitRpm}
                onChange={(e) => setRateLimitRpm(Number(e.target.value))}
                className="w-full glass-input px-3.5 py-2.5 rounded-xl text-xs text-slate-200 focus:outline-none"
              />
            </div>
          </div>
          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-700 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || !newKeyName.trim()}
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
            >
              {creating ? 'Generating...' : 'Create Key'}
            </button>
          </div>
        </form>
      )}

      {/* Keys List Table */}
      <div className="glass-card rounded-2xl overflow-hidden border border-slate-800">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3.5 px-4">Label</th>
              <th className="py-3.5 px-4">API Key Value</th>
              <th className="py-3.5 px-4">Created</th>
              <th className="py-3.5 px-4">Last Used</th>
              <th className="py-3.5 px-4">Requests</th>
              <th className="py-3.5 px-4">Status</th>
              <th className="py-3.5 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {keys.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  No API keys generated yet. Click "Generate New Key" above.
                </td>
              </tr>
            ) : (
              keys.map((k) => {
                const keyToCopy = k.raw_key || k.key_prefix;
                return (
                  <tr key={k.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-white">{k.name}</td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      <div className="flex items-center space-x-2">
                        <span className="text-amber-400 max-w-[180px] truncate select-all">
                          {k.raw_key || k.key_prefix}
                        </span>
                        {k.raw_key && (
                          <button
                            onClick={() => copySecret(k.raw_key!)}
                            className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white"
                            title="Copy full key"
                          >
                            <i className={`bx ${copiedKey === k.raw_key ? 'bx-check text-emerald-400' : 'bx-copy'}`}></i>
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-400">{formatDate(k.created_at)}</td>
                    <td className="py-3.5 px-4 text-slate-400">{formatDate(k.last_used_at)}</td>
                    <td className="py-3.5 px-4 font-mono text-indigo-400">{k.request_count}</td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                        k.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                      }`}>
                        {k.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleToggle(k.id)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-all"
                      >
                        {k.is_active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        onClick={() => handleRevoke(k.id)}
                        className="px-2.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-xs font-medium transition-all"
                        title="Permanently Revoke"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
