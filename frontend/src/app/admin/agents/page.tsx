"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Plus, Trash2 } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

interface AgentItem {
  name: string;
  description: string;
  model: string | null;
  tool_groups: string[] | null;
  skills: string[] | null;
  soul: string | null;
}

function useAgents() {
  return useQuery({
    queryKey: ["admin", "agents"],
    queryFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/agents`);
      if (!res.ok) throw new Error("Failed to load agents");
      const json = await res.json();
      return json.agents as AgentItem[];
    },
  });
}

export default function AdminAgentsPage() {
  const { data: agents, isLoading, error } = useAgents();
  const qc = useQueryClient();

  // Create agent
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newSoul, setNewSoul] = useState("");
  const createMut = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newName,
          description: newDesc,
          soul: newSoul,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Failed to create agent");
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "agents"] });
      setCreateOpen(false);
      setNewName("");
      setNewDesc("");
      setNewSoul("");
    },
  });

  // Delete agent
  const [deleteName, setDeleteName] = useState<string | null>(null);
  const deleteMut = useMutation({
    mutationFn: async (name: string) => {
      const res = await fetch(`${getBackendBaseURL()}/api/agents/${name}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Failed to delete agent");
      }
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "agents"] });
      setDeleteName(null);
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Agents</h1>
        <Button onClick={() => setCreateOpen(true)} size="sm" className="gap-1">
          <Plus className="h-4 w-4" /> Create Agent
        </Button>
      </div>

      {error && (
        <Card className="border-amber-200 bg-amber-50">
          <div className="p-4 text-sm text-amber-800">
            <strong>Note:</strong>{" "}
            {error instanceof Error ? error.message : "Failed to load agents"}.
            Make sure{" "}
            <code className="rounded bg-amber-100 px-1">
              agents_api.enabled=true
            </code>{" "}
            is set in config.yaml.
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading &&
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <div className="p-6">
                <div className="h-20 animate-pulse rounded bg-gray-100" />
              </div>
            </Card>
          ))}
        {agents?.map((agent) => (
          <Card key={agent.name}>
            <div className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-gray-400" />
                  <h3 className="font-medium text-gray-900">{agent.name}</h3>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDeleteName(agent.name)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
              {agent.description && (
                <p className="mt-2 text-sm text-gray-500">
                  {agent.description}
                </p>
              )}
              {agent.model && (
                <div className="mt-2">
                  <Badge variant="outline">Model: {agent.model}</Badge>
                </div>
              )}
              {agent.soul && (
                <p className="mt-3 line-clamp-3 text-xs whitespace-pre-wrap text-gray-400">
                  {agent.soul}
                </p>
              )}
            </div>
          </Card>
        ))}
        {agents?.length === 0 && !isLoading && (
          <div className="col-span-full rounded-lg border border-dashed border-gray-300 p-8 text-center text-gray-400">
            No custom agents yet
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Agent</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Name
              </label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="my-agent"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Description
              </label>
              <Input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="What this agent does"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                SOUL.md
              </label>
              <Textarea
                value={newSoul}
                onChange={(e) => setNewSoul(e.target.value)}
                placeholder="Define the agent's personality and behavioral guardrails..."
                rows={6}
              />
            </div>
            {createMut.isError && (
              <p className="text-sm text-red-600">{String(createMut.error)}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createMut.mutate()}
              disabled={!newName || createMut.isPending}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={!!deleteName} onOpenChange={() => setDeleteName(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Agent</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">
            Delete agent <strong>{deleteName}</strong>? This cannot be undone.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteName(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteName && deleteMut.mutate(deleteName)}
              disabled={deleteMut.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
