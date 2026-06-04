"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import { Textarea } from "@/components/ui/textarea";
import { fetch } from "@/core/api/fetcher";

interface RbacConfig {
  enabled: boolean;
  model_config?: string;
  policy_file?: string;
  default_roles?: string[];
  role_permissions?: Record<string, string[]>;
}

export default function AdminRbacPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "rbac"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/rbac");
      if (!res.ok) throw new Error("Failed to fetch RBAC config");
      return res.json() as Promise<RbacConfig>;
    },
  });

  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);

  const updateMut = useMutation({
    mutationFn: async (newData: RbacConfig) => {
      const res = await fetch("/api/v1/admin/rbac", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: newData }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Update failed");
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "rbac"] });
      setConfirmOpen(false);
      setEditOpen(false);
    },
  });

  function startEdit() {
    if (!data) return;
    setEditData(JSON.stringify(data, null, 2));
    setEditOpen(true);
  }

  function handleSave() {
    try {
      const parsed = JSON.parse(editData) as RbacConfig;
      setConfirmOpen(true);
      void updateMut.mutate(parsed);
    } catch {
      // JSON parse error shown in textarea
    }
  }

  const defaultRoles = data?.default_roles ?? [
    "tenant_admin",
    "project_manager",
    "developer",
    "operator",
    "external",
  ];
  const rolePerms = data?.role_permissions ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">RBAC</h1>
        <Button variant="outline" size="sm" onClick={startEdit}>
          Edit Configuration
        </Button>
      </div>

      <Card className="p-6">
        {isLoading ? (
          <div className="py-8 text-center text-gray-400">Loading...</div>
        ) : data ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-600">Status</span>
              <Badge variant={data.enabled ? "default" : "outline"}>
                {data.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Model Config Path
                </label>
                <p className="mt-1 font-mono text-sm text-gray-900">
                  {data.model_config ?? "Default"}
                </p>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Policy File
                </label>
                <p className="mt-1 font-mono text-sm text-gray-900">
                  {data.policy_file ?? "—"}
                </p>
              </div>
            </div>

            {/* Role & Permission Matrix */}
            <div className="mt-4 rounded-md border border-gray-200 p-4">
              <h3 className="mb-3 text-sm font-medium text-gray-700">
                Roles & Permissions
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="px-3 py-2 text-left font-medium text-gray-600">
                        Role
                      </th>
                      <th className="px-3 py-2 text-left font-medium text-gray-600">
                        Permissions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {defaultRoles.map((role) => (
                      <tr key={role} className="border-b border-gray-50">
                        <td className="px-3 py-2">
                          <Badge
                            variant="outline"
                            className="font-mono text-xs"
                          >
                            {role}
                          </Badge>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-1">
                            {(rolePerms[role] ?? []).map((perm) => (
                              <Badge
                                key={perm}
                                variant="secondary"
                                className="text-xs"
                              >
                                {perm}
                              </Badge>
                            ))}
                            {(!rolePerms[role] ??
                              rolePerms[role].length === 0) && (
                              <span className="text-xs text-gray-400">
                                No permissions defined
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {!data.enabled && (
              <div className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                RBAC is currently disabled. Enable it in config.yaml under the{" "}
                <code>rbac</code> section or use the Edit button above.
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400">
            No RBAC configuration found
          </div>
        )}
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit RBAC Configuration</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-gray-500">
              Edit the RBAC configuration as JSON. Changes are audited and may
              require a server restart.
            </p>
            <Textarea
              value={editData}
              onChange={(e) => setEditData(e.target.value)}
              className="min-h-[300px] font-mono text-sm"
            />
            {updateMut.isError && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                {updateMut.error instanceof Error
                  ? updateMut.error.message
                  : "Update failed"}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateMut.isPending}>
              {updateMut.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
