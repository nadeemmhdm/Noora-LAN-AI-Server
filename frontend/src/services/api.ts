import type {
  ServerStatus, ModelItem, CatalogModel, DownloadProgress,
  ApiKeyItem, DeviceItem, RequestLogItem, SystemLogItem, FirewallStatus
} from '../types';

const BASE_URL = '';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {})
    }
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || err.message || msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  // Server controls
  getStatus: () => fetchJson<ServerStatus>('/api/server/status'),
  getHardware: () => fetchJson<{
    cpu_model: string;
    physical_cores: number;
    logical_cores: number;
    recommended_threads: number;
    system_ram_gb: number;
    available_ram_gb: number;
  }>('/api/hardware'),
  startServer: () => fetchJson<{ success: boolean; message: string; status: string }>('/api/server/start', { method: 'POST' }),
  stopServer: () => fetchJson<{ success: boolean; message: string; status: string }>('/api/server/stop', { method: 'POST' }),
  restartServer: () => fetchJson<{ success: boolean; message: string; status: string }>('/api/server/restart', { method: 'POST' }),

  // Models
  getModels: () => fetchJson<ModelItem[]>('/api/models'),
  setActiveModel: (id: number) => fetchJson<{ success: boolean; message: string }>('/api/models/active', {
    method: 'POST',
    body: JSON.stringify({ id })
  }),
  deleteModel: (id: number) => fetchJson<{ success: boolean; message: string }>(`/api/models/${id}`, { method: 'DELETE' }),
  getCatalog: () => fetchJson<CatalogModel[]>('/api/models/catalog'),
  getDownloadStatus: () => fetchJson<Record<string, DownloadProgress>>('/api/models/download/status'),
  downloadModel: (catalog_id: string) => fetchJson<{ success: boolean; message: string }>('/api/models/download', {
    method: 'POST',
    body: JSON.stringify({ catalog_id })
  }),

  // API Keys
  getKeys: () => fetchJson<ApiKeyItem[]>('/api/keys'),
  getActiveKeyInfo: () => fetchJson<{
    active_key: any;
    raw_key: string;
    base_url: string;
    model: string;
    quick_curl: string;
    python_sample: string;
  }>('/api/keys/active'),
  createKey: (name: string, rate_limit_rpm: number = 120) => fetchJson<{ success: boolean; raw_key: string; record: ApiKeyItem }>('/api/keys/create', {
    method: 'POST',
    body: JSON.stringify({ name, rate_limit_rpm })
  }),
  toggleKey: (id: number) => fetchJson<{ success: boolean; is_active: number }>(`/api/keys/${id}/toggle`, { method: 'POST' }),
  revokeKey: (id: number) => fetchJson<{ success: boolean; message: string }>(`/api/keys/${id}`, { method: 'DELETE' }),

  // Devices
  getDevices: () => fetchJson<DeviceItem[]>('/api/devices'),
  blockDevice: (ip: string) => fetchJson<{ success: boolean; message: string }>(`/api/devices/${ip}/block`, { method: 'POST' }),
  unblockDevice: (ip: string) => fetchJson<{ success: boolean; message: string }>(`/api/devices/${ip}/unblock`, { method: 'POST' }),

  // Logs
  getRequestLogs: (limit = 50, offset = 0) => fetchJson<{ total: number; items: RequestLogItem[] }>(`/api/logs/requests?limit=${limit}&offset=${offset}`),
  getSystemLogs: (limit = 100) => fetchJson<SystemLogItem[]>(`/api/logs/system?limit=${limit}`),
  clearLogs: () => fetchJson<{ success: boolean; message: string }>('/api/logs/clear', { method: 'POST' }),

  // Network & Firewall
  getInterfaces: () => fetchJson<{ interfaces: any[]; primary_lan_ip: string }>('/api/network/interfaces'),
  getFirewallStatus: () => fetchJson<FirewallStatus>('/api/firewall/status'),
  configureFirewall: (action: 'add' | 'remove') => fetchJson<{ success: boolean; message: string }>('/api/firewall/configure', {
    method: 'POST',
    body: JSON.stringify({ action })
  }),

  // Settings
  getSettings: () => fetchJson<Record<string, string>>('/api/settings'),
  updateSettings: (settings: Record<string, string>) => fetchJson<{ success: boolean; message: string }>('/api/settings', {
    method: 'POST',
    body: JSON.stringify(settings)
  })
};
