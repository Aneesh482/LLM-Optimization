import React, { useState } from "react";
import {
  Send,
  Trash2,
  Copy,
  Check,
  Zap,
  Sliders,
  Sparkles,
  Bot,
  User,
  Clock,
  Layers,
} from "lucide-react";
import { api } from "../lib/api";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import type { ChatMessage, ChatCompletionResponse } from "../types";

const QUICK_PROMPTS = [
  {
    label: "Quick Concept",
    prompt: "Explain how recursion works in computer science with a simple 3-line example.",
  },
  {
    label: "Large JSON Context",
    prompt: `Analyze the performance bottlenecks from this server log:\n${JSON.stringify(
      Array.from({ length: 15 }).map((_, i) => ({
        id: i + 1,
        endpoint: "/api/checkout",
        status: i === 7 ? 504 : 200,
        latency_ms: i === 7 ? 8400 : 120,
      })),
      null,
      2
    )}`,
  },
  {
    label: "Code Refactor",
    prompt: "Refactor this Python function to be more efficient:\n\ndef find_duplicates(items):\n    dups = []\n    for i in range(len(items)):\n        for j in range(i+1, len(items)):\n            if items[i] == items[j] and items[i] not in dups:\n                dups.append(items[i])\n    return dups",
  },
];

interface MessageItem extends ChatMessage {
  id: string;
  timestamp: Date;
  metadata?: {
    latency_ms: number;
    usage: {
      input_tokens?: number | null;
      output_tokens?: number | null;
      total_tokens?: number | null;
      cached_tokens?: number | null;
    };
    model: string;
    optimization?: {
      original_tokens?: number;
      optimized_tokens?: number;
      tokens_saved?: number;
      compression_ratio?: number;
      summary_injected?: boolean;
      strategy?: string;
      archived_context_id?: string | null;
    } | null;
  };
}

