"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

interface MCPServer {
  enabled: boolean;
  type: string;
  command?: string | null;
  args?: string[];
  url?: string | null;
  description?: string;
}

interface MCPConfig {
  mcp_servers: Record<string, MCPServer>;
}

function useMCPConfig() {
  return useQuery({
    queryKey: ["admin", "mcp"],
    queryFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/mcp/config`);
      return res.json() as Promise<MCPConfig>;
    },
  });
}

function useUpdateMCPConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (config: MCPConfig) => {
      const res = await fetch(`${getBackendBaseURL()}/api/mcp/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "mcp"] });
    },
  });
}

export default function AdminMcpPage() {
  const { data: config, isLoading } = useMCPConfig();
  const updateMut = useUpdateMCPConfig();
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("stdio");
  const [newCommand, setNewCommand] = useState("");
  const [newUrl, setNewUrl] = useState("");

  function toggleServer(name: string, enabled: boolean) {
    if (!config) return;
    void updateMut.mutate({
      mcp_servers: {
        ...config.mcp_servers,
        [name]: { ...config.mcp_servers[name], enabled } as MCPServer,
      },
    });
  }

  function addServer() {
    if (!config || !newName) return;
    const server: MCPServer = {
      enabled: true,
      type: newType,
      description: "",
    };
    if (newType === "stdio") {
      server.command = newCommand;
      server.args = [];
    } else {
      server.url = newUrl;
    }
    void updateMut.mutate({
      mcp_servers: { ...config.mcp_servers, [newName]: server },
    });
    setAddOpen(false);
    setNewName("");
    setNewCommand("");
    setNewUrl("");
  }

  const servers = config?.mcp_servers ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">MCP Servers</h1>
        <Button onClick={() => setAddOpen(true)} size="sm" className="gap-1">
          <Plus className="h-4 w-4" /> Add Server
        </Button>
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
                  Type
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Command / URL
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Enabled
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
              {Object.entries(servers).map(([name, server]) => (
                <tr
                  key={name}
                  className="border-b border-gray-50 hover:bg-gray-50/50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {name}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{server.type}</Badge>
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-gray-500">
                    {server.type === "stdio"
                      ? server.command
                      : (server.url ?? "—")}
                  </td>
                  <td className="px-4 py-3">
                    <Switch
                      checked={server.enabled}
                      onCheckedChange={(checked) => toggleServer(name, checked)}
                    />
                  </td>
                </tr>
              ))}
              {Object.keys(servers).length === 0 && !isLoading && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    No MCP servers configured
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add Server Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add MCP Server</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Name
              </label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="my-server"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Type
              </label>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant={newType === "stdio" ? "default" : "outline"}
                  onClick={() => setNewType("stdio")}
                >
                  stdio
                </Button>
                <Button
                  size="sm"
                  variant={newType === "sse" ? "default" : "outline"}
                  onClick={() => setNewType("sse")}
                >
                  sse
                </Button>
                <Button
                  size="sm"
                  variant={newType === "http" ? "default" : "outline"}
                  onClick={() => setNewType("http")}
                >
                  http
                </Button>
              </div>
            </div>
            {newType === "stdio" ? (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Command
                </label>
                <Input
                  value={newCommand}
                  onChange={(e) => setNewCommand(e.target.value)}
                  placeholder="npx"
                />
              </div>
            ) : (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  URL
                </label>
                <Input
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  placeholder="http://localhost:3000"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={addServer}
              disabled={!newName || updateMut.isPending}
            >
              Add
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
