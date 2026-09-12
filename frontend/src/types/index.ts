export interface HealthResponse {
  status: string;
  version: string;
  provider: string;
}

export interface RequestLogItem {
  id: number;
  request_id: string;
  timestamp: string;
  model: string;
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
  latency_ms?: number | null;
  status: 'success' | 'error';
  error_message?: string | null;
}

export interface RequestListResponse {
  total: number;
  items: RequestLogItem[];
}

export interface ModelUsageMetric {
  model: string;
  request_count: number;
  total_tokens: number;
  avg_latency_ms: number;
}

export interface ContentTypeMetric {
  content_type: string;
  count: number;
  total_original_bytes: number;
  total_compressed_bytes: number;
  total_tokens_saved: number;
  avg_compression_ratio: number;
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  tokens_saved: number;
  avg_latency_ms: number;
}

export interface DashboardMetricsResponse {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_tokens_saved: number;
  avg_latency_ms: number;
  avg_compression_ratio: number;
  estimated_cost_usd: number;
  estimated_cost_saved_usd: number;
  models_usage: ModelUsageMetric[];
  content_types_breakdown: ContentTypeMetric[];
  time_series: TimeSeriesDataPoint[];
}

export interface CompressionResponse {
  content_type: string;
  original_size: number;
  compressed_size: number;
  compression_ratio: number;
  estimated_tokens_before: number;
  estimated_tokens_after: number;
  estimated_tokens_saved: number;
  compressed_content: string;
  metadata: Record<string, any>;
}

export interface ContextDetail {
  context_id: string;
  content_type: string;
  description?: string | null;
  original_size: number;
  compressed_size: number;
  compression_ratio: number;
  estimated_tokens_before: number;
  estimated_tokens_after: number;
  estimated_tokens_saved: number;
  access_count: number;
  created_at: string;
  accessed_at: string;
  compressed_content: string;
  metadata?: Record<string, any>;
}

export interface ContextListResponse {
  total: number;
  items: ContextDetail[];
}

export interface ContextRetrieveResponse {
  context_id: string;
  content_type: string;
  description?: string | null;
  original_content: string;
  original_size: number;
  access_count: number;
  accessed_at: string;
}

export interface ProviderCacheItem {
  name: string;
  model: string;
  display_name?: string | null;
  expire_time?: string | null;
  cached_tokens?: number | null;
}

export interface ProviderCacheListResponse {
  total: number;
  items: ProviderCacheItem[];
}

export interface CacheHierarchyStatus {
  tier_1_in_memory_gateway_cache: {
    cached_entries: number;
    max_capacity: number;
    cache_hits: number;
    cache_misses: number;
    hit_ratio: number;
  };
  tier_2_ccr_sqlite_storage: {
    stored_contexts: number;
    storage_backend: string;
    lifecycle: string;
  };
  tier_3_provider_context_caching: {
    provider: string;
    supported: boolean;
    active_provider_caches: number;
    caches: ProviderCacheItem[];
    error?: string;
  };
}

export interface TokenAnalysisResult {
  total_estimated_tokens: number;
  total_characters: number;
  total_words: number;
  message_count: number;
  role_distribution: Record<string, number>;
  largest_sections: Array<{
    index: number;
    role: string;
    estimated_tokens: number;
    characters: number;
    percentage_of_total: number;
    content_preview: string;
  }>;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface ChatCompletionRequest {
  model?: string;
  messages: ChatMessage[];
  temperature?: number;
  max_output_tokens?: number;
  optimize_context?: boolean;
  max_context_tokens?: number;
  cached_content?: string;
}

export interface ChatCompletionResponse {
  id: string;
  model: string;
  content: string;
  usage: {
    input_tokens?: number | null;
    output_tokens?: number | null;
    total_tokens?: number | null;
    cached_tokens?: number | null;
  };
  latency_ms: number;
  optimization?: {
    original_tokens?: number;
    optimized_tokens?: number;
    tokens_saved?: number;
    compression_ratio?: number;
    summary_injected?: boolean;
    strategy?: string;
    archived_context_id?: string | null;
  } | null;
}

export interface OptimizeContextRequest {
  messages: ChatMessage[];
  max_context_tokens?: number;
  recent_messages_count?: number;
  preserve_system?: boolean;
  archive_to_ccr?: boolean;
}

export interface OptimizeContextResponse {
  optimized_messages: ChatMessage[];
  metrics: {
    original_message_count: number;
    optimized_message_count: number;
    original_tokens: number;
    optimized_tokens: number;
    tokens_saved: number;
    compression_ratio: number;
    summary_injected: boolean;
    archived_context_id?: string | null;
  };
  metadata: Record<string, any>;
}
