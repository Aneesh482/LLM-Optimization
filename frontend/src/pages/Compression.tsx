import React, { useState } from "react";
import {
  Play,
  Copy,
  Check,
  FileCode,
  FileJson,
  FileText,
} from "lucide-react";
import { api } from "../lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { formatBytes, formatNumber, formatPercentage } from "../lib/utils";
import type { CompressionResponse } from "../types";

const SAMPLE_JSON = JSON.stringify(
  Array.from({ length: 40 }).map((_, i) => ({
    id: i + 1,
    event_type: i === 12 ? "CRITICAL_PAYMENT_FAILURE" : "api_request_success",
    latency_ms: i === 12 ? 4500 : 120 + (i % 5) * 10,
    status_code: i === 12 ? 500 : 200,
    user_id: `usr_${1000 + (i % 8)}`,
    region: "us-east-1",
    metadata: { env: "prod", cluster: "primary" },
  })),
  null,
  2
);

const SAMPLE_CODE = `import os
import sys
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class PaymentGatewayClient:
    """Manages secure communication with the upstream payment processor."""

    def __init__(self, api_key: str, timeout: int = 30) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self._session = None

    def connect(self) -> bool:
        """Initialize HTTP connection pool."""
        logger.info("Initializing payment connection...")
        for i in range(10):
            pass
        return True

    def process_charge(self, customer_id: str, amount_cents: int, currency: str = "USD") -> Dict[str, str]:
        """Submit a single charge transaction."""
        if amount_cents <= 0:
            raise ValueError("Amount must be positive")
        return {"status": "approved", "tx_id": "tx_9999"}
`;

const SAMPLE_LOGS = `2026-09-10 10:14:00.123 [INFO] 192.168.1.101 GET /api/v1/health 200 OK 12ms 4c9f1a20-3b4d-4e5f-a678-9b0c1d2e3f4a
2026-09-10 10:14:01.450 [INFO] 192.168.1.102 GET /api/v1/health 200 OK 10ms 5d0a2b31-4c5e-5f6a-b789-0c1d2e3f4a5b
2026-09-10 10:14:02.780 [INFO] 192.168.1.103 GET /api/v1/health 200 OK 14ms 6e1b3c42-5d6f-6a7b-c890-1d2e3f4a5b6c
2026-09-10 10:14:03.900 [INFO] 192.168.1.104 GET /api/v1/health 200 OK 11ms 7f2c4d53-6e7a-7b8c-d901-2e3f4a5b6c7d
2026-09-10 10:14:04.110 [WARN] 192.168.1.105 High memory watermark reached (89.2% utilized)
2026-09-10 10:14:05.220 [ERROR] 192.168.1.106 Database connection pool exhausted: Timeout after 5000ms
Traceback (most recent call last):
  File "server.py", line 42, in get_connection
    conn = pool.acquire(timeout=5)
TimeoutError: Resource pool exhausted
2026-09-10 10:14:06.330 [INFO] 192.168.1.107 GET /api/v1/health 200 OK 9ms 8a3d5e64-7f8b-8c9d-ea12-3f4a5b6c7d8e`;

