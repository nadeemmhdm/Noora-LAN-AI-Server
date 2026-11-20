import React, { useState, useEffect } from 'react';
import { ModelItem, CatalogModel, DownloadProgress, ServerStatus } from '../types';
import { api } from '../services/api';

interface ModelsViewProps {
  status: ServerStatus | null;
  refreshStatus: () => void;
}

export const ModelsView: React.FC<ModelsViewProps> = ({ status, refreshStatus }) => {
  const [models, setModels] = useState<ModelItem[]>([]);
  const [catalog, setCatalog] = useState<CatalogModel[]>([]);
  const [downloads, setDownloads] = useState<Record<string, DownloadProgress>>({});
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const fetchModelsAndCatalog = async () => {
    try {
      const [mList, cList, dlStatus] = await Promise.all([
        api.getModels(),
        api.getCatalog(),
        api.getDownloadStatus()
      ]);
      setModels(mList);
      setCatalog(cList);
      setDownloads(dlStatus);
    } catch (e: any) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchModelsAndCatalog();
    const timer = setInterval(() => {
      api.getDownloadStatus().then(dl => {
        setDownloads(dl);
        // If any completed, refresh models list
        if (Object.values(dl).some(d => d.status === 'completed')) {
          api.getModels().then(setModels);
        }
      }).catch(() => {});
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  const handleSetActive = async (id: number) => {
    try {
      setLoading(true);
      const res = await api.setActiveModel(id);
      setActionMsg(res.message);
      await fetchModelsAndCatalog();
      refreshStatus();
      setTimeout(() => setActionMsg(null), 3000);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this model file from disk?')) return;
    try {
      setLoading(true);
      const res = await api.deleteModel(id);
      setActionMsg(res.message);
      await fetchModelsAndCatalog();
      refreshStatus();
      setTimeout(() => setActionMsg(null), 3000);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (catalogId: string) => {
    try {
      const res = await api.downloadModel(catalogId);
      setActionMsg(res.message);
      setTimeout(() => setActionMsg(null), 3000);
      const dl = await api.getDownloadStatus();
      setDownloads(dl);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const formatBytes = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(2)} GB`;
    }
    return `${mb.toFixed(0)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <i className="bx bx-chip text-indigo-400"></i>
            GGUF Model Management
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Optimized for CPU-based inference on Intel Core i5 with 4GB RAM.
          </p>
        </div>

        {/* System Memory Safeguard Pill */}
        <div className="px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-center space-x-3">
          <div className="text-right">
            <span className="text-[11px] text-slate-400 block font-medium">Free System RAM</span>
            <span className="text-sm font-bold text-emerald-400 font-mono">
              {status?.system_ram_free_mb ? `${(status.system_ram_free_mb / 1024).toFixed(2)} GB` : 'Safe'}
            </span>
          </div>
          <i className="bx bx-shield-quarter text-2xl text-emerald-400"></i>
        </div>
      </div>

      {actionMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium flex items-center space-x-2">
          <i className="bx bx-check-circle text-base"></i>
          <span>{actionMsg}</span>
        </div>
      )}

      {/* Installed Models Section */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Installed Models ({models.length})
        </h3>

        {models.length === 0 ? (
          <div className="glass-card p-8 rounded-2xl text-center">
            <i className="bx bx-folder-open text-4xl text-slate-500 mb-2"></i>
            <p className="text-sm text-slate-400">No local GGUF models found in the models directory.</p>
            <p className="text-xs text-slate-500 mt-1">Download one from the curated catalog below.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {models.map((m) => {
              const isActive = m.is_active === 1;
              return (
                <div
                  key={m.id}
                  className={`glass-card p-5 rounded-2xl border transition-all ${
                    isActive ? 'border-indigo-500/50 bg-indigo-950/20 shadow-lg shadow-indigo-500/10' : 'border-slate-800'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-base font-bold text-white">{m.name}</h4>
                        {m.model_id && (
                          <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                            API ID: {m.model_id}
                          </span>
                        )}
                        {isActive && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Active
                          </span>
                        )}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-medium text-emerald-400">
                          ✨ Developed & Trained by Nadeem
                        </span>
                        {m.capability && (
                          <span className="text-[11px] text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            🎯 {m.capability}
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-mono text-slate-500 mt-1 truncate max-w-xs">{m.filename}</p>
                    </div>
                    <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {formatBytes(m.size_bytes)}
                    </span>
                  </div>

                  <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-xs text-slate-500">Format: {m.format}</span>
                    <div className="flex items-center space-x-2">
                      {!isActive ? (
                        <button
                          onClick={() => handleSetActive(m.id)}
                          disabled={loading}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all active:scale-95 disabled:opacity-50"
                        >
                          Set as Active
                        </button>
                      ) : (
                        <span className="text-xs text-indigo-400 font-medium">Currently Selected</span>
                      )}

                      <button
                        onClick={() => handleDelete(m.id)}
                        disabled={loading}
                        className="p-1.5 rounded-lg hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 text-sm transition-all"
                        title="Delete model file"
                      >
                        <i className="bx bx-trash"></i>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Curated Catalog Section */}
      <div className="space-y-4 pt-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Trusted Model Catalog (Curated for 4GB RAM)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {catalog.map((item) => {
            const isInstalled = models.some(m => m.filename === item.filename);
            const dl = downloads[item.filename];
            const isDownloading = dl && dl.status === 'downloading';

            return (
              <div key={item.id} className="glass-card p-5 rounded-2xl flex flex-col justify-between">
                <div>
                  <div className="flex items-start justify-between">
                    <h4 className="text-sm font-bold text-white">{item.name}</h4>
                    <span className="text-xs font-mono text-indigo-400">{item.size_mb} MB</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">{item.description}</p>

                  <div className="mt-3 flex items-center space-x-2 text-[11px] text-slate-400">
                    <i className="bx bx-memory-card text-slate-400"></i>
                    <span>Est. RAM: ~{item.required_ram_mb} MB</span>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800">
                  {isDownloading ? (
                    <div>
                      <div className="flex justify-between text-xs text-indigo-400 mb-1">
                        <span>Downloading...</span>
                        <span>{dl.progress_percent}%</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${dl.progress_percent}%` }}
                        ></div>
                      </div>
                    </div>
                  ) : isInstalled ? (
                    <div className="text-xs text-emerald-400 flex items-center space-x-1.5">
                      <i className="bx bx-check-circle"></i>
                      <span>Installed and ready</span>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleDownload(item.id)}
                      className="w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center space-x-1.5 transition-all active:scale-95 border border-slate-700"
                    >
                      <i className="bx bx-download"></i>
                      <span>Download Model</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
