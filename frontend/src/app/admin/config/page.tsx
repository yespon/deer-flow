"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save, RotateCcw, AlertTriangle } from "lucide-react";
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
import { Textarea } from "@/components/ui/textarea";
import { TIER_COLORS, TIER_LABELS } from "@/core/admin/hooks";
import { fetch } from "@/core/api/fetcher";

interface ConfigSectionInfo {
  key: string;
  tier: number;
  description: string;
}

interface ConfigData {
  sections: ConfigSectionInfo[];
  config: Record<string, unknown>;
}

function useConfigData() {
  return useQuery({
    queryKey: ["admin", "config"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/config");
      if (!res.ok) throw new Error("Failed to fetch config");
      return res.json() as Promise<ConfigData>;
    },
  });
}

function useUpdateSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      section,
      data,
    }: {
      section: string;
      data: unknown;
    }) => {
      const res = await fetch(`/api/v1/admin/config/${section}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ section, data }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail ?? "Update failed");
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "config"] });
    },
  });
}

function useValidateSection() {
  return useMutation({
    mutationFn: async ({
      section,
      data,
    }: {
      section: string;
      data: unknown;
    }) => {
      const res = await fetch("/api/v1/admin/config/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ section, data }),
      });
      return res.json() as Promise<{ valid: boolean; errors: string[] }>;
    },
  });
}

export default function AdminConfigPage() {
  const { data, isLoading } = useConfigData();
  const updateMut = useUpdateSection();
  const validateMut = useValidateSection();
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  const sections = data?.sections ?? [];
  const config = data?.config ?? {};

  function startEdit(key: string) {
    const sectionData = config[key];
    setActiveSection(key);
    setEditValue(JSON.stringify(sectionData, null, 2));
    setValidationErrors([]);
  }

  async function handleValidate() {
    if (!activeSection) return;
    try {
      const parsed = JSON.parse(editValue);
      const result = await validateMut.mutateAsync({
        section: activeSection,
        data: parsed,
      });
      setValidationErrors(result.errors);
      if (result.valid) {
        setConfirmOpen(true);
      }
    } catch (e) {
      setValidationErrors([e instanceof Error ? e.message : "Invalid JSON"]);
    }
  }

  async function handleSave() {
    if (!activeSection) return;
    try {
      const parsed = JSON.parse(editValue);
      await updateMut.mutateAsync({ section: activeSection, data: parsed });
      setConfirmOpen(false);
      setActiveSection(null);
    } catch {
      // Error shown via mutation state
    }
  }

  if (isLoading) {
    return (
      <div className="py-12 text-center text-gray-400">
        Loading configuration...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Configuration</h1>

      {activeSection ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActiveSection(null)}
              >
                <RotateCcw className="mr-1 h-4 w-4" /> Back
              </Button>
              <h2 className="text-lg font-medium text-gray-900">
                {activeSection}
              </h2>
              {sections.find((s) => s.key === activeSection) && (
                <Badge
                  className={
                    TIER_COLORS[
                      sections.find((s) => s.key === activeSection)!.tier
                    ] ?? ""
                  }
                >
                  {TIER_LABELS[
                    sections.find((s) => s.key === activeSection)!.tier
                  ] ??
                    `Tier ${sections.find((s) => s.key === activeSection)!.tier}`}
                </Badge>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleValidate}
                disabled={validateMut.isPending}
              >
                Validate
              </Button>
              <Button
                size="sm"
                onClick={handleValidate}
                disabled={updateMut.isPending || validateMut.isPending}
              >
                <Save className="mr-1 h-4 w-4" /> Save
              </Button>
            </div>
          </div>

          {validationErrors.length > 0 && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              <ul className="list-disc pl-4">
                {validationErrors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

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

          <Card className="p-4">
            <Textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="min-h-[400px] font-mono text-sm"
              placeholder="Edit JSON configuration..."
            />
          </Card>

          {/* Save Confirmation Dialog */}
          <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500" />
                  Confirm Configuration Change
                </DialogTitle>
              </DialogHeader>
              <p className="text-sm text-gray-600">
                You are about to update the <strong>{activeSection}</strong>{" "}
                configuration section.
                {sections.find((s) => s.key === activeSection)?.tier === 2 && (
                  <span className="mt-2 block font-medium text-amber-700">
                    This section requires a server restart to take effect.
                  </span>
                )}
              </p>
              <DialogFooter>
                <Button variant="outline" onClick={() => setConfirmOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={updateMut.isPending}>
                  Confirm Save
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      ) : (
        <div className="grid gap-3">
          {sections.map((section) => {
            const sectionData = config[section.key];
            const isTier3 = section.tier === 3;
            return (
              <Card
                key={section.key}
                className={`cursor-pointer p-4 transition-colors hover:bg-gray-50 ${
                  isTier3 ? "opacity-70" : ""
                }`}
                onClick={() => !isTier3 && startEdit(section.key)}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">
                        {section.key}
                      </span>
                      <Badge className={TIER_COLORS[section.tier] ?? ""}>
                        {TIER_LABELS[section.tier] ?? `Tier ${section.tier}`}
                      </Badge>
                    </div>
                    <p className="mt-0.5 text-sm text-gray-500">
                      {section.description}
                    </p>
                  </div>
                  <div className="text-right">
                    {isTier3 ? (
                      <Badge variant="outline" className="text-red-600">
                        Edit config.yaml
                      </Badge>
                    ) : (
                      <Badge variant="outline">
                        {typeof sectionData === "object" ? "Editable" : "Value"}
                      </Badge>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
