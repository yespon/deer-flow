"use client";

import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { usePendingRestart, useRestartServer } from "@/core/admin/hooks";

/**
 * Global banner that appears when config changes require a server restart.
 * Polls the /restart/pending endpoint every 15s and shows a dismissible
 * amber banner with a one-click restart button.
 */
export function RestartBanner() {
  const { data } = usePendingRestart();
  const restartMut = useRestartServer();

  if (!data?.pending_restart) return null;

  const sections = data.sections.join(", ");
  const since = data.since ? new Date(data.since).toLocaleTimeString() : "";

  return (
    <div className="flex items-center gap-3 border-b border-amber-200 bg-amber-50 px-4 py-2 text-sm">
      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
      <span className="text-amber-800">
        Config changes ({sections}) require a server restart to take effect.
        {since && <span className="text-amber-600"> Since {since}</span>}
      </span>
      <Button
        size="sm"
        variant="outline"
        className="ml-auto shrink-0 gap-1 border-amber-300 text-amber-800 hover:bg-amber-100"
        disabled={restartMut.isPending}
        onClick={() => restartMut.mutate("Restart from banner")}
      >
        <RefreshCw
          className={`h-3.5 w-3.5 ${restartMut.isPending ? "animate-spin" : ""}`}
        />
        {restartMut.isPending ? "Restarting..." : "Restart Now"}
      </Button>
    </div>
  );
}

/**
 * A standalone button for the admin sidebar to trigger a graceful restart.
 * Shows a pulsing dot indicator when a pending restart is detected.
 */
export function RestartButton() {
  const { data: pending } = usePendingRestart();
  const restartMut = useRestartServer();
  const hasPending = pending?.pending_restart;

  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        className="gap-1"
        disabled={restartMut.isPending}
        onClick={() => restartMut.mutate("Admin triggered from dashboard")}
      >
        <RefreshCw
          className={`h-3.5 w-3.5 ${restartMut.isPending ? "animate-spin" : ""}`}
        />
        {restartMut.isPending ? "Restarting..." : "Restart Server"}
      </Button>
      {hasPending && (
        <span className="absolute -top-1 -right-1 h-2.5 w-2.5 animate-pulse rounded-full bg-amber-500" />
      )}
    </div>
  );
}
