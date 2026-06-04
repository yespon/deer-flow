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
import { Textarea } from "@/components/ui/textarea";
import { fetch } from "@/core/api/fetcher";

interface BrandConfig {
  enabled: boolean;
  brand_name?: string;
  forbidden_words?: string[];
  required_disclaimers?: string[];
  tone_guidelines?: string;
}

interface PolicyRule {
  name: string;
  rule_type: string;
  severity: string;
  words?: string[];
}

interface ComplianceConfig {
  enabled: boolean;
  sensitive_words?: string[];
  policy_rules?: PolicyRule[];
  auto_review?: boolean;
}

interface QuotaConfig {
  enabled: boolean;
  enforcement_mode?: string;
  default_quotas?: Record<string, string | number>;
}

export default function AdminCompliancePage() {
  const qc = useQueryClient();

  const { data: brandData, isLoading: brandLoading } = useQuery({
    queryKey: ["admin", "brand"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/brand");
      if (!res.ok) throw new Error("Failed to fetch brand config");
      return res.json() as Promise<BrandConfig>;
    },
  });

  const { data: complianceData, isLoading: complianceLoading } = useQuery({
    queryKey: ["admin", "compliance"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/compliance");
      if (!res.ok) throw new Error("Failed to fetch compliance config");
      return res.json() as Promise<ComplianceConfig>;
    },
  });

  const { data: quotaData, isLoading: quotaLoading } = useQuery({
    queryKey: ["admin", "quota"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/quota");
      if (!res.ok) throw new Error("Failed to fetch quota config");
      return res.json() as Promise<QuotaConfig>;
    },
  });

  // Brand editing state
  const [brandEditOpen, setBrandEditOpen] = useState(false);
  const [brandEditData, setBrandEditData] = useState("");
  const [newForbiddenWord, setNewForbiddenWord] = useState("");

  // Compliance editing state
  const [complianceEditOpen, setComplianceEditOpen] = useState(false);
  const [complianceEditData, setComplianceEditData] = useState("");
  const [newSensitiveWord, setNewSensitiveWord] = useState("");

  const brandUpdateMut = useMutation({
    mutationFn: async (newConfig: BrandConfig) => {
      const res = await fetch("/api/v1/admin/brand", {
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
      void qc.invalidateQueries({ queryKey: ["admin", "brand"] });
      setBrandEditOpen(false);
    },
  });

  const complianceUpdateMut = useMutation({
    mutationFn: async (newConfig: ComplianceConfig) => {
      const res = await fetch("/api/v1/admin/compliance", {
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
      void qc.invalidateQueries({ queryKey: ["admin", "compliance"] });
      setComplianceEditOpen(false);
    },
  });

  function addForbiddenWord() {
    if (!brandData || !newForbiddenWord.trim()) return;
    const words = [
      ...(brandData.forbidden_words ?? []),
      newForbiddenWord.trim(),
    ];
    void brandUpdateMut.mutate({ ...brandData, forbidden_words: words });
    setNewForbiddenWord("");
  }

  function removeForbiddenWord(word: string) {
    if (!brandData) return;
    const words = (brandData.forbidden_words ?? []).filter((w) => w !== word);
    void brandUpdateMut.mutate({ ...brandData, forbidden_words: words });
  }

  function addSensitiveWord() {
    if (!complianceData || !newSensitiveWord.trim()) return;
    const words = [
      ...(complianceData.sensitive_words ?? []),
      newSensitiveWord.trim(),
    ];
    void complianceUpdateMut.mutate({
      ...complianceData,
      sensitive_words: words,
    });
    setNewSensitiveWord("");
  }

  function removeSensitiveWord(word: string) {
    if (!complianceData) return;
    const words = (complianceData.sensitive_words ?? []).filter(
      (w) => w !== word,
    );
    void complianceUpdateMut.mutate({
      ...complianceData,
      sensitive_words: words,
    });
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">
        Compliance & Brand
      </h1>

      {/* Brand Compliance */}
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-medium text-gray-900">
            Brand Compliance
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (brandData) {
                setBrandEditData(JSON.stringify(brandData, null, 2));
                setBrandEditOpen(true);
              }
            }}
          >
            Edit Configuration
          </Button>
        </div>
        {brandLoading ? (
          <div className="py-4 text-center text-gray-400">Loading...</div>
        ) : brandData ? (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">Status</span>
              <Badge variant={brandData.enabled ? "default" : "outline"}>
                {brandData.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            {brandData.brand_name && (
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Brand Name
                </label>
                <p className="mt-0.5 text-sm font-medium text-gray-900">
                  {brandData.brand_name}
                </p>
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">
                Forbidden Words
              </label>
              <div className="mt-1 flex flex-wrap gap-1">
                {(brandData.forbidden_words ?? []).map((w) => (
                  <span
                    key={w}
                    className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2 py-1 text-xs text-red-700"
                  >
                    {w}
                    <button
                      onClick={() => removeForbiddenWord(w)}
                      className="text-red-400 hover:text-red-600"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <Input
                  value={newForbiddenWord}
                  onChange={(e) => setNewForbiddenWord(e.target.value)}
                  placeholder="Add word..."
                  className="h-8 w-40 text-sm"
                  onKeyDown={(e) => e.key === "Enter" && addForbiddenWord()}
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={addForbiddenWord}
                  disabled={!newForbiddenWord.trim()}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            {brandData.tone_guidelines && (
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Tone Guidelines
                </label>
                <p className="mt-0.5 text-sm text-gray-700">
                  {brandData.tone_guidelines}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="py-4 text-center text-gray-400">
            No brand configuration
          </div>
        )}
      </Card>

      {/* Content Compliance */}
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-medium text-gray-900">
            Content Compliance
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (complianceData) {
                setComplianceEditData(JSON.stringify(complianceData, null, 2));
                setComplianceEditOpen(true);
              }
            }}
          >
            Edit Configuration
          </Button>
        </div>
        {complianceLoading ? (
          <div className="py-4 text-center text-gray-400">Loading...</div>
        ) : complianceData ? (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">Status</span>
              <Badge variant={complianceData.enabled ? "default" : "outline"}>
                {complianceData.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 uppercase">
                Sensitive Words
              </label>
              <div className="mt-1 flex flex-wrap gap-1">
                {(complianceData.sensitive_words ?? []).map((w) => (
                  <span
                    key={w}
                    className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-700"
                  >
                    {w}
                    <button
                      onClick={() => removeSensitiveWord(w)}
                      className="text-amber-400 hover:text-amber-600"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <Input
                  value={newSensitiveWord}
                  onChange={(e) => setNewSensitiveWord(e.target.value)}
                  placeholder="Add word..."
                  className="h-8 w-40 text-sm"
                  onKeyDown={(e) => e.key === "Enter" && addSensitiveWord()}
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={addSensitiveWord}
                  disabled={!newSensitiveWord.trim()}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            {complianceData.policy_rules &&
              complianceData.policy_rules.length > 0 && (
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase">
                    Policy Rules
                  </label>
                  <div className="mt-2 space-y-2">
                    {complianceData.policy_rules.map((rule, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 rounded-md border border-gray-100 px-3 py-2 text-sm"
                      >
                        <span className="font-medium text-gray-900">
                          {rule.name}
                        </span>
                        <Badge variant="outline">{rule.rule_type}</Badge>
                        <Badge
                          className={
                            rule.severity === "block"
                              ? "bg-red-100 text-red-800"
                              : rule.severity === "high"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-gray-100 text-gray-800"
                          }
                        >
                          {rule.severity}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </div>
        ) : (
          <div className="py-4 text-center text-gray-400">
            No compliance configuration
          </div>
        )}
      </Card>

      {/* Quota Management */}
      <Card className="p-6">
        <h2 className="text-base font-medium text-gray-900">
          Quota Management
        </h2>
        {quotaLoading ? (
          <div className="py-4 text-center text-gray-400">Loading...</div>
        ) : quotaData ? (
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-600">Status</span>
              <Badge variant={quotaData.enabled ? "default" : "outline"}>
                {quotaData.enabled ? "Enabled" : "Disabled"}
              </Badge>
            </div>
            {quotaData.enforcement_mode && (
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Enforcement Mode
                </label>
                <p className="mt-0.5 text-sm font-medium text-gray-900">
                  {quotaData.enforcement_mode}
                </p>
              </div>
            )}
            {quotaData.default_quotas && (
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase">
                  Default Quotas
                </label>
                <div className="mt-1 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
                  {Object.entries(quotaData.default_quotas).map(([k, v]) => (
                    <div
                      key={k}
                      className="rounded-md border border-gray-100 px-3 py-2"
                    >
                      <span className="text-xs text-gray-500">{k}</span>
                      <p className="font-medium text-gray-900">{String(v)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-4 text-center text-gray-400">
            No quota configuration
          </div>
        )}
      </Card>

      {/* Brand Edit Dialog */}
      <Dialog open={brandEditOpen} onOpenChange={setBrandEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Brand Configuration</DialogTitle>
          </DialogHeader>
          <Textarea
            value={brandEditData}
            onChange={(e) => setBrandEditData(e.target.value)}
            className="min-h-[300px] font-mono text-sm"
          />
          {brandUpdateMut.isError && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {brandUpdateMut.error instanceof Error
                ? brandUpdateMut.error.message
                : "Update failed"}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setBrandEditOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                try {
                  void brandUpdateMut.mutate(JSON.parse(brandEditData));
                } catch {}
              }}
              disabled={brandUpdateMut.isPending}
            >
              {brandUpdateMut.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Compliance Edit Dialog */}
      <Dialog open={complianceEditOpen} onOpenChange={setComplianceEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Compliance Configuration</DialogTitle>
          </DialogHeader>
          <Textarea
            value={complianceEditData}
            onChange={(e) => setComplianceEditData(e.target.value)}
            className="min-h-[300px] font-mono text-sm"
          />
          {complianceUpdateMut.isError && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {complianceUpdateMut.error instanceof Error
                ? complianceUpdateMut.error.message
                : "Update failed"}
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setComplianceEditOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                try {
                  void complianceUpdateMut.mutate(
                    JSON.parse(complianceEditData),
                  );
                } catch {}
              }}
              disabled={complianceUpdateMut.isPending}
            >
              {complianceUpdateMut.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
