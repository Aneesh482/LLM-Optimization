import React, { useEffect, useState } from "react";
import {
  Activity,
  DollarSign,
  TrendingDown,
  Clock,
  ArrowRight,
  Database,
  Cpu,
  Layers,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { api } from "../lib/api";
import { StatCard } from "../components/ui/StatCard";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { formatNumber, formatCurrency, formatPercentage, formatRelativeTime } from "../lib/utils";
import type { DashboardMetricsResponse, RequestLogItem, CacheHierarchyStatus } from "../types";
import { Link } from "react-router-dom";

const PIE_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"];

export function Overview() {
  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null);
  const [cacheStatus, setCacheStatus] = useState<CacheHierarchyStatus | null>(null);
  const [recentLogs, setRecentLogs] = useState<RequestLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [m, c, r] = await Promise.all([
        api.getMetrics(),
        api.getCacheStatus(),
        api.getRequests({ limit: 6 }),
      ]);
      setMetrics(m);
      setCacheStatus(c);
      setRecentLogs(r.items);
    } catch (err) {
      console.error("Failed to load overview data", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const totalTokensSaved = metrics?.total_tokens_saved || 0;
  const totalTokensUsed = metrics?.total_tokens || 0;
  const grossTokens = totalTokensUsed + totalTokensSaved;
  const savingsPct = grossTokens > 0 ? totalTokensSaved / grossTokens : 0;

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Overview
          </h1>
          <p className="text-xs text-muted-foreground">
            Gateway telemetry, token optimization performance, and caching metrics.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadData} isLoading={isLoading}>
            Refresh
          </Button>
          <Link to="/playground">
            <Button size="sm" className="gap-1.5">
              <span>Open Playground</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Requests"
          value={formatNumber(metrics?.total_requests || 0)}
          subtitle={`${metrics?.successful_requests || 0} succeeded, ${metrics?.failed_requests || 0} failed`}
          icon={<Activity className="h-4 w-4" />}
        />
        <StatCard
          title="Tokens Saved"
          value={formatNumber(totalTokensSaved)}
          subtitle={`${formatPercentage(savingsPct)} total reduction`}
          trend={{ value: formatPercentage(savingsPct), isPositive: true }}
          icon={<TrendingDown className="h-4 w-4 text-emerald-400" />}
        />
        <StatCard
          title="Average Latency"
          value={`${metrics?.avg_latency_ms || 0} ms`}
          subtitle="Gateway end-to-end"
          icon={<Clock className="h-4 w-4" />}
        />
        <StatCard
          title="Estimated Cost Saved"
          value={formatCurrency(metrics?.estimated_cost_saved_usd || 0)}
          subtitle={`Current usage: ${formatCurrency(metrics?.estimated_cost_usd || 0)}`}
          icon={<DollarSign className="h-4 w-4 text-emerald-400" />}
        />
      </div>

      {/* Cache Status Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Tier 1: Gateway RAM</span>
              <Badge variant="outline">In-Memory</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-1 text-xs">
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-lg font-mono font-bold text-foreground">
                {cacheStatus?.tier_1_in_memory_gateway_cache.cached_entries || 0} / {cacheStatus?.tier_1_in_memory_gateway_cache.max_capacity || 200}
              </span>
              <span className="font-mono text-emerald-400">
                {formatPercentage(cacheStatus?.tier_1_in_memory_gateway_cache.hit_ratio || 0)} Hit Rate
              </span>
            </div>
            <p className="mt-1 text-muted-foreground">
              {cacheStatus?.tier_1_in_memory_gateway_cache.cache_hits || 0} hits, {cacheStatus?.tier_1_in_memory_gateway_cache.cache_misses || 0} misses
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Tier 2: CCR Storage</span>
              <Badge variant="outline">SQLite</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-1 text-xs">
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-lg font-mono font-bold text-foreground">
                {cacheStatus?.tier_2_ccr_sqlite_storage.stored_contexts || 0} Contexts
              </span>
              <span className="font-mono text-muted-foreground">On-Demand</span>
            </div>
            <p className="mt-1 text-muted-foreground">
              Verbatim payloads stored for reference retrieval
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Tier 3: Gemini Cache</span>
              <Badge variant="success">Google GenAI</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-1 text-xs">
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-lg font-mono font-bold text-foreground">
                {cacheStatus?.tier_3_provider_context_caching.active_provider_caches || 0} Active
              </span>
              <span className="font-mono text-emerald-400">Available</span>
            </div>
            <p className="mt-1 text-muted-foreground">
              Provider-side prompt caches for large contexts
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Area Chart: Token Usage */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Token Usage Trends</CardTitle>
            <CardDescription>Input and output token volume across recent requests</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full">
              {metrics?.time_series && metrics.time_series.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={metrics.time_series} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorInput" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="colorOutput" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="timestamp" stroke="#71717a" fontSize={11} tickLine={false} />
                    <YAxis stroke="#71717a" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        borderColor: "#27272a",
                        borderRadius: "4px",
                        fontSize: "12px",
                      }}
                    />
                    <Area type="monotone" dataKey="input_tokens" name="Input Tokens" stroke="#3b82f6" fillOpacity={1} fill="url(#colorInput)" />
                    <Area type="monotone" dataKey="output_tokens" name="Output Tokens" stroke="#10b981" fillOpacity={1} fill="url(#colorOutput)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                  No requests recorded yet. Data will appear after sending requests.
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Content Type Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold">Contexts by Content Type</CardTitle>
            <CardDescription>Distribution of stored CCR payloads</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 w-full flex flex-col justify-center">
              {metrics?.content_types_breakdown && metrics.content_types_breakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={metrics.content_types_breakdown}
                      dataKey="count"
                      nameKey="content_type"
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      paddingAngle={4}
                    >
                      {metrics.content_types_breakdown.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#18181b",
                        borderColor: "#27272a",
                        borderRadius: "4px",
                        fontSize: "12px",
                      }}
                    />
                    <Legend verticalAlign="bottom" height={36} iconSize={8} wrapperStyle={{ fontSize: "11px" }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-muted-foreground text-center px-4">
                  No context entries stored yet. Use the Compression or Context Storage tab to create records.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Requests Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-sm font-semibold">Recent Requests</CardTitle>
            <CardDescription>Latest API completions dispatched via the gateway</CardDescription>
          </div>
          <Link to="/requests">
            <Button variant="ghost" size="sm" className="gap-1 text-xs text-primary">
              <span>View all</span>
              <ArrowRight className="h-3 w-3" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border text-muted-foreground font-mono">
                  <th className="pb-2.5 font-medium">Request ID</th>
                  <th className="pb-2.5 font-medium">Time</th>
                  <th className="pb-2.5 font-medium">Model</th>
                  <th className="pb-2.5 font-medium">In / Out Tokens</th>
                  <th className="pb-2.5 font-medium">Latency</th>
                  <th className="pb-2.5 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-mono">
                {recentLogs.length > 0 ? (
                  recentLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2.5 text-foreground font-medium">
                        {log.request_id.slice(0, 8)}...
                      </td>
                      <td className="py-2.5 text-muted-foreground">
                        {formatRelativeTime(log.timestamp)}
                      </td>
                      <td className="py-2.5 text-foreground">{log.model}</td>
                      <td className="py-2.5 text-muted-foreground">
                        {log.input_tokens || 0} / {log.output_tokens || 0}
                      </td>
                      <td className="py-2.5 text-muted-foreground">
                        {log.latency_ms ? `${log.latency_ms} ms` : "-"}
                      </td>
                      <td className="py-2.5 text-right">
                        <Badge
                          variant={log.status === "success" ? "success" : "destructive"}
                        >
                          {log.status}
                        </Badge>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-muted-foreground font-sans">
                      No requests logged yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
