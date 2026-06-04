"use client";

import { useQuery } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

interface ModelInfo {
  name: string;
  model: string;
  display_name: string | null;
  description: string | null;
  supports_thinking: boolean;
  supports_reasoning_effort: boolean;
}

interface ModelsResponse {
  models: ModelInfo[];
  token_usage: { enabled: boolean };
}

function useModels() {
  return useQuery({
    queryKey: ["admin", "models"],
    queryFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/models`);
      return res.json() as Promise<ModelsResponse>;
    },
  });
}

export default function AdminModelsPage() {
  const { data, isLoading } = useModels();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Models</h1>
        {data?.token_usage && (
          <Badge variant={data.token_usage.enabled ? "default" : "outline"}>
            Token Usage {data.token_usage.enabled ? "On" : "Off"}
          </Badge>
        )}
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Name
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Model ID
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Description
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Capabilities
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    Loading...
                  </td>
                </tr>
              )}
              {data?.models.map((m) => (
                <tr
                  key={m.name}
                  className="border-b border-gray-50 hover:bg-gray-50/50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {m.display_name ?? m.name}
                  </td>
                  <td className="px-4 py-3">
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-700">
                      {m.model}
                    </code>
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-gray-500">
                    {m.description ?? "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {m.supports_thinking && (
                        <Badge
                          variant="outline"
                          className="bg-violet-50 text-violet-700"
                        >
                          Thinking
                        </Badge>
                      )}
                      {m.supports_reasoning_effort && (
                        <Badge
                          variant="outline"
                          className="bg-amber-50 text-amber-700"
                        >
                          Reasoning Effort
                        </Badge>
                      )}
                      {!m.supports_thinking && !m.supports_reasoning_effort && (
                        <span className="text-gray-400">Standard</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {data?.models.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    No models configured
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
