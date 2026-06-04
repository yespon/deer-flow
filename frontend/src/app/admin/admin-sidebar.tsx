"use client";

import {
  BarChart3,
  Bot,
  Cpu,
  Database,
  KeyRound,
  LayoutDashboard,
  MessageSquare,
  Puzzle,
  ScrollText,
  Server,
  Settings,
  ShieldCheck,
  Users,
  FileCheck,
  Building2,
  Lock,
  BookOpen,
  AlertOctagon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { RestartButton } from "./restart-banner";

const NAV_ITEMS = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/runs", label: "Runs", icon: ScrollText },
  { href: "/admin/models", label: "Models", icon: Cpu },
  { href: "/admin/skills", label: "Skills", icon: Puzzle },
  { href: "/admin/mcp", label: "MCP", icon: Server },
  { href: "/admin/agents", label: "Agents", icon: Bot },
  { href: "/admin/memory", label: "Memory", icon: Database },
  { href: "/admin/channels", label: "Channels", icon: MessageSquare },
  { href: "/admin/config", label: "Config", icon: Settings },
  { href: "/admin/config/secrets", label: "API Keys", icon: KeyRound },
  { href: "/admin/audit", label: "Audit Log", icon: FileCheck },
  { href: "/admin/tenancy", label: "Tenancy", icon: Building2 },
  { href: "/admin/rbac", label: "RBAC", icon: Lock },
  { href: "/admin/approval", label: "Approval", icon: ShieldCheck },
  { href: "/admin/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/admin/compliance", label: "Compliance", icon: AlertOctagon },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-56 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-14 items-center gap-2 border-b border-gray-200 px-4">
        <BarChart3 className="h-5 w-5 text-gray-700" />
        <span className="text-sm font-semibold text-gray-900">Admin</span>
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/admin"
              ? pathname === "/admin"
              : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-gray-100 font-medium text-gray-900"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="space-y-2 border-t border-gray-200 p-3">
        <RestartButton />
        <Link
          href="/workspace"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-900"
        >
          &larr; Back to Workspace
        </Link>
      </div>
    </aside>
  );
}
