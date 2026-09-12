import React, { useEffect, useState } from "react";
import { RefreshCw, Server } from "lucide-react";
import { api } from "../../lib/api";
import type { HealthResponse } from "../../types";

export function Navbar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchHealth = async () => {
    try {
      setIsRefreshing(true);
      const res = await api.getHealth();
      setHealth(res);
    } catch {
      setHealth(null);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const timer = setInterval(fetchHealth, 15000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b border-border bg-card/80 px-6 backdrop-blur">
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-primary/10 text-primary">
          <Server className="h-4 w-4" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-semibold text-foreground">LLM Gateway</span>
          <span className="text-xs text-muted-foreground font-mono">Gemini Proxy</span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${
              health ? "bg-emerald-500" : "bg-rose-500"
            }`}
          />
          <span className="text-muted-foreground">
            {health ? "Operational" : "Offline"}
          </span>
        </div>

        <button
          onClick={fetchHealth}
          disabled={isRefreshing}
          title="Refresh gateway status"
          className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
        </button>
      </div>
    </header>
  );
}
