"use client";

/**
 * Prism Dashboard - Main Interface After Login
 * Based on MuleRun chat interface design
 */

import {
  Image,
  Video,
  BarChart3,
  Globe,
  FileText,
  Search,
  Send,
  Paperclip,
  ChevronDown,
  MessageSquare,
  Clock,
  Settings,
  Users,
  Compass,
  Sparkles,
  Zap,
  FileImage,
  FileCode,
  FileSpreadsheet,
  Music,
  Command,
  FolderOpen,
  Cloud,
  Wrench,
  Plus,
} from "lucide-react";
import Link from "next/link";
import React, { useState, useEffect, useCallback, useRef } from "react";

import { cn } from "@/lib/utils";

// ============================================================================
// Types
// ============================================================================

interface QuickAction {
  id: string;
  title: string;
  icon: React.ReactNode;
  prompt: string;
  model?: string;
}

interface RecentConversation {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
  unread?: boolean;
}

interface Deliverable {
  id: string;
  name: string;
  type: "image" | "video" | "document" | "code" | "spreadsheet" | "audio";
  createdAt: string;
}

// ============================================================================
// Mock Data
// ============================================================================

const QUICK_ACTIONS: QuickAction[] = [
  {
    id: "generate-image",
    title: "生成图片",
    icon: <Image className="h-5 w-5" />,
    prompt: "帮我生成一张",
    model: "GPT Image 2",
  },
  {
    id: "create-video",
    title: "创建视频",
    icon: <Video className="h-5 w-5" />,
    prompt: "帮我创建一个视频",
  },
  {
    id: "trading",
    title: "交易",
    icon: <BarChart3 className="h-5 w-5" />,
    prompt: "帮我分析交易机会",
  },
  {
    id: "create-game",
    title: "创建游戏",
    icon: <Sparkles className="h-5 w-5" />,
    prompt: "帮我创建一个游戏",
  },
  {
    id: "create-website",
    title: "创建网站",
    icon: <Globe className="h-5 w-5" />,
    prompt: "帮我创建一个网站",
  },
  {
    id: "data-analysis",
    title: "数据分析",
    icon: <BarChart3 className="h-5 w-5" />,
    prompt: "帮我分析这份数据",
  },
  {
    id: "ecommerce",
    title: "电子商务",
    icon: <FileText className="h-5 w-5" />,
    prompt: "帮我优化电商运营",
  },
];

const SIDEBAR_ITEMS = [
  {
    id: "new",
    label: "新建任务",
    icon: <Plus className="h-4 w-4" />,
    shortcut: "⌘K",
  },
  { id: "search", label: "搜索", icon: <Search className="h-4 w-4" /> },
  {
    id: "studio",
    label: "工作室",
    icon: <Sparkles className="h-4 w-4" />,
    badge: "Beta",
  },
  {
    id: "cli",
    label: "CLI",
    icon: <Command className="h-4 w-4" />,
    badge: "Beta",
  },
  {
    id: "computer",
    label: "我的电脑",
    icon: <FolderOpen className="h-4 w-4" />,
  },
  { id: "cloud", label: "云盘", icon: <Cloud className="h-4 w-4" /> },
  { id: "toolbox", label: "工具箱", icon: <Wrench className="h-4 w-4" /> },
];

const RECENT_CONVERSATIONS: RecentConversation[] = [
  {
    id: "1",
    title: "网站设计讨论",
    preview: "我们可以使用 React 和 Tailwind 来构建...",
    timestamp: "10 分钟前",
    unread: true,
  },
  {
    id: "2",
    title: "数据分析报告",
    preview: "Q4 季度的销售数据显示出明显的增长趋势...",
    timestamp: "1 小时前",
  },
  {
    id: "3",
    title: "产品文案优化",
    preview: "帮我优化一下这个 landing page 的文案...",
    timestamp: "3 小时前",
  },
  {
    id: "4",
    title: "代码审查",
    preview: "这段代码可以简化一下，建议用解构赋值...",
    timestamp: "昨天",
  },
];

const DELIVERABLES: Deliverable[] = [
  { id: "1", name: "产品宣传图.png", type: "image", createdAt: "10 分钟前" },
  {
    id: "2",
    name: "Q4 销售报告.xlsx",
    type: "spreadsheet",
    createdAt: "1 小时前",
  },
  { id: "3", name: "landing-page.tsx", type: "code", createdAt: "2 小时前" },
  { id: "4", name: "品牌视频.mp4", type: "video", createdAt: "3 小时前" },
  { id: "5", name: "调研报告.pdf", type: "document", createdAt: "昨天" },
  { id: "6", name: "背景音乐.mp3", type: "audio", createdAt: "昨天" },
];

