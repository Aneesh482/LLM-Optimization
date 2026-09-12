import React, { useEffect, useState } from "react";
import {
  Plus,
  RefreshCw,
  Search,
  Eye,
} from "lucide-react";
import { api } from "../lib/api";
import { Card, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { formatBytes, formatNumber } from "../lib/utils";
import type { ContextDetail, ContextRetrieveResponse } from "../types";

export function ContextStorage() {
  const [contexts, setContexts] = useState<ContextDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Store Context Modal
  const [isStoreModalOpen, setIsStoreModalOpen] = useState(false);
  const [newContent, setNewContent] = useState("");
  const [newContentType, setNewContentType] = useState("json");
  const [newDescription, setNewDescription] = useState("");
  const [isStoring, setIsStoring] = useState(false);

  // Retrieve & Preview Modal
  const [selectedContext, setSelectedContext] = useState<ContextDetail | null>(null);
  const [retrievedContent, setRetrievedContent] = useState<ContextRetrieveResponse | null>(null);
  const [isRetrieving, setIsRetrieving] = useState(false);

  const loadContexts = async () => {
    try {
      setIsLoading(true);
      const res = await api.getContexts();
      setContexts(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error("Failed to load contexts", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadContexts();
  }, []);

  const handleStore = async () => {
    if (!newContent.trim()) return;
    try {
      setIsStoring(true);
      await api.storeContext({
        content: newContent,
        content_type: newContentType,
        description: newDescription || undefined,
      });
      setIsStoreModalOpen(false);
      setNewContent("");
      setNewDescription("");
      loadContexts();
    } catch (err) {
      console.error("Failed to store context", err);
    } finally {
      setIsStoring(false);
    }
  };

  const handleRetrieve = async (ctx: ContextDetail) => {
    setSelectedContext(ctx);
    try {
      setIsRetrieving(true);
      const res = await api.retrieveOriginalContext(ctx.context_id);
      setRetrievedContent(res);
    } catch (err) {
      console.error("Failed to retrieve verbatim context", err);
    } finally {
      setIsRetrieving(false);
    }
  };

  const filteredContexts = contexts.filter((c) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      c.context_id.toLowerCase().includes(term) ||
      c.content_type.toLowerCase().includes(term) ||
      (c.description && c.description.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Context Storage
          </h1>
          <p className="text-xs text-muted-foreground">
            SQLite repository for Compress - Cache - Retrieve (CCR) payloads and reference tokens.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadContexts} isLoading={isLoading}>
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>
          <Button size="sm" onClick={() => setIsStoreModalOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            <span>Store Context</span>
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search contexts by ID or type..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full rounded border border-border bg-card pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/20 text-muted-foreground font-mono">
                  <th className="py-2.5 px-4 font-medium">Context ID</th>
                  <th className="py-2.5 px-4 font-medium">Type</th>
                  <th className="py-2.5 px-4 font-medium">Description</th>
                  <th className="py-2.5 px-4 font-medium">Original Size</th>
                  <th className="py-2.5 px-4 font-medium">Compressed</th>
                  <th className="py-2.5 px-4 font-medium">Tokens Saved</th>
                  <th className="py-2.5 px-4 font-medium">Access Count</th>
                  <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono">
                {filteredContexts.length > 0 ? (
                  filteredContexts.map((ctx) => (
                    <tr key={ctx.context_id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2.5 px-4 text-primary font-medium">
                        [CCR:{ctx.context_id}]
                      </td>
                      <td className="py-2.5 px-4 uppercase text-foreground">
                        <Badge variant="outline">
                          {ctx.content_type}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground font-sans truncate max-w-xs">
                        {ctx.description || "—"}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {formatBytes(ctx.original_size)}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {formatBytes(ctx.compressed_size)} ({(ctx.compression_ratio * 100).toFixed(0)}%)
                      </td>
                      <td className="py-2.5 px-4 text-emerald-400 font-semibold">
                        {formatNumber(ctx.estimated_tokens_saved)}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {ctx.access_count}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRetrieve(ctx)}
                          className="h-7 px-2 text-xs"
                        >
                          <Eye className="h-3.5 w-3.5 mr-1" />
                          <span>View</span>
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-muted-foreground font-sans">
                      {isLoading ? "Loading stored contexts..." : "No contexts stored in CCR yet."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Store Context Modal */}
      <Modal
        isOpen={isStoreModalOpen}
        onClose={() => setIsStoreModalOpen(false)}
        title="Store New Context"
        description="Compress large payload and persist verbatim original in SQLite."
        maxWidth="xl"
      >
        <div className="space-y-4 text-xs font-sans">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-medium text-foreground mb-1">Content Type</label>
              <select
                value={newContentType}
                onChange={(e) => setNewContentType(e.target.value)}
                className="w-full rounded border border-border bg-background p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="json">JSON (SmartCrusher)</option>
                <option value="code">Source Code (AST / Skeleton)</option>
                <option value="logs">Server Logs (Deduplicator)</option>
                <option value="conversation">Conversation History</option>
                <option value="text">Plain Text</option>
              </select>
            </div>
            <div>
              <label className="block font-medium text-foreground mb-1">Description (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Q3 Analytics Payload"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="w-full rounded border border-border bg-background p-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>

          <div>
            <label className="block font-medium text-foreground mb-1">Payload Content</label>
            <textarea
              rows={8}
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Paste raw content here..."
              className="w-full font-mono text-xs rounded border border-border bg-background p-3 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button variant="outline" size="sm" onClick={() => setIsStoreModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleStore} isLoading={isStoring} disabled={!newContent.trim()}>
              Store & Compress
            </Button>
          </div>
        </div>
      </Modal>

      {/* Retrieve & Inspect Modal */}
      {selectedContext && (
        <Modal
          isOpen={!!selectedContext}
          onClose={() => {
            setSelectedContext(null);
            setRetrievedContent(null);
          }}
          title={`Context: ${selectedContext.context_id}`}
          description={`Reference Token: [CCR:${selectedContext.context_id}]`}
          maxWidth="4xl"
        >
          <div className="space-y-4 text-xs font-mono">
            <div className="grid grid-cols-4 gap-3 bg-muted/20 p-3 rounded border border-border text-center">
              <div>
                <span className="text-muted-foreground text-[11px]">Type</span>
                <p className="font-bold text-foreground mt-0.5 uppercase">{selectedContext.content_type}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-[11px]">Original Size</span>
                <p className="font-bold text-foreground mt-0.5">{formatBytes(selectedContext.original_size)}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-[11px]">Compressed Size</span>
                <p className="font-bold text-primary mt-0.5">{formatBytes(selectedContext.compressed_size)}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-[11px]">Tokens Saved</span>
                <p className="font-bold text-emerald-400 mt-0.5">{formatNumber(selectedContext.estimated_tokens_saved)}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-1.5 font-sans">
                  <span className="font-semibold text-foreground">Compressed Representation</span>
                  <span className="text-xs text-muted-foreground">Sent to Gemini</span>
                </div>
                <textarea
                  rows={12}
                  readOnly
                  value={selectedContext.compressed_content}
                  className="w-full font-mono text-xs rounded border border-border bg-card p-3 text-muted-foreground focus:outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5 font-sans">
                  <span className="font-semibold text-foreground">Verbatim Original Payload</span>
                  <span className="text-xs text-emerald-400">Stored in SQLite</span>
                </div>
                <textarea
                  rows={12}
                  readOnly
                  value={isRetrieving ? "Loading verbatim payload..." : retrievedContent?.original_content || ""}
                  className="w-full font-mono text-xs rounded border border-border bg-card p-3 text-foreground focus:outline-none"
                />
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
