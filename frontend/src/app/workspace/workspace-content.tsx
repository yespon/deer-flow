"use client";

import {
  MessageSquare,
  Compass,
  Settings,
  Menu,
  X,
  Pin,
  PinOff,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { MouseEvent } from "react";
import { useCallback, useMemo, useState } from "react";
import { Toaster } from "sonner";

import { QueryClientProvider } from "@/components/query-client-provider";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { CommandPalette } from "@/components/workspace/command-palette";
import { RecentChatList } from "@/components/workspace/recent-chat-list";
import { WorkspaceNavMenu } from "@/components/workspace/workspace-nav-menu";
import {
  usePinnedTools,
  type WorkspaceToolItem,
} from "@/components/workspace/workspace-tools";
import { useThreads } from "@/core/threads/hooks";
import { pathOfThread, titleOfThread } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

type WorkspaceChromeState = {
  searchOpen: boolean;
  toolboxOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  setToolboxOpen: (open: boolean) => void;
};

function isRouteTool(tool: WorkspaceToolItem) {
  return tool.href.startsWith("/");
}

function useWorkspaceToolAction({
  setSearchOpen,
  setToolboxOpen,
}: Pick<WorkspaceChromeState, "setSearchOpen" | "setToolboxOpen">) {
  const router = useRouter();

  return useCallback(
    (tool: WorkspaceToolItem) => {
      if (tool.action === "search") {
        setSearchOpen(true);
        return;
      }
      if (tool.action === "toolbox") {
        setToolboxOpen(true);
        return;
      }
      if (isRouteTool(tool)) {
        router.push(tool.href);
      }
    },
    [router, setSearchOpen, setToolboxOpen],
  );
}

function isToolActive(pathname: string, tool: WorkspaceToolItem) {
  if (!isRouteTool(tool)) return false;
  return pathname === tool.href || pathname.startsWith(`${tool.href}/`);
}

function WorkspaceToolButton({
  tool,
  isSidebarOpen,
  isActive,
  onRun,
}: {
  tool: WorkspaceToolItem;
  isSidebarOpen: boolean;
  isActive: boolean;
  onRun: (tool: WorkspaceToolItem) => void;
}) {
  const Icon = tool.icon;
  const content = (
    <>
      <span className="flex min-w-0 items-center gap-3">
        <Icon className="size-4 shrink-0" />
        {isSidebarOpen && <span className="truncate">{tool.title}</span>}
      </span>
      {isSidebarOpen && (
        <span className="ml-auto flex shrink-0 items-center gap-2">
          {tool.badge && (
            <span className="rounded-full border border-neutral-200 px-1.5 py-0.5 text-[10px] leading-none text-neutral-500">
              {tool.badge}
            </span>
          )}
          {tool.shortcut && (
            <span className="text-xs text-neutral-400">{tool.shortcut}</span>
          )}
        </span>
      )}
    </>
  );

  const className = cn(
    "h-9 rounded-md px-2.5 text-[13px] font-medium transition-colors",
    "text-neutral-700 hover:bg-neutral-200/70 hover:text-neutral-950",
    "data-[active=true]:bg-neutral-200 data-[active=true]:text-neutral-950",
    tool.id === "new-task" &&
      "border border-neutral-200 bg-white shadow-[0_1px_0_rgba(0,0,0,0.03)] hover:bg-neutral-100",
  );

  if (isRouteTool(tool)) {
    return (
      <SidebarMenuButton
        asChild
        isActive={isActive}
        tooltip={tool.title}
        className={className}
      >
        <Link href={tool.href}>{content}</Link>
      </SidebarMenuButton>
    );
  }

  return (
    <SidebarMenuButton
      asChild
      isActive={isActive}
      tooltip={tool.title}
      className={className}
    >
      <button type="button" onClick={() => onRun(tool)}>
        {content}
      </button>
    </SidebarMenuButton>
  );
}

function WorkspaceSearchDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { data: threads } = useThreads();
  const groupedThreads = useMemo(() => threads?.slice(0, 12) ?? [], [threads]);

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Search tasks"
      description="Search workspace tasks and chats"
      className="border-neutral-200 bg-white/95 shadow-2xl backdrop-blur sm:max-w-2xl"
    >
      <CommandInput
        placeholder="Search tasks..."
        className="text-base placeholder:text-neutral-400"
      />
      <CommandList className="max-h-[420px] px-2 py-3">
        <CommandEmpty>No tasks found.</CommandEmpty>
        <CommandGroup heading="Recent tasks">
          {groupedThreads.map((thread) => (
            <CommandItem
              key={thread.thread_id}
              value={titleOfThread(thread)}
              className="rounded-lg px-3 py-2.5"
              onSelect={() => {
                router.push(pathOfThread(thread));
                onOpenChange(false);
              }}
            >
              <MessageSquare className="size-4 text-neutral-500" />
              <span className="truncate">{titleOfThread(thread)}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

function WorkspaceToolboxDialog({
  open,
  onOpenChange,
  onRunTool,
  toolboxSections,
  isPinned,
  togglePin,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRunTool: (tool: WorkspaceToolItem) => void;
  toolboxSections: { id: string; title: string; items: WorkspaceToolItem[] }[];
  isPinned: (id: string) => boolean;
  togglePin: (id: string) => void;
}) {
  const handleSelect = (tool: WorkspaceToolItem) => {
    onOpenChange(false);
    onRunTool(tool);
  };

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Toolbox"
      description="Search and launch workspace tools"
      className="border-neutral-200 bg-white/95 shadow-2xl backdrop-blur sm:max-w-3xl"
    >
      <CommandInput
        placeholder="Search tools..."
        className="text-base placeholder:text-neutral-400"
      />
      <CommandList className="max-h-[520px] px-3 py-4">
        <CommandEmpty>No tools found.</CommandEmpty>
        {toolboxSections.map((section) => (
          <CommandGroup
            key={section.id}
            heading={section.title}
            className="[&_[cmdk-group-heading]]:px-1 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:tracking-[0.16em] [&_[cmdk-group-heading]]:text-neutral-400 [&_[cmdk-group-heading]]:uppercase"
          >
            <div className="grid grid-cols-1 gap-2 py-1 sm:grid-cols-2">
              {section.items.map((tool) => {
                const Icon = tool.icon;
                const pinned = isPinned(tool.id);
                return (
                  <CommandItem
                    key={tool.id}
                    value={`${tool.title} ${tool.description}`}
                    className="group relative min-h-[68px] rounded-lg px-3 py-3"
                    onSelect={() => handleSelect(tool)}
                  >
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-neutral-200 bg-white text-neutral-600">
                      <Icon className="size-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate pr-4 font-medium text-neutral-800">
                        {tool.title}
                      </span>
                      <span className="block truncate text-xs text-neutral-400">
                        {tool.description}
                      </span>
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        togglePin(tool.id);
                      }}
                      className={cn(
                        "absolute top-2 right-2 flex size-3.5 items-center justify-center rounded transition-colors",
                        pinned
                          ? "text-neutral-400 hover:text-neutral-600"
                          : "text-neutral-200 hover:text-neutral-400",
                      )}
                      title={pinned ? "Unpin from sidebar" : "Pin to sidebar"}
                    >
                      {pinned ? (
                        <Pin className="size-[7px]" />
                      ) : (
                        <PinOff className="size-[7px]" />
                      )}
                    </button>
                  </CommandItem>
                );
              })}
            </div>
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}

// ============================================================================
// New Workspace Sidebar Content
// ============================================================================
function NewWorkspaceSidebar({
  setSearchOpen,
  setToolboxOpen,
  sidebarSections,
}: Pick<WorkspaceChromeState, "setSearchOpen" | "setToolboxOpen"> & {
  sidebarSections: { id: string; title?: string; items: WorkspaceToolItem[] }[];
}) {
  const { open: isSidebarOpen } = useSidebar();
  const pathname = usePathname();
  const runTool = useWorkspaceToolAction({ setSearchOpen, setToolboxOpen });

  return (
    <Sidebar
      variant="sidebar"
      collapsible="icon"
      className="border-r border-neutral-200/70"
    >
      {/* Logo Header */}
      <SidebarHeader className="px-3 py-4">
        <div className="flex items-center justify-between gap-2">
          <Link
            href="/workspace/chats/new"
            className="flex min-w-0 items-center gap-2"
          >
            <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-neutral-900 text-[10px] font-bold text-white">
              P
            </div>
            {isSidebarOpen && (
              <span className="min-w-0 leading-tight">
                <span className="block truncate text-sm font-semibold text-neutral-900">
                  Prism
                </span>
                <span className="block truncate text-[10px] font-medium text-neutral-500">
                  Enterprise
                </span>
              </span>
            )}
          </Link>
          <div
            className={cn(
              "transition-opacity",
              isSidebarOpen ? "opacity-100" : "opacity-0",
            )}
          >
            <SidebarTrigger className="size-7 rounded-md text-neutral-500 hover:bg-neutral-200/70" />
          </div>
        </div>
      </SidebarHeader>

      {/* Nav Items */}
      <SidebarContent className="gap-0 px-2 py-2">
        {sidebarSections.map((section, index) => (
          <div
            key={section.id}
            className={cn(
              index > 0 && "mt-3 border-t border-neutral-200/70 pt-3",
            )}
          >
            <SidebarMenu>
              {section.items.map((tool) => (
                <SidebarMenuItem key={tool.id}>
                  <WorkspaceToolButton
                    tool={tool}
                    isSidebarOpen={isSidebarOpen}
                    isActive={isToolActive(pathname, tool)}
                    onRun={runTool}
                  />
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </div>
        ))}

        {/* Recent Chats Section */}
        {isSidebarOpen && (
          <div className="mt-4 border-t border-neutral-200/70 pt-4">
            <div className="px-2 py-2 text-[11px] font-medium tracking-wide text-neutral-400">
              Conversations
            </div>
            <RecentChatList showLabel={false} />
          </div>
        )}
      </SidebarContent>

      {/* Footer */}
      <SidebarFooter className="border-t border-neutral-200/70 p-2">
        <WorkspaceNavMenu />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

// ============================================================================
// Mobile Header
// ============================================================================
function MobileHeader({
  setSearchOpen,
  setToolboxOpen,
  sidebarSections,
}: Pick<WorkspaceChromeState, "setSearchOpen" | "setToolboxOpen"> & {
  sidebarSections: { id: string; title?: string; items: WorkspaceToolItem[] }[];
}) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const runTool = useWorkspaceToolAction({ setSearchOpen, setToolboxOpen });

  return (
    <>
      <header className="fixed top-0 right-0 left-0 z-50 flex h-14 items-center justify-between border-b border-gray-100 bg-white px-4 lg:hidden">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
            <div className="h-3.5 w-3.5 rotate-45 transform rounded-sm bg-white" />
          </div>
          <span className="font-semibold text-gray-900">Prism</span>
        </Link>
        <div className="flex items-center gap-2">
          <Link
            href="/workspace/chats/new"
            className="rounded-lg bg-gray-100 p-2 text-gray-700"
          >
            <MessageSquare className="h-5 w-5" />
          </Link>
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="rounded-lg bg-gray-100 p-2 text-gray-700"
          >
            {isMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {isMenuOpen && (
        <div className="fixed inset-0 top-14 z-40 bg-white lg:hidden">
          <nav className="space-y-2 p-4">
            {sidebarSections
              .flatMap((section) => section.items)
              .map((item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  onClick={(event: MouseEvent<HTMLAnchorElement>) => {
                    if (!isRouteTool(item)) {
                      event.preventDefault();
                      runTool(item);
                    }
                    setIsMenuOpen(false);
                  }}
                  className="flex items-center gap-3 rounded-xl px-4 py-3 text-gray-700 hover:bg-gray-50"
                >
                  <item.icon className="h-5 w-5" />
                  <span className="font-medium">{item.title}</span>
                  {item.badge && (
                    <span className="ml-auto rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {item.badge}
                    </span>
                  )}
                </Link>
              ))}
          </nav>
        </div>
      )}
    </>
  );
}

// ============================================================================
// Mobile Bottom Navigation
// ============================================================================
const MOBILE_NAV_ITEMS = [
  {
    id: "chat",
    label: "对话",
    icon: MessageSquare,
    href: "/workspace/chats/new",
  },
  { id: "explore", label: "探索", icon: Compass, href: "#" },
  { id: "settings", label: "设置", icon: Settings, href: "#" },
];

function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="pb-safe fixed right-0 bottom-0 left-0 z-50 border-t border-gray-200 bg-white px-4 py-2 lg:hidden">
      <div className="flex items-center justify-around">
        {MOBILE_NAV_ITEMS.map((item) => {
          const isChatActive =
            pathname === item.href || pathname.startsWith("/workspace/chats");
          const active =
            item.id === "chat" ? isChatActive : pathname === item.href;
          return (
            <Link
              key={item.id}
              href={item.href}
              className={cn(
                "flex min-w-[64px] flex-col items-center gap-0.5 rounded-lg p-2 transition-colors",
                active ? "text-gray-900" : "text-gray-400 hover:text-gray-600",
              )}
            >
              <item.icon className="h-5 w-5" />
              <span className="text-[10px] font-medium">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

// ============================================================================
// Main Workspace Content
// ============================================================================
export function WorkspaceContent({
  children,
  defaultOpen,
}: Readonly<{ children: React.ReactNode; defaultOpen?: boolean }>) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [toolboxOpen, setToolboxOpen] = useState(false);
  const runTool = useWorkspaceToolAction({ setSearchOpen, setToolboxOpen });
  const { toolboxSections, sidebarSections, isPinned, togglePin } =
    usePinnedTools();

  return (
    <QueryClientProvider>
      <SidebarProvider
        className="h-screen bg-[#f7f7f4]"
        defaultOpen={defaultOpen}
      >
        {/* Mobile Header */}
        <MobileHeader
          setSearchOpen={setSearchOpen}
          setToolboxOpen={setToolboxOpen}
          sidebarSections={sidebarSections}
        />

        {/* Desktop Sidebar */}
        <NewWorkspaceSidebar
          setSearchOpen={setSearchOpen}
          setToolboxOpen={setToolboxOpen}
          sidebarSections={sidebarSections}
        />

        {/* Main Content */}
        <SidebarInset className="min-w-0 bg-[#f7f7f4] pt-14 pb-16 lg:pt-0 lg:pb-0">
          {children}
        </SidebarInset>

        {/* Mobile Bottom Nav */}
        <MobileBottomNav />
        <WorkspaceSearchDialog open={searchOpen} onOpenChange={setSearchOpen} />
        <WorkspaceToolboxDialog
          open={toolboxOpen}
          onOpenChange={setToolboxOpen}
          onRunTool={runTool}
          toolboxSections={toolboxSections}
          isPinned={isPinned}
          togglePin={togglePin}
        />
      </SidebarProvider>
      <CommandPalette />
      <Toaster position="top-center" />
    </QueryClientProvider>
  );
}
