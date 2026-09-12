import React, { useEffect, useState } from "react";
import {
  Trash2,
  Plus,
  RefreshCw,
} from "lucide-react";
import { api } from "../lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { formatNumber, formatPercentage } from "../lib/utils";
import type { CacheHierarchyStatus, ProviderCacheItem } from "../types";

export function Providers() {
  const [hierarchy, setHierarchy] = useState<CacheHierarchyStatus | null>(null);
  const [providerCaches, setProviderCaches] = useState<ProviderCacheItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Create Provider Cache Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [cacheName, setCacheName] = useState("");
  const [cacheModel, setCacheModel] = useState("gemini-3.6-flash");
  const [cacheTtl, setCacheTtl] = useState(300);
  const [cacheContent, setCacheContent] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [h, c] = await Promise.all([
        api.getCacheStatus(),
        api.getProviderCaches().catch(() => ({ total: 0, items: [] })),
      ]);
      setHierarchy(h);
      setProviderCaches(c.items);
    } catch (err) {
      console.error("Failed to load provider cache data", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateCache = async () => {
    setCreateError(null);
    if (!cacheContent.trim()) return;

    try {
      setIsCreating(true);
      await api.createProviderCache({
        messages: [{ role: "user", content: cacheContent }],
        model: cacheModel,
        ttl_seconds: cacheTtl,
        display_name: cacheName || undefined,
      });
      setIsCreateModalOpen(false);
      setCacheContent("");
      setCacheName("");
      loadData();
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || "Failed to create Gemini context cache.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteCache = async (cacheResourceName: string) => {
    try {
      await api.deleteProviderCache(cacheResourceName);
      loadData();
    } catch (err) {
      console.error("Failed to delete cache", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Providers & Cache
          </h1>
          <p className="text-xs text-muted-foreground">
            Multi-tier cache hierarchy and Gemini server-side context caching.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadData} isLoading={isLoading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>
          <Button size="sm" onClick={() => setIsCreateModalOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            <span>Create Gemini Cache</span>
          </Button>
        </div>
      </div>

      {/* 3-Tier Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Tier 1 */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <Badge variant="outline">Tier 1</Badge>
              <span className="text-xs text-muted-foreground font-mono">In-Memory</span>
            </div>
            <CardTitle className="text-sm font-semibold mt-1">Gateway RAM Cache</CardTitle>
            <CardDescription>Exact-match prompt completion cache</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-border">
              <span className="text-muted-foreground">Entries</span>
              <span className="text-foreground font-semibold">
                {hierarchy?.tier_1_in_memory_gateway_cache.cached_entries || 0} / {hierarchy?.tier_1_in_memory_gateway_cache.max_capacity || 200}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border">
              <span className="text-muted-foreground">Hits / Misses</span>
              <span className="text-foreground">
                {hierarchy?.tier_1_in_memory_gateway_cache.cache_hits || 0} / {hierarchy?.tier_1_in_memory_gateway_cache.cache_misses || 0}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-muted-foreground">Hit Rate</span>
              <span className="text-emerald-400 font-bold">
                {formatPercentage(hierarchy?.tier_1_in_memory_gateway_cache.hit_ratio || 0)}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Tier 2 */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <Badge variant="outline">Tier 2</Badge>
              <span className="text-xs text-muted-foreground font-mono">SQLite DB</span>
            </div>
            <CardTitle className="text-sm font-semibold mt-1">CCR Storage</CardTitle>
            <CardDescription>Persistent compressed context repository</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-border">
              <span className="text-muted-foreground">Contexts</span>
              <span className="text-foreground font-semibold">
                {hierarchy?.tier_2_ccr_sqlite_storage.stored_contexts || 0} Stored
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border">
              <span className="text-muted-foreground">Storage Backend</span>
              <span className="text-foreground">SQLite</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-muted-foreground">Access Mode</span>
              <span className="text-primary font-bold">On-Demand</span>
            </div>
          </CardContent>
        </Card>

        {/* Tier 3 */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <Badge variant="success">Tier 3</Badge>
              <span className="text-xs text-muted-foreground font-mono">Google GenAI</span>
            </div>
            <CardTitle className="text-sm font-semibold mt-1">Gemini Context Cache</CardTitle>
            <CardDescription>Server-side prompt caches hosted at Google</CardDescription>
          </CardHeader>
          <CardContent className="space-y-1 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-border">
              <span className="text-muted-foreground">Active Caches</span>
              <span className="text-foreground font-semibold">
                {hierarchy?.tier_3_provider_context_caching.active_provider_caches || 0} Caches
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border">
              <span className="text-muted-foreground">Provider</span>
              <span className="text-foreground">Google Gemini API</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-muted-foreground">Status</span>
              <span className="text-emerald-400 font-bold">Supported</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gemini Caches Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold">Active Gemini Server Caches</CardTitle>
            <Badge variant="outline">{providerCaches.length} active</Badge>
          </div>
          <CardDescription>
            Prompt caches hosted directly on Google infrastructure to eliminate repeated input token charges.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/20 text-muted-foreground font-mono">
                  <th className="py-2.5 px-4 font-medium">Cache Name</th>
                  <th className="py-2.5 px-4 font-medium">Model</th>
                  <th className="py-2.5 px-4 font-medium">Display Name</th>
                  <th className="py-2.5 px-4 font-medium">Cached Tokens</th>
                  <th className="py-2.5 px-4 font-medium">Expire Time</th>
                  <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono">
                {providerCaches.length > 0 ? (
                  providerCaches.map((c) => (
                    <tr key={c.name} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2.5 px-4 text-primary font-medium">{c.name}</td>
                      <td className="py-2.5 px-4 text-foreground">{c.model}</td>
                      <td className="py-2.5 px-4 text-muted-foreground">{c.display_name || "—"}</td>
                      <td className="py-2.5 px-4 text-emerald-400 font-semibold">
                        {c.cached_tokens ? formatNumber(c.cached_tokens) : "Dynamic"}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {c.expire_time ? new Date(c.expire_time).toLocaleTimeString() : "—"}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteCache(c.name)}
                          className="h-7 px-2 text-xs"
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" />
                          <span>Delete</span>
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground font-sans">
                      No active Gemini server-side caches. Create one to cache long documents.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Create Gemini Context Cache Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Gemini Server Cache"
        description="Creates a cachedContents resource in Google Gemini to reuse context."
        maxWidth="xl"
      >
        <div className="space-y-4 text-xs font-sans">
          {createError && (
            <div className="text-xs text-rose-400 bg-rose-950/20 border border-rose-800/30 p-2.5 rounded">
              {createError}
            </div>
          )}

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block font-medium text-foreground mb-1">Display Name</label>
              <input
                type="text"
                placeholder="e.g. system-docs"
                value={cacheName}
                onChange={(e) => setCacheName(e.target.value)}
                className="w-full rounded border border-border bg-background p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
            <div>
              <label className="block font-medium text-foreground mb-1">Model</label>
              <select
                value={cacheModel}
                onChange={(e) => setCacheModel(e.target.value)}
                className="w-full rounded border border-border bg-background p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
              >
                <option value="gemini-3.6-flash">gemini-3.6-flash</option>
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              </select>
            </div>
            <div>
              <label className="block font-medium text-foreground mb-1">TTL (Seconds)</label>
              <input
                type="number"
                min={60}
                max={86400}
                value={cacheTtl}
                onChange={(e) => setCacheTtl(Number(e.target.value))}
                className="w-full rounded border border-border bg-background p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block font-medium text-foreground mb-1">Content to Cache</label>
            <textarea
              rows={8}
              value={cacheContent}
              onChange={(e) => setCacheContent(e.target.value)}
              placeholder="Paste large system instructions or reference document here..."
              className="w-full font-mono text-xs rounded border border-border bg-background p-3 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button variant="outline" size="sm" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleCreateCache} isLoading={isCreating} disabled={!cacheContent.trim()}>
              Create Cache
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
