"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, KeyRound, Save } from "lucide-react";
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
import { fetch } from "@/core/api/fetcher";

interface SecretEntry {
  key: string;
  source: string;
  masked_value: string;
  is_env_ref: boolean;
}

function useSecrets() {
  return useQuery({
    queryKey: ["admin", "secrets"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/secrets");
      if (!res.ok) throw new Error("Failed to fetch secrets");
      return res.json() as Promise<{ secrets: SecretEntry[] }>;
    },
  });
}

function useUpdateSecret() {
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
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "secrets"] });
    },
  });
}

export default function AdminSecretsPage() {
  const { data, isLoading } = useSecrets();
  const updateMut = useUpdateSecret();
  const [editKey, setEditKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [showValue, setShowValue] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const secrets = data?.secrets ?? [];

  function startEdit(entry: SecretEntry) {
    setEditKey(entry.key);
    setEditValue("");
    setShowValue(false);
  }

  function handleSave() {
    if (!editKey || !editValue) return;
    void updateMut.mutate(
      { key: editKey, value: editValue },
      {
        onSuccess: () => {
          setConfirmOpen(false);
          setEditKey(null);
          setEditValue("");
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">API Keys</h1>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Key
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Source
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Value
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Type
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
              {secrets.map((entry) => (
                <tr
                  key={entry.key}
                  className="border-b border-gray-50 hover:bg-gray-50/50"
                >
                  <td className="px-4 py-3 font-mono text-xs text-gray-900">
                    {entry.key}
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline">{entry.source}</Badge>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {editKey === entry.key ? (
                      <div className="flex items-center gap-1">
                        <Input
                          type={showValue ? "text" : "password"}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          placeholder="Enter new value"
                          className="h-7 text-xs"
                          autoFocus
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0"
                          onClick={() => setShowValue(!showValue)}
                        >
                          {showValue ? (
                            <EyeOff className="h-3.5 w-3.5" />
                          ) : (
                            <Eye className="h-3.5 w-3.5" />
                          )}
                        </Button>
                      </div>
                    ) : (
                      entry.masked_value
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {entry.is_env_ref ? (
                      <Badge className="bg-blue-100 text-blue-800">
                        Env Var
                      </Badge>
                    ) : (
                      <Badge variant="outline">Literal</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {editKey === entry.key ? (
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setEditKey(null)}
                        >
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          disabled={!editValue}
                          onClick={() => setConfirmOpen(true)}
                        >
                          <Save className="mr-1 h-3.5 w-3.5" /> Save
                        </Button>
                      </div>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => startEdit(entry)}
                      >
                        <KeyRound className="mr-1 h-3.5 w-3.5" /> Update
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {secrets.length === 0 && !isLoading && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    No API keys found in configuration
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {updateMut.isError && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
          {updateMut.error instanceof Error
            ? updateMut.error.message
            : "Update failed"}
        </div>
      )}

      {updateMut.isSuccess && (
        <div className="rounded-md bg-green-50 p-3 text-sm text-green-700">
          {updateMut.data.message}
        </div>
      )}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update API Key</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">
            You are about to update{" "}
            <code className="rounded bg-gray-100 px-1">{editKey}</code>. This
            will modify the config.yaml file. A restart may be required.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateMut.isPending}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
