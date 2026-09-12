import React from "react";
import { Card, CardContent } from "./Card";
import { cn } from "../../lib/utils";

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  className,
}: StatCardProps) {
  return (
    <Card className={cn("border-border bg-card", className)}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-muted-foreground">{title}</p>
          {icon && <div className="text-muted-foreground">{icon}</div>}
        </div>

        <div className="mt-2 flex items-baseline justify-between">
          <div className="text-xl font-bold font-mono tracking-tight text-foreground">
            {value}
          </div>
          {trend && (
            <span
              className={cn(
                "text-xs font-mono font-medium",
                trend.isPositive ? "text-emerald-400" : "text-rose-400"
              )}
            >
              {trend.value}
            </span>
          )}
        </div>

        {subtitle && (
          <p className="mt-1 text-xs text-muted-foreground truncate">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