export function Playground() {
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: "init",
      role: "assistant",
      content: "Hello! I am connected to the LLM Gateway. Type a prompt below to send requests through our optimization proxy.",
      timestamp: new Date(),
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("You are an expert AI assistant.");
  const [selectedModel, setSelectedModel] = useState("gemini-3.6-flash");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1000);
  const [optimizeContext, setOptimizeContext] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleSend = async () => {
    if (!inputText.trim() || isLoading) return;

    setErrorMsg(null);
    const userMessage: MessageItem = {
      id: String(Date.now()),
      role: "user",
      content: inputText.trim(),
      timestamp: new Date(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputText("");
    setIsLoading(true);

    try {
      // Build request messages (including system prompt if provided)
      const apiMessages: ChatMessage[] = [];
      if (systemPrompt.trim()) {
        apiMessages.push({ role: "system", content: systemPrompt.trim() });
      }
      for (const m of updatedMessages) {
        if (m.role === "user" || m.role === "assistant") {
          apiMessages.push({ role: m.role, content: m.content });
        }
      }

      const res: ChatCompletionResponse = await api.sendChatCompletion({
        model: selectedModel,
        messages: apiMessages,
        temperature,
        max_output_tokens: maxTokens,
        optimize_context: optimizeContext,
      });

      const assistantMessage: MessageItem = {
        id: res.id || String(Date.now() + 1),
        role: "assistant",
        content: res.content,
        timestamp: new Date(),
        metadata: {
          latency_ms: res.latency_ms,
          usage: res.usage,
          model: res.model,
          optimization: res.optimization,
        },
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to get completion from gateway.";
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClear = () => {
    setMessages([]);
    setErrorMsg(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Chat Playground
          </h1>
          <p className="text-xs text-muted-foreground">
            Test LLM prompts directly through the optimization gateway with real-time token tracking.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleClear} className="h-8 gap-1.5 text-xs">
          <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
          <span>Clear Chat</span>
        </Button>
      </div>

      {/* Main Grid: Chat Area + Control Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat Area (2 cols) */}
        <div className="lg:col-span-2 flex flex-col space-y-4">
          {/* Presets & Prominent Optimize Context Button Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-2 p-2 rounded bg-card border border-border">
            <div className="flex items-center gap-1.5 overflow-x-auto">
              <span className="text-xs text-muted-foreground font-medium shrink-0 mr-1">Presets:</span>
              {QUICK_PROMPTS.map((qp, idx) => (
                <button
                  key={idx}
                  onClick={() => setInputText(qp.prompt)}
                  className="text-xs px-2.5 py-1 rounded bg-muted/40 border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0 font-medium"
                >
                  {qp.label}
                </button>
              ))}
            </div>

            {/* Prominent Optimize Context Toggle Button */}
            <button
              onClick={() => setOptimizeContext(!optimizeContext)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold border transition-all ${
                optimizeContext
                  ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25"
                  : "bg-muted text-muted-foreground border-border hover:text-foreground"
              }`}
            >
              <Zap className={`h-3.5 w-3.5 ${optimizeContext ? "text-emerald-400 fill-emerald-400/30" : ""}`} />
              <span>Optimize Context: {optimizeContext ? "ON" : "OFF"}</span>
            </button>
          </div>

          {/* Messages Container */}
          <Card className="flex-1 min-h-[460px] max-h-[580px] flex flex-col">
            <CardContent className="p-4 flex-1 overflow-y-auto space-y-4">
              {messages.length === 0 ? (
                <div className="flex h-full min-h-[300px] flex-col items-center justify-center text-center text-xs text-muted-foreground">
                  <Bot className="h-8 w-8 text-muted-foreground/50 mb-2" />
                  <p className="font-medium text-foreground">No messages yet</p>
                  <p className="mt-1 max-w-sm text-muted-foreground">
                    Type a prompt below or click a preset above to test the gateway.
                  </p>
                </div>
              ) : (
                messages.map((m) => {
                  const isUser = m.role === "user";
                  return (
                    <div
                      key={m.id}
                      className={`flex gap-3 text-xs ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      {!isUser && (
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-primary/10 text-primary mt-0.5">
                          <Bot className="h-4 w-4" />
                        </div>
                      )}

                      <div
                        className={`flex flex-col space-y-1.5 max-w-[85%] rounded-lg p-3.5 ${
                          isUser
                            ? "bg-primary text-primary-foreground font-sans"
                            : "bg-muted/30 border border-border text-foreground font-sans"
                        }`}
                      >
                        <div className="whitespace-pre-wrap leading-relaxed font-sans">
                          {m.content}
                        </div>

                        {/* Assistant Metadata Footer */}
                        {!isUser && m.metadata && (
                          <div className="mt-2 pt-2 border-t border-border/60 flex flex-col gap-1.5 text-[11px] font-mono text-muted-foreground">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-3">
                                <span title="Prompt tokens sent to Gemini">
                                  Prompt (In): <strong className="text-foreground">{m.metadata.usage.input_tokens || 0}</strong>
                                </span>
                                <span title="Response tokens generated by Gemini">
                                  Generated (Out): <strong className="text-foreground">{m.metadata.usage.output_tokens || 0}</strong>
                                </span>
                                <span>
                                  Total: <strong className="text-primary">{m.metadata.usage.total_tokens || 0}</strong>
                                </span>
                                <span className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {m.metadata.latency_ms.toFixed(0)} ms
                                </span>
                              </div>

                              <button
                                onClick={() => handleCopy(m.id, m.content)}
                                className="text-muted-foreground hover:text-foreground p-0.5 rounded"
                                title="Copy response"
                              >
                                {copiedId === m.id ? (
                                  <Check className="h-3 w-3 text-emerald-400" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </button>
                            </div>

                            {m.metadata.optimization && (m.metadata.optimization.tokens_saved || 0) > 0 && (
                              <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 w-fit">
                                <Zap className="h-3 w-3 shrink-0" />
                                <span>
                                  Optimization saved <strong>{m.metadata.optimization.tokens_saved} prompt tokens</strong> ({m.metadata.optimization.original_tokens} → {m.metadata.optimization.optimized_tokens})
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {isUser && (
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-secondary text-foreground mt-0.5">
                          <User className="h-4 w-4" />
                        </div>
                      )}
                    </div>
                  );
                })
              )}

              {isLoading && (
                <div className="flex gap-3 text-xs justify-start items-center text-muted-foreground">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-primary/10 text-primary">
                    <Bot className="h-4 w-4 animate-pulse" />
                  </div>
                  <div className="p-3 bg-muted/20 rounded border border-border flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-primary animate-ping" />
                    <span>Routing & optimizing prompt via Gemini...</span>
                  </div>
                </div>
              )}
            </CardContent>

            {/* Input Box */}
            <div className="p-3 border-t border-border bg-card">
              {errorMsg && (
                <div className="text-xs text-rose-400 bg-rose-950/20 border border-rose-800/30 p-2.5 rounded mb-2 font-mono">
                  {errorMsg}
                </div>
              )}

              <div className="flex gap-2">
                <textarea
                  rows={2}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Type a message or paste context... (Ctrl + Enter to send)"
                  className="flex-1 font-sans text-xs rounded border border-border bg-background p-2.5 text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
                <Button
                  onClick={handleSend}
                  disabled={!inputText.trim() || isLoading}
                  isLoading={isLoading}
                  className="px-4 gap-1.5"
                >
                  <Send className="h-3.5 w-3.5" />
                  <span>Send</span>
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Configuration Controls (1 col) */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Sliders className="h-4 w-4 text-muted-foreground" />
                <span>Gateway Parameters</span>
              </CardTitle>
              <CardDescription>Configure optimization & Gemini model</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              {/* Model selection */}
              <div>
                <label className="block font-medium text-foreground mb-1">Model</label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full rounded border border-border bg-background p-2 font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="gemini-3.6-flash">gemini-3.6-flash (Fast)</option>
                  <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                  <option value="gemini-2.5-pro">gemini-2.5-pro (Reasoning)</option>
                </select>
              </div>

              {/* Optimization Toggle Box */}
              <div
                onClick={() => setOptimizeContext(!optimizeContext)}
                className={`p-3 rounded border transition-colors cursor-pointer space-y-1.5 ${
                  optimizeContext
                    ? "bg-emerald-500/10 border-emerald-500/30"
                    : "bg-muted/20 border-border hover:bg-muted/30"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <Zap className={`h-3.5 w-3.5 ${optimizeContext ? "text-emerald-400" : "text-muted-foreground"}`} />
                    <span>Optimize Context</span>
                  </span>
                  <Badge variant={optimizeContext ? "success" : "outline"}>
                    {optimizeContext ? "ENABLED" : "DISABLED"}
                  </Badge>
                </div>
                <p className="text-muted-foreground text-[11px] leading-relaxed">
                  Automatically compresses large JSON/Code/Logs in your prompt and archives older conversation context to SQLite.
                </p>
              </div>

              {/* System Prompt */}
              <div>
                <label className="block font-medium text-foreground mb-1">System Instructions</label>
                <textarea
                  rows={3}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="System instructions..."
                  className="w-full font-mono text-xs rounded border border-border bg-background p-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </div>

              {/* Temperature */}
              <div>
                <div className="flex justify-between font-medium text-foreground mb-1">
                  <span>Temperature</span>
                  <span className="font-mono text-muted-foreground">{temperature}</span>
                </div>
                <input
                  type="range"
                  min={0.0}
                  max={1.0}
                  step={0.1}
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>

              {/* Max Output Tokens */}
              <div>
                <div className="flex justify-between font-medium text-foreground mb-1">
                  <span>Max Tokens</span>
                  <span className="font-mono text-muted-foreground">{maxTokens}</span>
                </div>
                <input
                  type="range"
                  min={200}
                  max={4000}
                  step={100}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(Number(e.target.value))}
                  className="w-full accent-primary"
                />
              </div>
            </CardContent>
          </Card>

          {/* Quick Info Card */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                How It Works
              </CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground space-y-2">
              <p>
                1. Your prompt is analyzed for bulky content structures (JSON tables, repetitive logs, code AST).
              </p>
              <p>
                2. Large content is compressed or archived in SQLite.
              </p>
              <p>
                3. The optimized request is sent to Gemini, and all telemetry is recorded in your dashboard.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
