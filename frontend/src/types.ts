export interface ServerStatus {
  status: "ONLINE" | "OFFLINE" | "STARTING" | "STOPPING" | "ERROR";
  app_name: string;
  ai_name: string;
  developer: string;
  active_model: string;
  active_model_path: string | null;
  uptime_seconds: number;
  engine_memory_mb: number;
  engine_cpu_percent: number;
  system_ram_total_mb: number;
  system_ram_used_mb: number;
  system_ram_free_mb: number;
  system_ram_percent: number;
  system_cpu_percent: number;
  cpu_model?: string;
  cpu_physical_cores?: number;
  cpu_logical_cores?: number;
  threads_used?: number;
  lan_ip: string;
  port: number;
  api_base_url: string;
  active_working_key?: string;
  active_key_prefix?: string;
  is_online?: boolean;
  internet_latency_ms?: number;
  web_search_enabled?: boolean;
  web_search_mode?: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  active_clients: number;
  error_message: string | null;
}

export interface ModelItem {
  id: number;
  name: string;
  model_id?: string;
  capability?: string;
  filename: string;
  path: string;
  size_bytes: number;
  format: string;
  is_active: number;
  downloaded_at: number;
}

export interface CatalogModel {
  id: string;
  name: string;
  filename: string;
  size_mb: number;
  required_ram_mb: number;
  format: string;
  description: string;
  download_url: string;
}

export interface DownloadProgress {
  status: "downloading" | "completed" | "failed";
  progress_percent: number;
  downloaded_mb: number;
  total_mb: number;
  error: string | null;
}

export interface ApiKeyItem {
  id: number;
  name: string;
  key_prefix: string;
  raw_key?: string;
  created_at: number;
  last_used_at: number | null;
  request_count: number;
  is_active: number;
  rate_limit_rpm: number;
}

export interface DeviceItem {
  id: number;
  ip_address: string;
  hostname: string | null;
  first_seen: number;
  last_seen: number;
  request_count: number;
  last_api_key_name: string | null;
  is_blocked: number;
  observed_status: "Active" | "Recent" | "Idle";
}

export interface RequestLogItem {
  id: number;
  timestamp: number;
  client_ip: string;
  endpoint: string;
  method: string;
  status_code: number;
  latency_ms: number;
  tokens_prompt: number;
  tokens_completion: number;
  api_key_name: string | null;
  error_message: string | null;
}

export interface SystemLogItem {
  id: number;
  timestamp: number;
  level: "INFO" | "WARNING" | "ERROR";
  source: string;
  message: string;
}

export interface FirewallStatus {
  supported: boolean;
  exists: boolean;
  rule_name: string;
  port: number;
  details?: string;
  message?: string;
}

export interface WebSearchResult {
  title: string;
  url: string;
  source: string;
  snippet: string;
}

export interface ConnectivityStatus {
  online: boolean;
  latency_ms: number;
  web_search_enabled: boolean;
  web_search_mode: string;
}

export interface KnowledgeDocument {
  id: number;
  filename: string;
  title: string;
  summary: string;
  word_count: number;
  chunk_count: number;
  file_size_bytes: number;
  created_at: number;
  updated_at: number;
}

export interface KnowledgeChunk {
  id: number;
  doc_id: number;
  section_title: string;
  chunk_index: number;
  content: string;
  keywords: string;
  created_at: number;
}

export interface KnowledgeSearchResult {
  doc_id: number;
  filename: string;
  doc_title: string;
  section_title: string;
  chunk_index: number;
  content: string;
  score: number;
}

export interface KnowledgeListResponse {
  documents: KnowledgeDocument[];
  total: number;
  total_chunks: number;
  total_words: number;
}

export interface KnowledgeTrainResult {
  doc_id: number;
  filename: string;
  title: string;
  summary: string;
  word_count: number;
  chunk_count: number;
  file_size_bytes: number;
  chunks_saved: number;
}
