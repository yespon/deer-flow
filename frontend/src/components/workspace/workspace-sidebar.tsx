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
  ChevronDown,
} from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";

import { RecentChatList } from "./recent-chat-list";

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
// Sidebar Component
// ============================================================================
export function WorkspaceSidebar({ className }: { className?: string }) {
  return (
    <aside
      className={cn(
        "fixed top-0 left-0 z-40 hidden h-screen w-64 flex-col border-r border-gray-100 bg-white lg:flex",
        className,
      )}
    >
      {/* Logo */}
      <div className="border-b border-gray-100 p-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
            <div className="h-4 w-4 rotate-45 transform rounded-sm bg-white" />
          </div>
          <span className="text-lg font-semibold text-gray-900">Prism</span>
        </Link>
      </div>

      {/* Nav Items */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {SIDEBAR_ITEMS.map((item) => (
          <Link
            key={item.id}
            href={item.href}
            className={cn(
              "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
              item.id === "new"
                ? "bg-gray-100 text-gray-900 hover:bg-gray-200"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
            )}
          >
            <span className="flex items-center gap-3">
              <item.icon className="h-4 w-4" />
              <span>{item.label}</span>
            </span>
            <span className="flex items-center gap-2">
              {item.badge && (
                <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">
                  {item.badge}
                </span>
              )}
              {item.shortcut && (
                <span className="text-xs text-gray-400">{item.shortcut}</span>
              )}
            </span>
          </Link>
        ))}

        {/* Recent Chats Section */}
        <div className="mt-4 border-t border-gray-100 pt-4">
          <div className="px-3 py-2 text-xs font-medium tracking-wider text-gray-400 uppercase">
            最近对话
          </div>
          <RecentChatList />
        </div>
      </nav>

      {/* User */}
      <div className="border-t border-gray-100 p-4">
        <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-gray-50">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500 text-sm font-medium text-white">
            U
          </div>
          <div className="flex-1 text-left">
            <p className="text-sm font-medium text-gray-900">用户名</p>
            <p className="text-xs text-gray-500">user@company.com</p>
          </div>
          <ChevronDown className="h-4 w-4 text-gray-400" />
        </button>
      </div>
    </aside>
  );
}

// ============================================================================
// Mobile Header
// ============================================================================
export function MobileHeader() {
  return (
    <header className="fixed top-0 right-0 left-0 z-50 flex h-14 items-center justify-between border-b border-gray-100 bg-white px-4 lg:hidden">
      <Link href="/" className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
          <div className="h-3.5 w-3.5 rotate-45 transform rounded-sm bg-white" />
        </div>
        <span className="font-semibold text-gray-900">Prism</span>
      </Link>
      <Link
        href="/workspace/chats/new"
        className="rounded-lg bg-gray-100 p-2 text-gray-700"
      >
        <MessageSquare className="h-5 w-5" />
      </Link>
    </header>
  );
}
