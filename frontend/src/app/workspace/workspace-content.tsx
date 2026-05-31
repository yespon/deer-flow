"use client";

import {
  Plus,
  Search,
  Sparkles,
  Command,
  FolderOpen,
  Cloud,
  Wrench,
  MessageSquare,
  Compass,
  Settings,
  Menu,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Toaster } from "sonner";

import { QueryClientProvider } from "@/components/query-client-provider";
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
  useSidebar,
} from "@/components/ui/sidebar";
import { CommandPalette } from "@/components/workspace/command-palette";
import { RecentChatList } from "@/components/workspace/recent-chat-list";
import { WorkspaceNavMenu } from "@/components/workspace/workspace-nav-menu";
import { cn } from "@/lib/utils";

// ============================================================================
// Sidebar Navigation Items
// ============================================================================
const SIDEBAR_ITEMS = [
  {
    id: "new",
    label: "新建对话",
    icon: Plus,
    shortcut: "⌘K",
    href: "/workspace/chats/new",
  },
  { id: "search", label: "搜索", icon: Search, href: "#" },
  { id: "studio", label: "工作室", icon: Sparkles, badge: "Beta", href: "#" },
  { id: "cli", label: "CLI", icon: Command, badge: "Beta", href: "#" },
  { id: "computer", label: "我的电脑", icon: FolderOpen, href: "#" },
  { id: "cloud", label: "云盘", icon: Cloud, href: "#" },
  { id: "toolbox", label: "工具箱", icon: Wrench, href: "#" },
];

// ============================================================================
// New Workspace Sidebar Content
// ============================================================================
function NewWorkspaceSidebar() {
  const { open: isSidebarOpen } = useSidebar();
  const pathname = usePathname();

  return (
    <Sidebar
      variant="sidebar"
      collapsible="icon"
      className="border-r border-gray-100"
    >
      {/* Logo Header */}
      <SidebarHeader className="border-b border-gray-100 p-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
            <div className="h-4 w-4 rotate-45 transform rounded-sm bg-white" />
          </div>
          {isSidebarOpen && (
            <span className="text-lg font-semibold text-gray-900">Prism</span>
          )}
        </Link>
      </SidebarHeader>

      {/* Nav Items */}
      <SidebarContent className="space-y-1 px-3 py-4">
        <SidebarMenu>
          {SIDEBAR_ITEMS.map((item) => (
            <SidebarMenuItem key={item.id}>
              <SidebarMenuButton
                asChild
                isActive={pathname === item.href}
                className={cn(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
                  item.id === "new"
                    ? "bg-gray-100 text-gray-900 hover:bg-gray-200"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                )}
              >
                <Link href={item.href}>
                  <span className="flex items-center gap-3">
                    <item.icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </span>
                  {isSidebarOpen && item.badge && (
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">
                      {item.badge}
                    </span>
                  )}
                  {isSidebarOpen && item.shortcut && (
                    <span className="text-xs text-gray-400">
                      {item.shortcut}
                    </span>
                  )}
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>

        {/* Recent Chats Section */}
        {isSidebarOpen && (
          <div className="mt-4 border-t border-gray-100 pt-4">
            <div className="px-3 py-2 text-xs font-medium tracking-wider text-gray-400 uppercase">
              最近对话
            </div>
            <RecentChatList />
          </div>
        )}
      </SidebarContent>

      {/* Footer */}
      <SidebarFooter className="border-t border-gray-100 p-4">
        <WorkspaceNavMenu />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

// ============================================================================
// Mobile Header
// ============================================================================
function MobileHeader() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

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
            <Plus className="h-5 w-5" />
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
            {SIDEBAR_ITEMS.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                onClick={() => setIsMenuOpen(false)}
                className="flex items-center gap-3 rounded-xl px-4 py-3 text-gray-700 hover:bg-gray-50"
              >
                <item.icon className="h-5 w-5" />
                <span className="font-medium">{item.label}</span>
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
  return (
    <QueryClientProvider>
      <SidebarProvider
        className="h-screen bg-[#F4F5F2]"
        defaultOpen={defaultOpen}
      >
        {/* Mobile Header */}
        <MobileHeader />

        {/* Desktop Sidebar */}
        <NewWorkspaceSidebar />

        {/* Main Content */}
        <SidebarInset className="min-w-0 bg-[#F4F5F2] pt-14 pb-16 lg:pt-0 lg:pb-0">
          {children}
        </SidebarInset>

        {/* Mobile Bottom Nav */}
        <MobileBottomNav />
      </SidebarProvider>
      <CommandPalette />
      <Toaster position="top-center" />
    </QueryClientProvider>
  );
}
