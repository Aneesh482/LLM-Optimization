import React, { useEffect, useState } from "react";
import {
  Search,
  RefreshCw,
  Eye,
  AlertCircle,
} from "lucide-react";
import { api } from "../lib/api";
import { Card, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Modal } from "../components/ui/Modal";
import { formatNumber } from "../lib/utils";
import type { RequestLogItem } from "../types";

export function Requests() {
  const [requests, setRequests] = useState<RequestLogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedRequest, setSelectedRequest] = useState<RequestLogItem | null>(null);

  const loadRequests = async () => {
    try {
      setIsLoading(true);
      const res = await api.getRequests({
        limit: 100,
        status: statusFilter !== "all" ? statusFilter : undefined,
      });
      setRequests(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error("Failed to load requests", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, [statusFilter]);

  const filteredRequests = requests.filter((r) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      r.request_id.toLowerCase().includes(term) ||
      r.model.toLowerCase().includes(term) ||
      (r.error_message && r.error_message.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Requests
          </h1>
          <p className="text-xs text-muted-foreground">
            Audit log of all LLM completions routed through the gateway.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadRequests} isLoading={isLoading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by ID, model, or error..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded border border-border bg-card pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex items-center gap-1 bg-card border border-border p-0.5 rounded">
          {["all", "success", "error"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 text-xs rounded capitalize font-medium transition-colors ${
                statusFilter === st
                  ? "bg-secondary text-foreground font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/20 text-muted-foreground font-mono">
                  <th className="py-2.5 px-4 font-medium">Request ID</th>
                  <th className="py-2.5 px-4 font-medium">Time</th>
                  <th className="py-2.5 px-4 font-medium">Model</th>
                  <th className="py-2.5 px-4 font-medium">Status</th>
                  <th className="py-2.5 px-4 font-medium">In Tokens</th>
                  <th className="py-2.5 px-4 font-medium">Out Tokens</th>
                  <th className="py-2.5 px-4 font-medium">Total</th>
                  <th className="py-2.5 px-4 font-medium">Latency</th>
                  <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono">
                {filteredRequests.length > 0 ? (
                  filteredRequests.map((req) => (
                    <tr key={req.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2.5 px-4 text-foreground font-medium">
                        {req.request_id}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {new Date(req.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="py-2.5 px-4 text-foreground">{req.model}</td>
                      <td className="py-2.5 px-4">
                        <Badge variant={req.status === "success" ? "success" : "destructive"}>
                          {req.status}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {formatNumber(req.input_tokens || 0)}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {formatNumber(req.output_tokens || 0)}
                      </td>
                      <td className="py-2.5 px-4 text-foreground font-semibold">
                        {formatNumber(req.total_tokens || 0)}
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground">
                        {req.latency_ms ? `${req.latency_ms} ms` : "-"}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedRequest(req)}
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
                    <td colSpan={9} className="py-8 text-center text-muted-foreground font-sans">
                      {isLoading ? "Loading requests..." : "No matching requests found."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Details Modal */}
      {selectedRequest && (
        <Modal
          isOpen={!!selectedRequest}
          onClose={() => setSelectedRequest(null)}
          title="Request Details"
          description={`ID: ${selectedRequest.request_id}`}
          maxWidth="xl"
        >
          <div className="space-y-4 text-xs font-mono">
            <div className="grid grid-cols-2 gap-3 bg-muted/20 p-3 rounded border border-border">
              <div>
                <span className="text-muted-foreground">Model:</span>
                <p className="font-semibold text-foreground mt-0.5">{selectedRequest.model}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Status:</span>
                <p className="mt-0.5">
                  <Badge variant={selectedRequest.status === "success" ? "success" : "destructive"}>
                    {selectedRequest.status}
                  </Badge>
                </p>
              </div>
              <div>
                <span className="text-muted-foreground">Timestamp:</span>
                <p className="text-foreground mt-0.5">{new Date(selectedRequest.timestamp).toISOString()}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Latency:</span>
                <p className="text-foreground mt-0.5">{selectedRequest.latency_ms || 0} ms</p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 bg-muted/20 p-3 rounded border border-border text-center">
              <div>
                <span className="text-muted-foreground text-[11px]">Input Tokens</span>
                <p className="text-base font-bold text-foreground mt-1">{selectedRequest.input_tokens || 0}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-[11px]">Output Tokens</span>
                <p className="text-base font-bold text-foreground mt-1">{selectedRequest.output_tokens || 0}</p>
              </div>
              <div>
                <span className="text-muted-foreground text-[11px]">Total Tokens</span>
                <p className="text-base font-bold text-primary mt-1">{selectedRequest.total_tokens || 0}</p>
              </div>
            </div>

            {selectedRequest.error_message && (
              <div className="space-y-1.5">
                <span className="text-rose-400 font-semibold flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4" />
                  <span>Error Diagnostics:</span>
                </span>
                <pre className="bg-rose-950/20 border border-rose-800/30 text-rose-300 p-3 rounded overflow-x-auto whitespace-pre-wrap">
                  {selectedRequest.error_message}
                </pre>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}
