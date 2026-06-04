"use client";

import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { fetch } from "@/core/api/fetcher";

interface AuditEntry {
  id: string;
  user_id: string;
  user_email: string;
  action: string;
  target_type: string;
  target_id: string;
  detail: string | null;
  ip_address: string | null;
  timestamp: string;
}

function useAuditLogs(page: number, action?: string, userId?: string) {
  return useQuery({
    queryKey: ["admin", "audit", page, action, userId],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "20",
      });
      if (action) params.set("action", action);
      if (userId) params.set("user_id", userId);
      const res = await fetch(`/api/v1/admin/audit?${params}`);
      if (!res.ok) throw new Error("Failed to fetch audit logs");
      return res.json() as Promise<{
        items: AuditEntry[];
        total: number;
        page: number;
        page_size: number;
      }>;
    },
  });
}

const ACTION_COLORS: Record<string, string> = {
  config_update: "bg-amber-100 text-amber-800",
  secret_update: "bg-red-100 text-red-800",
  user_create: "bg-green-100 text-green-800",
  user_update: "bg-blue-100 text-blue-800",
  user_delete: "bg-red-100 text-red-800",
  password_reset: "bg-purple-100 text-purple-800",
  restart: "bg-purple-100 text-purple-800",
  enterprise_config_update: "bg-indigo-100 text-indigo-800",
};

async function exportAuditLogs() {
  // Fetch all logs (up to 1000) and download as JSON
  const params = new URLSearchParams({ page: "1", page_size: "1000" });
  const res = await fetch(`/api/v1/admin/audit?${params}`);
  if (!res.ok) return;
  const data = await res.json();
  const blob = new Blob([JSON.stringify(data.items, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function AdminAuditPage() {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const { data, isLoading } = useAuditLogs(
    page,
    actionFilter || undefined,
    userFilter || undefined,
  );

  const entries = data?.items ?? [];
  const totalPages = Math.ceil((data?.total ?? 0) / 20);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Audit Log</h1>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Filter by action..."
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 w-40 text-sm"
          />
          <Input
            placeholder="Filter by user..."
            value={userFilter}
            onChange={(e) => {
              setUserFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 w-40 text-sm"
          />
          <Badge variant="outline">{data?.total ?? 0} entries</Badge>
          <Button
            variant="outline"
            size="sm"
            className="gap-1"
            onClick={exportAuditLogs}
          >
            <Download className="h-3.5 w-3.5" /> Export
          </Button>
        </div>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Time
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  User
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Action
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Target
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Detail
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  IP
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    Loading...
                  </td>
                </tr>
              )}
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  className="border-b border-gray-50 hover:bg-gray-50/50"
                >
                  <td className="px-4 py-3 whitespace-nowrap text-gray-500">
                    {new Date(entry.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-gray-900">
                      {entry.user_email}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      className={
                        ACTION_COLORS[entry.action] ??
                        "bg-gray-100 text-gray-800"
                      }
                    >
                      {entry.action}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-600">{entry.target_type}</span>
                    {entry.target_id && (
                      <code className="ml-1 rounded bg-gray-100 px-1 text-xs">
                        {entry.target_id}
                      </code>
                    )}
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-gray-500">
                    {entry.detail ?? "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">
                    {entry.ip_address ?? "—"}
                  </td>
                </tr>
              ))}
              {entries.length === 0 && !isLoading && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    No audit logs found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            className="rounded border px-3 py-1 text-sm disabled:opacity-50"
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page <= 1}
          >
            Prev
          </button>
          <span className="text-sm text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            className="rounded border px-3 py-1 text-sm disabled:opacity-50"
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
