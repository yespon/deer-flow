import { describe, expect, it } from "vitest";

import {
  TOOL_REGISTRY,
  buildToolboxSections,
  buildSidebarSections,
} from "@/components/workspace/workspace-tools";

const DEFAULT_PINNED_IDS = new Set(
  TOOL_REGISTRY.filter((t) => t.section === "pinned").map((t) => t.id),
);

describe("workspace tool registry", () => {
  it("excludes search, toolbox, and new-agent from toolbox dialog", () => {
    const sections = buildToolboxSections(DEFAULT_PINNED_IDS);
    const tools = sections.flatMap((section) => section.items);
    const ids = tools.map((t) => t.id);

    expect(ids).not.toContain("search");
    expect(ids).not.toContain("toolbox");
    expect(ids).not.toContain("new-agent");
  });

  it("keeps sidebar navigation grouped for the compact workspace layout", () => {
    const sections = buildSidebarSections(DEFAULT_PINNED_IDS);

    expect(sections.map((section) => section.id)).toEqual([
      "quick",
      "workspace",
      "tools",
    ]);
    expect(
      sections.flatMap((section) => section.items).map((item) => item.id),
    ).toEqual([
      "new-task",
      "search",
      "studio",
      "cli",
      "knowledge",
      "scheduled-tasks",
      "datasources",
      "toolbox",
    ]);
  });

  it("moves a tool from available to pinned when pinned", () => {
    const pinnedIds = new Set(DEFAULT_PINNED_IDS);
    pinnedIds.add("agents");

    const sections = buildToolboxSections(pinnedIds);
    const pinned = sections.find((s) => s.id === "pinned")!;
    const available = sections.find((s) => s.id === "available")!;

    expect(pinned.items.map((t) => t.id)).toContain("agents");
    expect(available.items.map((t) => t.id)).not.toContain("agents");
  });

  it("moves a tool from pinned to available when unpinned", () => {
    const pinnedIds = new Set(DEFAULT_PINNED_IDS);
    pinnedIds.delete("knowledge");

    const sections = buildToolboxSections(pinnedIds);
    const pinned = sections.find((s) => s.id === "pinned")!;
    const available = sections.find((s) => s.id === "available")!;

    expect(pinned.items.map((t) => t.id)).not.toContain("knowledge");
    expect(available.items.map((t) => t.id)).toContain("knowledge");
  });

  it("reflects unpinned tools in sidebar workspace section", () => {
    const pinnedIds = new Set(DEFAULT_PINNED_IDS);
    pinnedIds.delete("studio");

    const sections = buildSidebarSections(pinnedIds);
    const workspaceItems = sections.find((s) => s.id === "workspace")!;

    expect(workspaceItems.items.map((t) => t.id)).not.toContain("studio");
  });
});