// ============================================================================
// Helper Functions
// ============================================================================

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

function getDeliverableIcon(type: Deliverable["type"]) {
  switch (type) {
    case "image":
      return <FileImage className="h-4 w-4 text-violet-500" />;
    case "video":
      return <Video className="h-4 w-4 text-fuchsia-500" />;
    case "document":
      return <FileText className="h-4 w-4 text-blue-500" />;
    case "code":
      return <FileCode className="h-4 w-4 text-emerald-500" />;
    case "spreadsheet":
      return <FileSpreadsheet className="h-4 w-4 text-cyan-500" />;
    case "audio":
      return <Music className="h-4 w-4 text-amber-500" />;
    default:
      return <FileText className="h-4 w-4 text-gray-500" />;
  }
}

function getDeliverableBgColor(type: Deliverable["type"]) {
  switch (type) {
    case "image":
      return "bg-violet-50";
    case "video":
      return "bg-fuchsia-50";
    case "document":
      return "bg-blue-50";
    case "code":
      return "bg-emerald-50";
    case "spreadsheet":
      return "bg-cyan-50";
    case "audio":
      return "bg-amber-50";
    default:
      return "bg-gray-50";
  }
}

// ============================================================================
// Components
// ============================================================================

/**
 * Sidebar Navigation
 */
function Sidebar() {
  return (
    <aside className="fixed top-0 left-0 z-40 hidden h-screen w-64 flex-col border-r border-gray-100 bg-white lg:flex">
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
          <button
            key={item.id}
            className={cn(
              "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
              item.id === "new"
                ? "bg-gray-100 text-gray-900 hover:bg-gray-200"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
            )}
          >
            <span className="flex items-center gap-3">
              {item.icon}
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
          </button>
        ))}

        {/* Tasks Section */}
        <div className="mt-4 border-t border-gray-100 pt-4">
          <div className="px-3 py-2 text-xs font-medium tracking-wider text-gray-400 uppercase">
            你的任务
          </div>
          <div className="px-3 py-4 text-center text-sm text-gray-400">
            暂无任务
          </div>
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

/**
 * Mobile Header
 */
function MobileHeader() {
  return (
    <header className="fixed top-0 right-0 left-0 z-50 flex h-14 items-center justify-between border-b border-gray-100 bg-white px-4 lg:hidden">
      <Link href="/" className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
          <div className="h-3.5 w-3.5 rotate-45 transform rounded-sm bg-white" />
        </div>
        <span className="font-semibold text-gray-900">Prism</span>
      </Link>
      <button className="rounded-lg bg-gray-100 p-2 text-sm font-medium text-gray-700">
        登录
      </button>
    </header>
  );
}

/**
 * Welcome Section with Quick Actions
 */
