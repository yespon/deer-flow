import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { fetch } from "@/core/api/fetcher";

import { type SystemStats, type FeedbackStats } from "./api";

// ── Dashboard ────────────────────────────────────────────────────

export interface DashboardData {
  stats: SystemStats;
  feedback_stats: FeedbackStats;
  channels: {
    service_running: boolean;
    channels: Record<string, unknown>;
  };
  memory_config: {
    enabled: boolean;
    max_facts: number;
    injection_enabled: boolean;
  };
  skills_count: number;
  mcp_servers: Record<string, { enabled: boolean; type: string }>;
}

export function useAdminDashboard() {
  return useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/dashboard");
      if (!res.ok) throw new Error("Failed to fetch dashboard data");
      return res.json() as Promise<DashboardData>;
    },
    refetchInterval: 30_000,
  });
}

// ── Config ────────────────────────────────────────────────────────

export interface ConfigSectionInfo {
  key: string;
  tier: number;
  description: string;
}

export interface ConfigData {
  sections: ConfigSectionInfo[];
  config: Record<string, unknown>;
}

export function useAdminConfig() {
  return useQuery({
    queryKey: ["admin", "config"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/config");
      if (!res.ok) throw new Error("Failed to fetch config");
      return res.json() as Promise<ConfigData>;
    },
  });
}

// ── Config Section Write ──────────────────────────────────────────

export function useUpdateConfigSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      section,
      data,
    }: {
      section: string;
      data: unknown;
    }) => {
      const res = await fetch(`/api/v1/admin/config/${section}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ section, data }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Update failed");
      }
      return res.json() as Promise<{
        success: boolean;
        tier: number;
        message: string;
        requires_restart: boolean;
      }>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "config"] });
      void qc.invalidateQueries({ queryKey: ["admin", "restart", "pending"] });
    },
  });
}

export function useValidateConfigSection() {
  return useMutation({
    mutationFn: async ({
      section,
      data,
    }: {
      section: string;
      data: unknown;
    }) => {
      const res = await fetch("/api/v1/admin/config/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ section, data }),
      });
      return res.json() as Promise<{ valid: boolean; errors: string[] }>;
    },
  });
}

// ── Secrets ───────────────────────────────────────────────────────

export interface SecretEntry {
  key: string;
  source: string;
  masked_value: string;
  is_env_ref: boolean;
}

export function useAdminSecrets() {
  return useQuery({
    queryKey: ["admin", "secrets"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/secrets");
      if (!res.ok) throw new Error("Failed to fetch secrets");
      return res.json() as Promise<{ secrets: SecretEntry[] }>;
    },
  });
}

export function useUpdateSecret() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      const res = await fetch("/api/v1/admin/secrets", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Update failed");
      }
      return res.json() as Promise<{ success: boolean; message: string }>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "secrets"] });
    },
  });
}

// ── Restart ───────────────────────────────────────────────────────

export interface PendingRestartStatus {
  pending_restart: boolean;
  sections: string[];
  since: string | null;
}

export function usePendingRestart() {
  return useQuery({
    queryKey: ["admin", "restart", "pending"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/restart/pending");
      if (!res.ok) throw new Error("Failed to check pending restart");
      return res.json() as Promise<PendingRestartStatus>;
    },
    refetchInterval: 15_000,
  });
}

export function useRestartServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reason = "Admin triggered from dashboard") => {
      const res = await fetch("/api/v1/admin/restart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!res.ok) throw new Error("Restart failed");
      return res.json() as Promise<{ success: boolean; message: string }>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "restart", "pending"] });
    },
  });
}

// ── Tier helpers ──────────────────────────────────────────────────

export const TIER_COLORS: Record<number, string> = {
  1: "bg-green-100 text-green-800",
  2: "bg-amber-100 text-amber-800",
  3: "bg-red-100 text-red-800",
};

export const TIER_LABELS: Record<number, string> = {
  1: "Hot reload",
  2: "Needs restart",
  3: "Security sensitive",
};
