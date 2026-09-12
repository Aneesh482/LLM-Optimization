import React, { useEffect, useState } from "react";
import {
  Server,
  Key,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Shield,
} from "lucide-react";
import { api } from "../lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import type { HealthResponse } from "../types";

export function Settings() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isChecking, setIsChecking] = useState(false);

  const checkHealth = async () => {
    try {
      setIsChecking(true);
      const res = await api.getHealth();
      setHealth(res);
    } catch {
      setHealth(null);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Settings
        </h1>
        <p className="text-xs text-muted-foreground">
          Gateway runtime status, environment parameters, and provider configuration.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gateway Health & Runtime */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Server className="h-4 w-4 text-muted-foreground" />
              <span>Gateway Runtime</span>
            </CardTitle>
            <CardDescription>Backend server status and active routing</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-xs font-mono">
            <div className="flex items-center justify-between p-3 rounded bg-muted/20 border border-border">
              <div className="flex items-center gap-2">
                {health ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-rose-400" />
                )}
                <span className="font-sans font-medium text-foreground">
                  {health ? "Backend Online" : "Backend Offline"}
                </span>
              </div>
              <Button variant="outline" size="sm" onClick={checkHealth} isLoading={isChecking} className="h-7 text-xs">
                <RefreshCw className={`h-3 w-3 mr-1 ${isChecking ? "animate-spin" : ""}`} />
                <span>Ping</span>
              </Button>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground font-sans">Health Endpoint</span>
                <span className="text-foreground">GET /health</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground font-sans">Completions Endpoint</span>
                <span className="text-foreground">POST /api/v1/chat/completions</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground font-sans">Database</span>
                <span className="text-foreground">SQLite (aiosqlite)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground font-sans">Version</span>
                <span className="text-foreground">0.1.0</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Gemini Provider Authentication */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Key className="h-4 w-4 text-muted-foreground" />
              <span>Gemini Provider</span>
            </CardTitle>
            <CardDescription>Google GenAI Python SDK integration configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-xs font-mono">
            <div className="p-3 bg-muted/20 rounded border border-border">
              <div className="flex items-center justify-between font-sans">
                <span className="font-medium text-foreground">GEMINI_API_KEY</span>
                <Badge variant="success">Active in .env</Badge>
              </div>
              <p className="text-muted-foreground text-xs font-sans mt-1">
                Managed on the backend via environment variables. Never exposed to browser clients.
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground font-sans">Default Model</span>
                <span className="text-foreground font-semibold">gemini-3.6-flash</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border">
                <span className="text-muted-foreground font-sans">SDK Package</span>
                <span className="text-foreground">google-genai</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground font-sans">Provider Mode</span>
                <span className="text-foreground">Agnostic Base Adapter</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gateway Architecture Notes */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <span>Architecture Notes</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs space-y-3 font-sans text-muted-foreground leading-relaxed">
          <p>
            The LLM Gateway acts as an intelligent proxy between applications and Google Gemini. Requests undergo content routing (JSON, Code, Logs), token analysis, and compression before dispatch.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs pt-1">
            <div className="p-3 bg-card rounded border border-border">
              <span className="font-semibold text-foreground font-sans block mb-1">CCR Storage</span>
              <span>Archives large verbatim payloads in SQLite and sends compact references to Gemini.</span>
            </div>
            <div className="p-3 bg-card rounded border border-border">
              <span className="font-semibold text-foreground font-sans block mb-1">Safety Guardrails</span>
              <span>Automatic rollback ensures compressed representation never exceeds original verbatim size.</span>
            </div>
            <div className="p-3 bg-card rounded border border-border">
              <span className="font-semibold text-foreground font-sans block mb-1">Multi-Tier Caching</span>
              <span>Combines in-memory RAM caching, SQLite CCR storage, and Gemini server-side context caching.</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