export function Compression() {
  const [content, setContent] = useState<string>(SAMPLE_JSON);
  const [selectedType, setSelectedType] = useState<string>("auto");
  const [result, setResult] = useState<CompressionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCompress = async () => {
    setErrorMsg(null);
    try {
      setIsLoading(true);
      const res = await api.compressContent(
        content,
        selectedType !== "auto" ? selectedType : undefined
      );
      setResult(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Compression failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const loadSample = (sampleText: string, type: string) => {
    setContent(sampleText);
    setSelectedType(type);
    setResult(null);
    setErrorMsg(null);
  };

  const handleCopy = () => {
    if (result) {
      navigator.clipboard.writeText(result.compressed_content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Compression
        </h1>
        <p className="text-xs text-muted-foreground">
          Test intelligent compressors for JSON (SmartCrusher), Source Code, and Server Logs.
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-card p-3 rounded border border-border">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-medium">Load sample:</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadSample(SAMPLE_JSON, "json")}
            className="h-7 text-xs gap-1"
          >
            <FileJson className="h-3.5 w-3.5 text-blue-400" />
            <span>JSON</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadSample(SAMPLE_CODE, "code")}
            className="h-7 text-xs gap-1"
          >
            <FileCode className="h-3.5 w-3.5 text-emerald-400" />
            <span>Code</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadSample(SAMPLE_LOGS, "logs")}
            className="h-7 text-xs gap-1"
          >
            <FileText className="h-3.5 w-3.5 text-amber-400" />
            <span>Logs</span>
          </Button>
        </div>

        <div className="flex items-center gap-1 bg-background border border-border p-0.5 rounded">
          {["auto", "json", "code", "logs"].map((m) => (
            <button
              key={m}
              onClick={() => setSelectedType(m)}
              className={`px-2.5 py-1 text-xs rounded uppercase font-mono transition-colors ${
                selectedType === m
                  ? "bg-secondary text-foreground font-bold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Editor Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Raw Content Input */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-sm font-semibold">Raw Input</CardTitle>
              <CardDescription>{formatBytes(content.length)} payload</CardDescription>
            </div>
            <Button size="sm" onClick={handleCompress} isLoading={isLoading} className="gap-1.5">
              <Play className="h-3.5 w-3.5 fill-current" />
              <span>Compress</span>
            </Button>
          </CardHeader>
          <CardContent className="flex-1 flex flex-col">
            <textarea
              rows={16}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste raw JSON, Code, or Logs here..."
              className="w-full flex-1 font-mono text-xs rounded border border-border bg-background p-3 text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-y"
            />
          </CardContent>
        </Card>

        {/* Compressed Output */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-sm font-semibold">Compressed Output</CardTitle>
              <CardDescription>
                {result
                  ? `${formatBytes(result.compressed_size)} (${formatPercentage(1 - result.compression_ratio)} reduction)`
                  : "Run compression to view output"}
              </CardDescription>
            </div>
            {result && (
              <Button variant="outline" size="sm" onClick={handleCopy} className="h-7 gap-1 text-xs">
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </Button>
            )}
          </CardHeader>
          <CardContent className="flex-1 flex flex-col">
            {errorMsg && (
              <div className="text-xs text-rose-400 bg-rose-950/20 border border-rose-800/30 p-2.5 rounded mb-3">
                {errorMsg}
              </div>
            )}
            <textarea
              rows={16}
              readOnly
              value={result?.compressed_content || ""}
              placeholder="Compressed output will appear here..."
              className="w-full flex-1 font-mono text-xs rounded border border-border bg-card p-3 text-muted-foreground focus:outline-none resize-y"
            />
          </CardContent>
        </Card>
      </div>

      {/* Metrics Bar */}
      {result && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <span className="text-xs text-muted-foreground font-mono">Tokens Saved</span>
              <p className="text-2xl font-bold font-mono text-emerald-400 mt-1">
                {formatNumber(result.estimated_tokens_saved)}
              </p>
              <span className="text-xs text-muted-foreground font-mono">
                {result.estimated_tokens_before} &rarr; {result.estimated_tokens_after}
              </span>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <span className="text-xs text-muted-foreground font-mono">Compression Ratio</span>
              <p className="text-2xl font-bold font-mono text-primary mt-1">
                {(result.compression_ratio * 100).toFixed(1)}%
              </p>
              <span className="text-xs text-muted-foreground">Of original size</span>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <span className="text-xs text-muted-foreground font-mono">Bytes Reduced</span>
              <p className="text-2xl font-bold font-mono text-foreground mt-1">
                {formatBytes(result.original_size - result.compressed_size)}
              </p>
              <span className="text-xs text-muted-foreground font-mono">
                {formatBytes(result.original_size)} &rarr; {formatBytes(result.compressed_size)}
              </span>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <span className="text-xs text-muted-foreground font-mono">Content Type</span>
              <p className="text-2xl font-bold font-mono text-foreground mt-1 uppercase">
                {result.content_type}
              </p>
              <span className="text-xs text-muted-foreground">
                {result.metadata.strategy || "Standard"}
              </span>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
