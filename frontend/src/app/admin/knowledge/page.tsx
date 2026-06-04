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
import { Textarea } from "@/components/ui/textarea";
import { fetch } from "@/core/api/fetcher";

interface KnowledgeConfig {
  enabled: boolean;
  vector_store?: { provider?: string; collection_name?: string };
  embedding?: { provider?: string; model?: string };
  chunking?: { strategy?: string; chunk_size?: number; overlap?: number };
  retrieval?: {
    top_k?: number;
    similarity_threshold?: number;
    max_context_length?: number;
  };
}

export default function AdminKnowledgePage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "knowledge"],
    queryFn: async () => {
      const res = await fetch("/api/v1/admin/knowledge-base");
      if (!res.ok) throw new Error("Failed to fetch knowledge base config");
      return res.json() as Promise<KnowledgeConfig>;
    },
  });

  const [editOpen, setEditOpen] = useState(false);
  const [editData, setEditData] = useState("");

  const updateMut = useMutation({
    mutationFn: async (newConfig: KnowledgeConfig) => {
      const res = await fetch("/api/v1/admin/knowledge-base", {
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
      void qc.invalidateQueries({ queryKey: ["admin", "knowledge"] });
      setEditOpen(false);
    },
  });

  function startEdit() {
    if (!data) return;
    setEditData(JSON.stringify(data, null, 2));
    setEditOpen(true);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Knowledge Base</h1>
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

            {data.vector_store && (
              <div className="rounded-md border border-gray-200 p-4">
                <h3 className="mb-2 text-sm font-medium text-gray-700">
                  Vector Store
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Provider:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.vector_store.provider ?? "chroma"}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Collection:</span>{" "}
                    <code className="text-xs">
                      {data.vector_store.collection_name ?? "deerflow_kb"}
                    </code>
                  </div>
                </div>
              </div>
            )}

            {data.embedding && (
              <div className="rounded-md border border-gray-200 p-4">
                <h3 className="mb-2 text-sm font-medium text-gray-700">
                  Embedding
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Provider:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.embedding.provider ?? "openai"}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Model:</span>{" "}
                    <code className="text-xs">
                      {data.embedding.model ?? "—"}
                    </code>
                  </div>
                </div>
              </div>
            )}

            {data.chunking && (
              <div className="rounded-md border border-gray-200 p-4">
                <h3 className="mb-2 text-sm font-medium text-gray-700">
                  Chunking
                </h3>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Strategy:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.chunking.strategy ?? "paragraphs"}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Chunk Size:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.chunking.chunk_size ?? 1000}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Overlap:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.chunking.overlap ?? 100}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {data.retrieval && (
              <div className="rounded-md border border-gray-200 p-4">
                <h3 className="mb-2 text-sm font-medium text-gray-700">
                  Retrieval
                </h3>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Top K:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.retrieval.top_k ?? 5}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Similarity:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.retrieval.similarity_threshold ?? 0.7}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Max Context:</span>{" "}
                    <span className="font-medium text-gray-900">
                      {data.retrieval.max_context_length ?? 4000}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {!data.enabled && (
              <div className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                Knowledge Base is currently disabled. Enable it in config.yaml
                under the <code>knowledge_base</code> section or use the Edit
                button above.
              </div>
            )}
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400">
            No knowledge base configuration found
          </div>
        )}
      </Card>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Knowledge Base Configuration</DialogTitle>
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
