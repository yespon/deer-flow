"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

interface ChannelInfo {
  enabled: boolean;
  connected?: boolean;
  type?: string;
  webhook_url?: string;
  [key: string]: unknown;
}

interface ChannelStatusResponse {
  service_running: boolean;
  channels: Record<string, ChannelInfo>;
}

function useChannels() {
  return useQuery({
    queryKey: ["admin", "channels"],
    queryFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/channels/`);
      return res.json() as Promise<ChannelStatusResponse>;
    },
    refetchInterval: 15_000,
  });
}

function useRestartChannel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const res = await fetch(
        `${getBackendBaseURL()}/api/channels/${encodeURIComponent(name)}/restart`,
        {
          method: "POST",
        },
      );
      return res.json() as Promise<{ success: boolean; message: string }>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "channels"] });
    },
  });
}

export default function AdminChannelsPage() {
  const { data, isLoading } = useChannels();
  const restartMut = useRestartChannel();

  const channels = data?.channels ?? {};
  const channelEntries = Object.entries(channels);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Channels</h1>
        <Badge variant={data?.service_running ? "default" : "outline"}>
          {data?.service_running ? "Service Running" : "Service Stopped"}
        </Badge>
      </div>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Channel
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Type
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Status
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Enabled
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    Loading...
                  </td>
                </tr>
              )}
              {channelEntries.map(([name, info]) => (
                <tr
                  key={name}
                  className="border-b border-gray-50 hover:bg-gray-50/50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {name}
                  </td>
                  <td className="px-4 py-3">
                    {info.type ? (
                      <Badge variant="outline">{info.type}</Badge>
                    ) : (
                      <span className="text-gray-400">&mdash;</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={info.connected ? "default" : "secondary"}
                      className={
                        info.connected
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-600"
                      }
                    >
                      {info.connected ? "Connected" : "Disconnected"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={info.enabled ? "default" : "secondary"}
                      className={
                        info.enabled
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-600"
                      }
                    >
                      {info.enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      size="sm"
                      variant="outline"
                      className="gap-1"
                      disabled={restartMut.isPending}
                      onClick={() => restartMut.mutate(name)}
                    >
                      <RefreshCw
                        className={`h-3.5 w-3.5 ${restartMut.isPending ? "animate-spin" : ""}`}
                      />
                      Restart
                    </Button>
                  </td>
                </tr>
              ))}
              {channelEntries.length === 0 && !isLoading && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    {data?.service_running
                      ? "No channels configured"
                      : "Channel service is not running"}
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
