import axios from "axios";
import type {
  HealthResponse,
  DashboardMetricsResponse,
  RequestListResponse,
  CompressionResponse,
  ContextListResponse,
  ContextDetail,
  ContextRetrieveResponse,
  CacheHierarchyStatus,
  ProviderCacheListResponse,
  ProviderCacheItem,
  TokenAnalysisResult,
} from "../types";

const client = axios.create({
  baseURL: "",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 25000,
});

export const api = {
  // Health
  getHealth: async (): Promise<HealthResponse> => {
    const res = await client.get<HealthResponse>("/health");
    return res.data;
  },

  // Telemetry & Metrics
  getMetrics: async (): Promise<DashboardMetricsResponse> => {
    const res = await client.get<DashboardMetricsResponse>("/api/v1/metrics");
    return res.data;
  },

  // Requests
  getRequests: async (params?: {
    limit?: number;
    offset?: number;
    model?: string;
    status?: string;
  }): Promise<RequestListResponse> => {
    const res = await client.get<RequestListResponse>("/api/v1/requests", { params });
    return res.data;
  },

  // Token Analysis
  analyzeTokens: async (messages: Array<{ role: string; content: string }>): Promise<TokenAnalysisResult> => {
    const res = await client.post<TokenAnalysisResult>("/api/v1/analyze", { messages });
    return res.data;
  },

  // Compression
  compressContent: async (content: string, contentType?: string, options?: Record<string, any>): Promise<CompressionResponse> => {
    const res = await client.post<CompressionResponse>("/api/v1/compress", {
      content,
      content_type: contentType,
      options,
    });
    return res.data;
  },

  // CCR Context Storage
  getContexts: async (limit = 50, offset = 0): Promise<ContextListResponse> => {
    const res = await client.get<ContextListResponse>("/api/v1/contexts", { params: { limit, offset } });
    return res.data;
  },

  getContextDetail: async (contextId: string): Promise<ContextDetail> => {
    const res = await client.get<ContextDetail>(`/api/v1/context/${contextId}`);
    return res.data;
  },

  retrieveOriginalContext: async (contextId: string): Promise<ContextRetrieveResponse> => {
    const res = await client.post<ContextRetrieveResponse>(`/api/v1/context/${contextId}/retrieve`);
    return res.data;
  },

  storeContext: async (payload: {
    content: string;
    content_type?: string;
    description?: string;
  }): Promise<ContextDetail> => {
    const res = await client.post<ContextDetail>("/api/v1/context/store", payload);
    return res.data;
  },

  // Multi-Tier Cache & Provider Caching
  getCacheStatus: async (): Promise<CacheHierarchyStatus> => {
    const res = await client.get<CacheHierarchyStatus>("/api/v1/cache/status");
    return res.data;
  },

  getProviderCaches: async (): Promise<ProviderCacheListResponse> => {
    const res = await client.get<ProviderCacheListResponse>("/api/v1/cache/provider");
    return res.data;
  },

  createProviderCache: async (payload: {
    messages: Array<{ role: string; content: string }>;
    model?: string;
    ttl_seconds?: number;
    display_name?: string;
  }): Promise<ProviderCacheItem> => {
    const res = await client.post<ProviderCacheItem>("/api/v1/cache/provider/create", payload);
    return res.data;
  },

  deleteProviderCache: async (cacheName: string): Promise<{ status: string; cache_name: string }> => {
    const res = await client.delete<{ status: string; cache_name: string }>(`/api/v1/cache/provider/${cacheName}`);
    return res.data;
  },

  // Chat completions (Playground)
  sendChatCompletion: async (payload: import("../types").ChatCompletionRequest): Promise<import("../types").ChatCompletionResponse> => {
    const res = await client.post<import("../types").ChatCompletionResponse>("/api/v1/chat/completions", payload);
    return res.data;
  },

  // Context window optimization
  optimizeContext: async (payload: import("../types").OptimizeContextRequest): Promise<import("../types").OptimizeContextResponse> => {
    const res = await client.post<import("../types").OptimizeContextResponse>("/api/v1/context/optimize", payload);
    return res.data;
  },
};
