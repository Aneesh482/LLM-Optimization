import React, { useState } from "react";
import { Play, Calculator } from "lucide-react";
import { api } from "../lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { formatNumber, formatCurrency, formatPercentage } from "../lib/utils";
import type { TokenAnalysisResult } from "../types";

export function TokenAnalytics() {
  const [inputText, setInputText] = useState(
    JSON.stringify(
      [
        { role: "system", content: "You are a helpful software engineering assistant." },
        { role: "user", content: "Analyze the architectural trade-offs between monolithic and microservice architectures." },
        { role: "assistant", content: "Here is a comparison of monoliths vs microservices covering deployment, latency, and scaling..." },
      ],
      null,
      2
    )
  );
  const [analysis, setAnalysis] = useState<TokenAnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);

  // Cost calculator state
  const [monthlyTokens, setMonthlyTokens] = useState<number>(50000000);
  const [compressionRatio, setCompressionRatio] = useState<number>(0.35); // 35% tokens saved

  const handleAnalyze = async () => {
    setParseError(null);
    let messages: Array<{ role: string; content: string }> = [];

    try {
      const parsed = JSON.parse(inputText);
      if (Array.isArray(parsed)) {
        messages = parsed;
      } else {
        messages = [{ role: "user", content: inputText }];
      }
    } catch {
      messages = [{ role: "user", content: inputText }];
    }

    try {
      setIsAnalyzing(true);
      const res = await api.analyzeTokens(messages);
      setAnalysis(res);
    } catch (err: any) {
      setParseError(err.response?.data?.detail || "Failed to analyze tokens.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Gemini Flash estimated price ($0.075 / 1M tokens)
  const costPerMillion = 0.075;
  const unoptimizedCost = (monthlyTokens / 1000000) * costPerMillion;
  const tokensSavedMonthly = monthlyTokens * compressionRatio;
  const optimizedTokens = monthlyTokens - tokensSavedMonthly;
  const optimizedCost = (optimizedTokens / 1000000) * costPerMillion;
  const monthlySavings = unoptimizedCost - optimizedCost;

  const [optResult, setOptResult] = useState<import("../types").OptimizeContextResponse | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const handleOptimize = async () => {
    setParseError(null);
    let messages: Array<{ role: string; content: string }> = [];

    try {
      const parsed = JSON.parse(inputText);
      if (Array.isArray(parsed)) {
        messages = parsed;
      } else {
        messages = [{ role: "user", content: inputText }];
      }
    } catch {
      messages = [{ role: "user", content: inputText }];
    }

    try {
      setIsOptimizing(true);
      const res = await api.optimizeContext({
        messages: messages as any,
        max_context_tokens: 300,
        recent_messages_count: 2,
        archive_to_ccr: true,
      });
      setOptResult(res);
    } catch (err: any) {
      setParseError(err.response?.data?.detail || "Failed to optimize context.");
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          Token Analytics & Context Optimizer
        </h1>
        <p className="text-xs text-muted-foreground">
          Inspect token distributions, bloated context sections, or run the rolling-window context optimizer.
        </p>
      </div>

      {/* Context Analyzer */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">Context Token Analyzer & Window Optimizer</CardTitle>
          <CardDescription>
            Paste a JSON conversation array or prompt text to inspect tokens or test rolling-window context optimization.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            rows={6}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder='[{"role": "user", "content": "..."}]'
            className="w-full font-mono text-xs rounded border border-border bg-background p-3 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />

          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">
              Accepts JSON array of {`{"role", "content"}`} or raw text.
            </span>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={handleAnalyze} isLoading={isAnalyzing} className="gap-1.5">
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>Analyze Tokens</span>
              </Button>
              <Button size="sm" onClick={handleOptimize} isLoading={isOptimizing} className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white">
                <span>⚡ Optimize Context Window</span>
              </Button>
            </div>
          </div>

          {parseError && (
            <div className="text-xs text-rose-400 bg-rose-950/20 border border-rose-800/30 p-2.5 rounded">
              {parseError}
            </div>
          )}

          {/* Standalone Optimization Result Card */}
          {optResult && (
            <div className="p-4 bg-emerald-950/20 border border-emerald-500/30 rounded-lg space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-emerald-400 flex items-center gap-1.5">
                  <span>⚡ Context Window Optimized</span>
                </span>
                <Badge variant="success">CCR Archived</Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                <div className="p-2 bg-card rounded border border-border">
                  <span className="text-muted-foreground text-[10px]">Original Tokens</span>
                  <p className="font-bold text-foreground mt-0.5">{optResult.metrics.original_tokens}</p>
                </div>
                <div className="p-2 bg-card rounded border border-border">
                  <span className="text-muted-foreground text-[10px]">Optimized Tokens</span>
                  <p className="font-bold text-foreground mt-0.5">{optResult.metrics.optimized_tokens}</p>
                </div>
                <div className="p-2 bg-card rounded border border-border">
                  <span className="text-muted-foreground text-[10px]">Tokens Saved</span>
                  <p className="font-bold text-emerald-400 mt-0.5">{optResult.metrics.tokens_saved}</p>
                </div>
                <div className="p-2 bg-card rounded border border-border">
                  <span className="text-muted-foreground text-[10px]">Messages</span>
                  <p className="font-bold text-foreground mt-0.5">
                    {optResult.metrics.original_message_count} &rarr; {optResult.metrics.optimized_message_count}
                  </p>
                </div>
              </div>

              {optResult.metrics.archived_context_id && (
                <p className="text-[11px] text-muted-foreground">
                  Archived to CCR: <span className="text-primary font-bold">[CCR:{optResult.metrics.archived_context_id}]</span>
                </p>
              )}
            </div>
          )}

          {analysis && (
            <div className="mt-4 space-y-4 pt-4 border-t border-border">
              {/* Stat Counters */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="p-3 bg-card rounded border border-border">
                  <span className="text-xs text-muted-foreground font-mono">Estimated Tokens</span>
                  <p className="text-xl font-bold font-mono text-primary mt-1">
                    {formatNumber(analysis.total_estimated_tokens)}
                  </p>
                </div>
                <div className="p-3 bg-card rounded border border-border">
                  <span className="text-xs text-muted-foreground font-mono">Characters</span>
                  <p className="text-xl font-bold font-mono text-foreground mt-1">
                    {formatNumber(analysis.total_characters)}
                  </p>
                </div>
                <div className="p-3 bg-card rounded border border-border">
                  <span className="text-xs text-muted-foreground font-mono">Words</span>
                  <p className="text-xl font-bold font-mono text-foreground mt-1">
                    {formatNumber(analysis.total_words)}
                  </p>
                </div>
                <div className="p-3 bg-card rounded border border-border">
                  <span className="text-xs text-muted-foreground font-mono">Messages</span>
                  <p className="text-xl font-bold font-mono text-foreground mt-1">
                    {analysis.message_count}
                  </p>
                </div>
              </div>

              {/* Largest Sections List */}
              {analysis.largest_sections && analysis.largest_sections.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-foreground">
                    Largest Sections in Context
                  </h4>
                  <div className="space-y-2">
                    {analysis.largest_sections.map((sec) => (
                      <div
                        key={sec.index}
                        className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded bg-card border border-border text-xs font-mono gap-2"
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          <Badge variant="outline" className="uppercase text-[10px]">
                            {sec.role}
                          </Badge>
                          <span className="text-muted-foreground truncate font-sans">
                            {sec.content_preview}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-muted-foreground shrink-0">
                          <span>{sec.estimated_tokens} tokens</span>
                          <span className="text-foreground font-semibold">
                            {formatPercentage(sec.percentage_of_total / 100)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cost Estimator */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Calculator className="h-4 w-4 text-muted-foreground" />
            <span>Cost & Savings Calculator</span>
          </CardTitle>
          <CardDescription>
            Estimate monthly cost reductions based on your projected token volume.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-medium text-foreground mb-1.5">
                  <span>Monthly Tokens:</span>
                  <span className="font-mono text-primary">{formatNumber(monthlyTokens)}</span>
                </div>
                <input
                  type="range"
                  min={1000000}
                  max={200000000}
                  step={1000000}
                  value={monthlyTokens}
                  onChange={(e) => setMonthlyTokens(Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-foreground mb-1.5">
                  <span>Optimization Ratio:</span>
                  <span className="font-mono text-emerald-400">{formatPercentage(compressionRatio)} saved</span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={0.8}
                  step={0.05}
                  value={compressionRatio}
                  onChange={(e) => setCompressionRatio(Number(e.target.value))}
                  className="w-full accent-emerald-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="p-4 bg-muted/20 rounded border border-border flex flex-col justify-center">
                <span className="text-xs text-muted-foreground">Unoptimized Cost</span>
                <p className="text-xl font-bold font-mono text-foreground mt-1">
                  {formatCurrency(unoptimizedCost)} / mo
                </p>
                <span className="text-[11px] text-muted-foreground mt-1">Direct API</span>
              </div>

              <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded flex flex-col justify-center">
                <span className="text-xs text-emerald-400 font-medium">Gateway Cost</span>
                <p className="text-xl font-bold font-mono text-emerald-400 mt-1">
                  {formatCurrency(optimizedCost)} / mo
                </p>
                <span className="text-[11px] text-emerald-400 mt-1">
                  Save {formatCurrency(monthlySavings)} / mo
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