function WelcomeSection() {
  const [greeting, setGreeting] = useState(getGreeting());

  useEffect(() => {
    const interval = setInterval(() => setGreeting(getGreeting()), 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-8 text-center lg:py-12">
      {/* Status Badge */}
      <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1.5">
        <span className="flex h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        <span className="text-xs font-medium text-gray-600">Beta</span>
        <span className="text-xs text-gray-500">启动 Prism Computer</span>
      </div>

      {/* Greeting */}
      <h1 className="mb-2 text-2xl font-semibold text-gray-900 lg:text-3xl">
        你好，<span className="inline-block">👋</span>
      </h1>
      <p className="text-gray-500">{greeting}，准备好创建点什么了吗？</p>
    </section>
  );
}

/**
 * Quick Actions Grid
 */
function QuickActions({
  onActionClick,
}: {
  onActionClick: (action: QuickAction) => void;
}) {
  return (
    <section className="mb-8 px-4 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.id}
              onClick={() => onActionClick(action)}
              className="group flex flex-col items-center gap-2 rounded-2xl border border-gray-100 bg-white p-4 transition-all hover:border-gray-200 hover:shadow-md"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-50 text-gray-600 transition-colors group-hover:bg-gray-100">
                {action.icon}
              </div>
              <span className="text-sm font-medium text-gray-700">
                {action.title}
              </span>
              {action.model && (
                <span className="text-[10px] text-gray-400">
                  {action.model}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * Chat Input Area with Pro Toggle
 */
function ChatInputArea({
  value,
  onChange,
  onSubmit,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  const [mode, setMode] = useState<"pro" | "flash">("pro");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) onSubmit();
    }
  };

  const quickPrompts = ["起草一封专业的邮件回复"];

  return (
    <section className="mb-8 px-4 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
          {/* Quick Prompts */}
          <div className="flex flex-wrap items-center gap-2 px-4 pt-3">
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                onClick={() => onChange(prompt)}
                className="rounded-full bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-100"
              >
                {prompt}
              </button>
            ))}
            <span className="text-xs text-gray-400">TAB</span>
          </div>

          {/* Input */}
          <div className="p-4">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="跟小镜聊..."
              className="max-h-[200px] min-h-[60px] w-full resize-none bg-transparent text-gray-900 placeholder:text-gray-400 focus:outline-none"
              rows={1}
            />
          </div>

          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 pb-4">
            <div className="flex items-center gap-2">
              <button className="rounded-lg p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600">
                <Paperclip className="h-5 w-5" />
              </button>

              {/* Pro Toggle */}
              <button
                onClick={() => setMode(mode === "pro" ? "flash" : "pro")}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
                  mode === "pro"
                    ? "bg-gray-900 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200",
                )}
              >
                <Zap className="h-3 w-3" />
                Pro
              </button>
            </div>

            <button
              onClick={onSubmit}
              disabled={!value.trim()}
              className={cn(
                "flex h-9 w-9 items-center justify-center rounded-full transition-all",
                value.trim()
                  ? "bg-gray-900 text-white hover:bg-gray-800"
                  : "cursor-not-allowed bg-gray-100 text-gray-400",
              )}
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * Promo Card
 */
function PromoCard() {
  return (
    <section className="mb-8 px-4 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6">
          <div className="relative z-10">
            <h3 className="mb-1 text-lg font-semibold text-gray-900">
              探索使用案例
            </h3>
            <p className="text-sm text-gray-500">
              发现你可以构建的一切 — 网站、游戏、数据分析等更多精彩。
            </p>
          </div>
          <div className="absolute top-0 right-0 h-full w-32 bg-gradient-to-l from-gray-50 to-transparent" />
        </div>
      </div>
    </section>
  );
}

/**
 * Mobile Bottom Nav
 */
function MobileBottomNav() {
  const items = [
    {
      icon: <MessageSquare className="h-5 w-5" />,
      label: "对话",
      active: true,
    },
    { icon: <Users className="h-5 w-5" />, label: "Agents" },
    { icon: <Compass className="h-5 w-5" />, label: "探索" },
    { icon: <Settings className="h-5 w-5" />, label: "设置" },
  ];

  return (
    <nav className="fixed right-0 bottom-0 left-0 z-50 border-t border-gray-200 bg-white px-4 py-2 lg:hidden">
      <div className="flex items-center justify-around">
        {items.map((item) => (
          <button
            key={item.label}
            className={cn(
              "flex flex-col items-center gap-0.5 rounded-lg p-2 transition-colors",
              item.active
                ? "text-gray-900"
                : "text-gray-400 hover:text-gray-600",
            )}
          >
            {item.icon}
            <span className="text-[10px] font-medium">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}

// ============================================================================
// Main Dashboard
// ============================================================================

export default function DashboardPage() {
  const [inputValue, setInputValue] = useState("");

  const handleQuickActionClick = useCallback((action: QuickAction) => {
    setInputValue(action.prompt);
  }, []);

  const handleSubmit = useCallback(() => {
    console.log("Submitting:", inputValue);
    setInputValue("");
  }, [inputValue]);

  return (
    <div className="min-h-screen bg-[#F4F5F2] lg:pl-64">
      {/* Mobile Header */}
      <MobileHeader />

      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <main className="flex min-h-screen flex-col pt-14 pb-20 lg:pt-0 lg:pb-0">
        <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center">
          <WelcomeSection />
          <QuickActions onActionClick={handleQuickActionClick} />
          <ChatInputArea
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSubmit}
          />
          <PromoCard />
        </div>
      </main>

      {/* Mobile Bottom Nav */}
      <MobileBottomNav />
    </div>
  );
}
