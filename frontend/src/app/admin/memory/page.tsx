"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

interface MemoryFact {
  id: string;
  content: string;
  category: string;
  confidence: number;
  createdAt: string;
  source: string;
}

interface MemoryData {
  version: string;
  lastUpdated: string;
  facts: MemoryFact[];
  user: {
    workContext: { summary: string };
    personalContext: { summary: string };
    topOfMind: { summary: string };
  };
}

interface MemoryConfig {
  enabled: boolean;
  storage_path: string;
  debounce_seconds: number;
  max_facts: number;
  fact_confidence_threshold: number;
  injection_enabled: boolean;
  max_injection_tokens: number;
}

function useMemory() {
  return useQuery({
    queryKey: ["admin", "memory"],
    queryFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/memory`);
      if (!res.ok) throw new Error("Failed to load memory");
      return res.json() as Promise<MemoryData>;
    },
  });
}

function useMemoryConfig() {
  return useQuery({
    queryKey: ["admin", "memory-config"],
    queryFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/memory/config`);
      if (!res.ok) throw new Error("Failed to load memory config");
      return res.json() as Promise<MemoryConfig>;
    },
  });
}

export default function AdminMemoryPage() {
  const { data: memory, isLoading: memLoading } = useMemory();
  const { data: memConfig, isLoading: cfgLoading } = useMemoryConfig();
  const qc = useQueryClient();

  const deleteFactMut = useMutation({
    mutationFn: async (factId: string) => {
      const res = await fetch(
        `${getBackendBaseURL()}/api/memory/facts/${factId}`,
        {
          method: "DELETE",
        },
      );
      if (!res.ok) throw new Error("Failed to delete fact");
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "memory"] });
    },
  });

  const reloadMut = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/memory/reload`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to reload");
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "memory"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Memory</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => reloadMut.mutate()}
          disabled={reloadMut.isPending}
        >
          Reload from file
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Config card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {cfgLoading ? (
              <div className="h-20 animate-pulse rounded bg-gray-100" />
            ) : memConfig ? (
              <>
                <div className="flex justify-between">
                  <span className="text-gray-600">Enabled</span>
                  <Badge variant={memConfig.enabled ? "default" : "outline"}>
                    {memConfig.enabled ? "Yes" : "No"}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Max facts</span>
                  <span>{memConfig.max_facts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Threshold</span>
                  <span>{memConfig.fact_confidence_threshold}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Injection</span>
                  <Badge
                    variant={
                      memConfig.injection_enabled ? "default" : "outline"
                    }
                  >
                    {memConfig.injection_enabled ? "On" : "Off"}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Max tokens</span>
                  <span>{memConfig.max_injection_tokens}</span>
                </div>
              </>
            ) : (
              <p className="text-gray-400">Not available</p>
            )}
          </CardContent>
        </Card>

        {/* User context card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">User Context</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {memLoading ? (
              <div className="h-20 animate-pulse rounded bg-gray-100" />
            ) : memory ? (
              <>
                <div>
                  <p className="font-medium text-gray-700">Work</p>
                  <p className="text-gray-500">
                    {memory.user.workContext.summary || "—"}
                  </p>
                </div>
                <div>
                  <p className="font-medium text-gray-700">Personal</p>
                  <p className="text-gray-500">
                    {memory.user.personalContext.summary || "—"}
                  </p>
                </div>
                <div>
                  <p className="font-medium text-gray-700">Top of Mind</p>
                  <p className="text-gray-500">
                    {memory.user.topOfMind.summary || "—"}
                  </p>
                </div>
              </>
            ) : (
              <p className="text-gray-400">Not available</p>
            )}
          </CardContent>
        </Card>

        {/* Facts card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Facts ({memory?.facts.length ?? 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="max-h-80 space-y-2 overflow-y-auto text-sm">
            {memLoading ? (
              <div className="h-20 animate-pulse rounded bg-gray-100" />
            ) : (memory?.facts ?? []).length === 0 ? (
              <p className="text-gray-400">No facts stored</p>
            ) : (
              memory?.facts.map((fact) => (
                <div
                  key={fact.id}
                  className="flex items-start justify-between gap-2 rounded-md bg-gray-50 p-2"
                >
                  <div className="min-w-0">
                    <p className="truncate text-gray-700">{fact.content}</p>
                    <div className="mt-1 flex gap-2">
                      <Badge variant="outline" className="text-xs">
                        {fact.category}
                      </Badge>
                      <span className="text-xs text-gray-400">
                        {(fact.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0 text-red-500 hover:text-red-600"
                    onClick={() => deleteFactMut.mutate(fact.id)}
                  >
                    ×
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
