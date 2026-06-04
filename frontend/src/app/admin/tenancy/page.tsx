"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
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

interface Tenant {
  id: string;
  name: string;
  plan?: string;
  isolation_mode?: string;
}

interface TenancyConfig {
  enabled: boolean;
  default_isolation_mode?: string;
  header_name?: string;
  domain_pattern?: string;
  tenants?: Tenant[];
}

export default function AdminTenancyPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "tenancy"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/tenancy");
      if (!res.ok) throw new Error("Failed to fetch tenancy config");
      return res.json() as Promise<TenancyConfig>;
    },
  });

  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newId, setNewId] = useState("");
  const [newPlan, setNewPlan] = useState("pro");
  const [newIsolation, setNewIsolation] = useState("relaxed");

  const updateMut = useMutation({
    mutationFn: async (newConfig: TenancyConfig) => {
      const res = await fetch("/api/v1/admin/tenancy", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: newConfig }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Update failed");
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "tenancy"] });
      setAddOpen(false);
    },
  });

  function addTenant() {
    if (!data || !newName || !newId) return;
    const tenants = [
      ...(data.tenants ?? []),
      {
        id: newId,
        name: newName,
        plan: newPlan,
        isolation_mode: newIsolation,
      },
    ];
    void updateMut.mutate({ ...data, tenants });
    setNewName("");
    setNewId("");
    setNewPlan("pro");
    setNewIsolation("relaxed");
  }

  function removeTenant(tenantId: string) {
    if (!data) return;
    const tenants = (data.tenants ?? []).filter((t) => t.id !== tenantId);
    void updateMut.mutate({ ...data, tenants });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Tenancy</h1>
        <Button
          size="sm"
          className="gap-1"
          onClick={() => setAddOpen(true)}
          disabled={!data?.enabled}
        >
          <Plus className="h-4 w-4" /> Add Tenant
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
                  Default Isolation Mode
                </label>
                <p className="mt-1 text-sm text-gray-900">
                  {data.default_isolation_mode ?? "relaxed"}
                </p>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Header Name
                </label>
                <p className="mt-1 font-mono text-sm text-gray-900">
                  {data.header_name ?? "—"}
                </p>
              </div>
            </div>

            {data.domain_pattern && (
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Domain Pattern
                </label>
                <p className="mt-1 font-mono text-sm text-gray-900">
                  {data.domain_pattern}
                </p>
              </div>
            )}

            {data.tenants && data.tenants.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-2 text-sm font-medium text-gray-700">
                  Tenants ({data.tenants.length})
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 bg-gray-50/50">
                        <th className="px-3 py-2 text-left font-medium text-gray-600">
                          ID
                        </th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600">
                          Name
                        </th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600">
                          Plan
                        </th>
                        <th className="px-3 py-2 text-left font-medium text-gray-600">
                          Isolation
                        </th>
                        <th className="px-3 py-2 text-right font-medium text-gray-600">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.tenants.map((t, i) => (
                        <tr
                          key={i}
                          className="border-b border-gray-50 hover:bg-gray-50/50"
                        >
                          <td className="px-3 py-2 font-mono text-xs">
                            {t.id}
                          </td>
                          <td className="px-3 py-2 font-medium text-gray-900">
                            {t.name}
                          </td>
                          <td className="px-3 py-2">
                            <Badge variant="outline">{t.plan ?? "pro"}</Badge>
                          </td>
                          <td className="px-3 py-2">
                            <Badge
                              variant={
                                t.isolation_mode === "strict"
                                  ? "default"
                                  : "outline"
                              }
                            >
                              {t.isolation_mode ?? "relaxed"}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-500 hover:text-red-600"
                              onClick={() => removeTenant(t.id)}
                              disabled={updateMut.isPending}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {(!data.tenants || data.tenants.length === 0) && (
              <p className="py-4 text-center text-sm text-gray-400">
                No tenants configured
              </p>
            )}

            {!data.enabled && (
              <div className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                Multi-tenancy is currently disabled. Enable it in config.yaml
                under the <code>tenancy</code> section.
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400">
            No tenancy configuration found
          </div>
        )}
      </Card>

      {/* Add Tenant Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Tenant</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Tenant ID
              </label>
              <Input
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                placeholder="acme-corp"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Name
              </label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Acme Corporation"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Plan
                </label>
                <div className="flex gap-2">
                  {["free", "pro", "enterprise"].map((p) => (
                    <Button
                      key={p}
                      size="sm"
                      variant={newPlan === p ? "default" : "outline"}
                      onClick={() => setNewPlan(p)}
                    >
                      {p}
                    </Button>
                  ))}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Isolation
                </label>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={newIsolation === "relaxed" ? "default" : "outline"}
                    onClick={() => setNewIsolation("relaxed")}
                  >
                    Relaxed
                  </Button>
                  <Button
                    size="sm"
                    variant={newIsolation === "strict" ? "default" : "outline"}
                    onClick={() => setNewIsolation("strict")}
                  >
                    Strict
                  </Button>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={addTenant}
              disabled={!newId || !newName || updateMut.isPending}
            >
              {updateMut.isPending ? "Adding..." : "Add Tenant"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
