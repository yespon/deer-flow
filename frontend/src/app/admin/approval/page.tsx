"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { XCircle } from "lucide-react";
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

interface ApprovalConfig {
  enabled: boolean;
  default_timeout_hours: number;
  storage_path: string;
  notifications?: {
    channels?: string[];
    webhook_url?: string;
  };
}

interface ApprovalRequest {
  id: string;
  type: string;
  description: string;
  requested_by: string;
  requested_at: string;
  status: "pending" | "approved" | "rejected" | "expired";
  details?: string;
}

export default function AdminApprovalPage() {
  const qc = useQueryClient();
  const { data: config, isLoading } = useQuery({
    queryKey: ["admin", "approval"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/approval");
      if (!res.ok) throw new Error("Failed to fetch approval config");
      return res.json() as Promise<ApprovalConfig>;
    },
  });

  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState("");

  const updateMut = useMutation({
    mutationFn: async (newConfig: ApprovalConfig) => {
      const res = await fetch("/api/v1/admin/approval", {
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
      void qc.invalidateQueries({ queryKey: ["admin", "approval"] });
      setEditOpen(false);
    },
  });

  function startEdit() {
    if (!config) return;
    setEditData(JSON.stringify(config, null, 2));
    setEditOpen(true);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">
          Approval Workflow
        </h1>
        <Button variant="outline" size="sm" onClick={startEdit}>
          Edit Configuration
        </Button>
      </div>

      <Card className="p-6">
        {isLoading ? (
          <div className="py-8 text-center text-gray-400">Loading...</div>
        ) : config ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-600">Status</span>
              <Badge variant={config.enabled ? "default" : "outline"}>
                {config.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Default Timeout
                </label>
                <p className="mt-1 text-sm text-gray-900">
                  {config.default_timeout_hours ?? 24} hours
                </p>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Storage Path
                </label>
                <p className="mt-1 font-mono text-sm text-gray-900">
                  {config.storage_path ?? ".deer-flow/approvals"}
                </p>
              </div>
            </div>

            {config.notifications && (
              <div className="mt-4">
                <h3 className="mb-2 text-sm font-medium text-gray-700">
                  Notifications
                </h3>
                <div className="flex flex-wrap gap-2">
                  {config.notifications.channels?.map((ch) => (
                    <Badge key={ch} variant="outline">
                      {ch}
                    </Badge>
                  ))}
                </div>
                {config.notifications.webhook_url && (
                  <p className="mt-2 font-mono text-xs text-gray-500">
                    {config.notifications.webhook_url}
                  </p>
                )}
              </div>
            )}

            {!config.enabled && (
              <div className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                Human-in-Loop approval workflow is currently disabled. Enable it
                in config.yaml under the <code>approval</code> section or use
                the Edit button above.
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400">
            No approval configuration found
          </div>
        )}
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Approval Configuration</DialogTitle>
          </DialogHeader>
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
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                try {
                  void updateMut.mutate(JSON.parse(editData));
                } catch {}
              }}
              disabled={updateMut.isPending}
            >
              {updateMut.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
