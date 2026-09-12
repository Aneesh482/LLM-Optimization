import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Bot,
  ListOrdered,
  Activity,
  FileCode,
  HardDrive,
  Layers,
  Settings,
} from "lucide-react";
import { cn } from "../../lib/utils";

const navigation = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Playground", href: "/playground", icon: Bot },
  { name: "Requests", href: "/requests", icon: ListOrdered },
  { name: "Token Analytics", href: "/tokens", icon: Activity },
  { name: "Compression", href: "/compression", icon: FileCode },
  { name: "Context Storage", href: "/contexts", icon: HardDrive },
  { name: "Providers & Cache", href: "/providers", icon: Layers },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="w-56 border-r border-border bg-card flex flex-col justify-between p-3 min-h-[calc(100vh-3.5rem)]">
      <div className="space-y-1">
        <div className="px-3 py-1.5 text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
          Menu
        </div>
        <nav className="space-y-0.5">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-colors",
                    isActive
                      ? "bg-secondary text-foreground font-semibold"
                      : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="rounded-md border border-border bg-background p-3 text-xs text-muted-foreground space-y-1 font-mono">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Engine</span>
          <span className="text-foreground">FastAPI</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">DB</span>
          <span className="text-foreground">SQLite</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">LLM</span>
          <span className="text-foreground">Gemini</span>
        </div>
      </div>
    </aside>
  );
}
