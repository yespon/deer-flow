"use client";

/**
 * DeerFlow Dashboard Prototype
 *
 * 设计思路:
 * 1. 采用暖米色背景 (#fafaf9) 营造舒适的工作环境
 * 2. 大圆角设计 (rounded-2xl) 带来友好的视觉体验
 * 3. 渐变色彩区分不同功能模块
 * 4. 悬停动画增强交互反馈
 * 5. 响应式布局适配移动端
 *
 * UX 灵感来源于 MuleRun:
 * - 清晰的视觉层次
 * - 快捷操作一键触达
 * - 输入框始终可见，随时可用
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
  MoreHorizontal,
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
} from "lucide-react";
import React, { useState, useEffect, useCallback } from "react";

import { cn } from "@/lib/utils";

// ============================================================================
// Types
// ============================================================================

interface QuickAction {
  id: string;
  title: string;
  icon: React.ReactNode;
  prompt: string;
  gradient: string;
  hoverGradient: string;
  shadowColor: string;
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
  thumbnail?: string;
  createdAt: string;
}

// ============================================================================
// Mock Data
// ============================================================================

const QUICK_ACTIONS: QuickAction[] = [
  {
    id: "generate-image",
    title: "生成图片",
    icon: <Image className="h-6 w-6" />,
    prompt: "帮我生成一张",
    gradient: "from-pink-400 via-rose-400 to-pink-500",
    hoverGradient: "from-pink-500 via-rose-500 to-pink-600",
    shadowColor: "shadow-pink-200",
  },
  {
    id: "create-video",
    title: "创建视频",
    icon: <Video className="h-6 w-6" />,
    prompt: "帮我创建一个视频",
    gradient: "from-rose-400 via-red-400 to-rose-500",
    hoverGradient: "from-rose-500 via-red-500 to-rose-600",
    shadowColor: "shadow-rose-200",
  },
  {
    id: "data-analysis",
    title: "数据分析",
    icon: <BarChart3 className="h-6 w-6" />,
    prompt: "帮我分析这份数据",
    gradient: "from-emerald-400 via-teal-400 to-emerald-500",
    hoverGradient: "from-emerald-500 via-teal-500 to-emerald-600",
    shadowColor: "shadow-emerald-200",
  },
  {
    id: "create-website",
    title: "创建网站",
    icon: <Globe className="h-6 w-6" />,
    prompt: "帮我创建一个网站",
    gradient: "from-blue-400 via-cyan-400 to-blue-500",
    hoverGradient: "from-blue-500 via-cyan-500 to-blue-600",
    shadowColor: "shadow-blue-200",
  },
  {
    id: "document-processing",
    title: "文档处理",
    icon: <FileText className="h-6 w-6" />,
    prompt: "帮我处理这份文档",
    gradient: "from-amber-400 via-orange-400 to-amber-500",
    hoverGradient: "from-amber-500 via-orange-500 to-amber-600",
    shadowColor: "shadow-amber-200",
  },
  {
    id: "web-research",
    title: "网络调研",
    icon: <Search className="h-6 w-6" />,
    prompt: "帮我调研一下",
    gradient: "from-teal-400 via-cyan-400 to-teal-500",
    hoverGradient: "from-teal-500 via-cyan-500 to-teal-600",
    shadowColor: "shadow-teal-200",
  },
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
  {
    id: "5",
    title: "营销方案策划",
    preview: "针对新品发布的社交媒体推广计划...",
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
      return <FileImage className="h-5 w-5 text-purple-500" />;
    case "video":
      return <Video className="h-5 w-5 text-rose-500" />;
    case "document":
      return <FileText className="h-5 w-5 text-blue-500" />;
    case "code":
      return <FileCode className="h-5 w-5 text-emerald-500" />;
    case "spreadsheet":
      return <FileSpreadsheet className="h-5 w-5 text-green-500" />;
    case "audio":
      return <Music className="h-5 w-5 text-amber-500" />;
    default:
      return <FileText className="h-5 w-5 text-gray-500" />;
  }
}

function getDeliverableBgColor(type: Deliverable["type"]) {
  switch (type) {
    case "image":
      return "bg-purple-50";
    case "video":
      return "bg-rose-50";
    case "document":
      return "bg-blue-50";
    case "code":
      return "bg-emerald-50";
    case "spreadsheet":
      return "bg-green-50";
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
 * 顶部导航栏组件
 * - Logo 与品牌标识
 * - 主导航项
 * - 用户头像下拉菜单
 */
function TopNavBar() {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const navItems = [
    { label: "工作台", href: "#", active: true },
    { label: "对话", href: "#" },
    { label: "Agents", href: "#" },
    { label: "探索", href: "#" },
    { label: "设置", href: "#" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-stone-200/60 bg-[#fafaf9]/80 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 shadow-sm">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-semibold tracking-tight text-stone-800">
              DeerFlow
            </span>
          </div>

          {/* Navigation */}
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => (
              <a
                key={item.label}
                href={item.href}
                className={cn(
                  "rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200",
                  item.active
                    ? "bg-stone-900 text-white"
                    : "text-stone-600 hover:bg-stone-200/50 hover:text-stone-900",
                )}
              >
                {item.label}
              </a>
            ))}
          </nav>

          {/* User Menu */}
          <div className="relative">
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 rounded-full p-1.5 transition-colors hover:bg-stone-200/50"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-stone-400 to-stone-600 text-sm font-medium text-white">
                U
              </div>
              <ChevronDown className="h-4 w-4 text-stone-500" />
            </button>

            {isUserMenuOpen && (
              <div className="absolute right-0 z-50 mt-2 w-48 rounded-xl border border-stone-200 bg-white py-1 shadow-lg">
                <div className="border-b border-stone-100 px-4 py-2">
                  <p className="text-sm font-medium text-stone-900">用户名称</p>
                  <p className="text-xs text-stone-500">user@example.com</p>
                </div>
                <a
                  href="#"
                  className="block px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
                >
                  个人设置
                </a>
                <a
                  href="#"
                  className="block px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
                >
                  使用统计
                </a>
                <a
                  href="#"
                  className="block px-4 py-2 text-sm text-stone-700 hover:bg-stone-50"
                >
                  帮助中心
                </a>
                <div className="mt-1 border-t border-stone-100">
                  <a
                    href="#"
                    className="block px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    退出登录
                  </a>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

/**
 * 欢迎区域组件
 * - 时间感知问候语
 * - 动态副标题
 */
function WelcomeSection() {
  const [greeting, setGreeting] = useState(getGreeting());

  useEffect(() => {
    // Update greeting every minute
    const interval = setInterval(() => {
      setGreeting(getGreeting());
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-10 text-center md:py-14">
      <h1 className="mb-3 text-3xl font-bold text-stone-800 md:text-4xl">
        {greeting}，朋友 <span className="animate-wave inline-block">👋</span>
      </h1>
      <p className="text-lg text-stone-500">今天有什么可以帮你的吗？</p>
    </section>
  );
}

/**
 * 快捷操作卡片组件
 * - 6个彩色渐变卡片
 * - 悬停上浮动画
 * - 点击填充提示词
 */
function QuickActionCard({
  action,
  onClick,
}: {
  action: QuickAction;
  onClick: (prompt: string) => void;
}) {
  return (
    <button
      onClick={() => onClick(action.prompt)}
      className={cn(
        "group relative flex flex-col items-center justify-center gap-3",
        "rounded-2xl bg-gradient-to-br p-6 text-white",
        "transition-all duration-300 ease-out",
        "hover:-translate-y-1 hover:shadow-xl",
        "focus:ring-2 focus:ring-stone-400 focus:ring-offset-2 focus:outline-none",
        action.gradient,
        action.shadowColor,
      )}
    >
      {/* Hover overlay for gradient change */}
      <div
        className={cn(
          "absolute inset-0 rounded-2xl bg-gradient-to-br opacity-0",
          "transition-opacity duration-300",
          "group-hover:opacity-100",
          action.hoverGradient,
        )}
      />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center gap-3">
        <div className="rounded-xl bg-white/20 p-3 backdrop-blur-sm">
          {action.icon}
        </div>
        <span className="text-sm font-medium">{action.title}</span>
      </div>
    </button>
  );
}

/**
 * 快捷操作区域
 */
function QuickActions({
  onActionClick,
}: {
  onActionClick: (prompt: string) => void;
}) {
  return (
    <section className="mb-8 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {QUICK_ACTIONS.map((action) => (
            <QuickActionCard
              key={action.id}
              action={action}
              onClick={onActionClick}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

/**
 * 对话输入区组件
 * - 快捷标签
 * - 文本输入框
 * - Pro/Flash 模式切换
 * - 模型选择
 * - 附件按钮
 * - 发送按钮
 */
function ChatInputArea({
  value,
  onChange,
  onSubmit,
  onQuickActionClick,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onQuickActionClick: (prompt: string) => void;
}) {
  const [mode, setMode] = useState<"pro" | "flash">("pro");
  const [isModelSelectOpen, setIsModelSelectOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState("GPT-4");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200,
      )}px`;
    }
  }, [value]);

  const handleSubmit = useCallback(() => {
    if (value.trim()) {
      onSubmit();
    }
  }, [value, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const quickTags = ["数据分析", "创建网站", "生成文案", "代码优化"];

  const models = ["GPT-4", "Claude 3.5", "Gemini Pro", "Llama 3"];

  return (
    <section className="mb-10 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <div
          className={cn(
            "rounded-2xl border border-stone-200 bg-white shadow-sm",
            "transition-all duration-300",
            isFocused && "border-stone-300 shadow-md ring-2 ring-stone-900/5",
          )}
        >
          {/* Quick Tags - show when focused or has content */}
          {(isFocused || value) && (
            <div className="animate-fade-in flex flex-wrap items-center gap-2 px-4 pt-3">
              <span className="text-xs text-stone-400">快捷:</span>
              {quickTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => onQuickActionClick(tag)}
                  className="rounded-full bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-200"
                >
                  {tag}
                </button>
              ))}
              <button className="px-2.5 py-1 text-xs font-medium text-stone-400 transition-colors hover:text-stone-600">
                更多...
              </button>
            </div>
          )}

          {/* Input Area */}
          <div className="p-4">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题..."
              className="max-h-[200px] min-h-[60px] w-full resize-none bg-transparent text-stone-800 placeholder:text-stone-400 focus:outline-none"
              rows={1}
            />
          </div>

          {/* Toolbar */}
          <div className="flex items-center justify-between px-4 pb-4">
            {/* Left: Attach, Mode, Model */}
            <div className="flex items-center gap-2">
              {/* Attach Button */}
              <button className="rounded-lg p-2 text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700">
                <Paperclip className="h-5 w-5" />
              </button>

              {/* Mode Toggle */}
              <div className="flex items-center rounded-lg bg-stone-100 p-0.5">
                <button
                  onClick={() => setMode("pro")}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                    mode === "pro"
                      ? "bg-stone-900 text-white shadow-sm"
                      : "text-stone-600 hover:text-stone-800",
                  )}
                >
                  <span className="flex items-center gap-1">
                    <Zap className="h-3 w-3" />
                    Pro
                  </span>
                </button>
                <button
                  onClick={() => setMode("flash")}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-all",
                    mode === "flash"
                      ? "bg-stone-900 text-white shadow-sm"
                      : "text-stone-600 hover:text-stone-800",
                  )}
                >
                  <span className="flex items-center gap-1">
                    <Sparkles className="h-3 w-3" />
                    Flash
                  </span>
                </button>
              </div>

              {/* Model Select */}
              <div className="relative">
                <button
                  onClick={() => setIsModelSelectOpen(!isModelSelectOpen)}
                  className="flex items-center gap-1 rounded-lg bg-stone-100 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-200"
                >
                  {selectedModel}
                  <ChevronDown className="h-3 w-3" />
                </button>

                {isModelSelectOpen && (
                  <div className="absolute top-full left-0 z-50 mt-1 w-36 rounded-lg border border-stone-200 bg-white py-1 shadow-lg">
                    {models.map((model) => (
                      <button
                        key={model}
                        onClick={() => {
                          setSelectedModel(model);
                          setIsModelSelectOpen(false);
                        }}
                        className={cn(
                          "block w-full px-3 py-2 text-left text-xs",
                          selectedModel === model
                            ? "bg-stone-100 font-medium text-stone-900"
                            : "text-stone-600 hover:bg-stone-50",
                        )}
                      >
                        {model}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right: Send Button */}
            <button
              onClick={handleSubmit}
              disabled={!value.trim()}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-full",
                "bg-gradient-to-r from-stone-800 to-stone-900 text-white",
                "transition-all duration-200",
                "hover:scale-105 hover:from-stone-700 hover:to-stone-800 hover:shadow-lg",
                "disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100 disabled:hover:shadow-none",
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
 * 最近对话列表组件
 */
function RecentConversations() {
  return (
    <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
        <h3 className="flex items-center gap-2 font-semibold text-stone-800">
          <MessageSquare className="h-4 w-4 text-stone-500" />
          最近对话
        </h3>
        <button className="text-xs text-stone-500 transition-colors hover:text-stone-800">
          查看全部
        </button>
      </div>
      <div className="divide-y divide-stone-100">
        {RECENT_CONVERSATIONS.map((conversation) => (
          <a
            key={conversation.id}
            href="#"
            className="group block px-5 py-4 transition-colors hover:bg-stone-50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="truncate font-medium text-stone-800 group-hover:text-stone-900">
                    {conversation.title}
                  </h4>
                  {conversation.unread && (
                    <span className="h-2 w-2 flex-shrink-0 rounded-full bg-amber-400" />
                  )}
                </div>
                <p className="mt-0.5 truncate text-sm text-stone-500">
                  {conversation.preview}
                </p>
              </div>
              <span className="flex-shrink-0 text-xs text-stone-400">
                {conversation.timestamp}
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

/**
 * 最新交付物网格组件
 */
function RecentDeliverables() {
  return (
    <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
        <h3 className="flex items-center gap-2 font-semibold text-stone-800">
          <FileText className="h-4 w-4 text-stone-500" />
          最新交付物
        </h3>
        <button className="text-xs text-stone-500 transition-colors hover:text-stone-800">
          查看全部
        </button>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {DELIVERABLES.map((deliverable) => (
            <a
              key={deliverable.id}
              href="#"
              className="group rounded-xl border border-stone-100 p-3 transition-all hover:border-stone-200 hover:bg-stone-50"
            >
              <div
                className={cn(
                  "mb-2 flex h-10 w-10 items-center justify-center rounded-lg",
                  getDeliverableBgColor(deliverable.type),
                )}
              >
                {getDeliverableIcon(deliverable.type)}
              </div>
              <p className="truncate text-sm font-medium text-stone-800 group-hover:text-stone-900">
                {deliverable.name}
              </p>
              <p className="mt-0.5 text-xs text-stone-400">
                {deliverable.createdAt}
              </p>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * 最近活动区域（两列布局）
 */
function RecentActivity() {
  return (
    <section className="px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <RecentConversations />
          <RecentDeliverables />
        </div>
      </div>
    </section>
  );
}

/**
 * 底部快捷入口
 * 移动端显示的底部导航
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
    <nav className="fixed right-0 bottom-0 left-0 z-50 border-t border-stone-200 bg-white px-4 py-2 md:hidden">
      <div className="flex items-center justify-around">
        {items.map((item) => (
          <button
            key={item.label}
            className={cn(
              "flex flex-col items-center gap-0.5 rounded-lg p-2 transition-colors",
              item.active
                ? "text-stone-900"
                : "text-stone-400 hover:text-stone-600",
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
// Main Dashboard Component
// ============================================================================

export default function DeerFlowDashboard() {
  const [inputValue, setInputValue] = useState("");

  const handleQuickActionClick = useCallback((prompt: string) => {
    setInputValue((prev) => {
      // If there's existing content, add a space
      const separator = prev && !prev.endsWith(" ") ? " " : "";
      return prev + separator + prompt;
    });
  }, []);

  const handleSubmit = useCallback(() => {
    // Mock submit - in real app this would send to API
    console.log("Submitting:", inputValue);
    setInputValue("");
  }, [inputValue]);

  return (
    <div className="min-h-screen bg-[#fafaf9] pb-20 md:pb-0">
      {/* Top Navigation */}
      <TopNavBar />

      {/* Main Content */}
      <main className="pt-4">
        {/* Welcome Section */}
        <WelcomeSection />

        {/* Quick Actions */}
        <QuickActions onActionClick={handleQuickActionClick} />

        {/* Chat Input Area */}
        <ChatInputArea
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          onQuickActionClick={handleQuickActionClick}
        />

        {/* Recent Activity */}
        <RecentActivity />
      </main>

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav />

      {/* Footer */}
      <footer className="mt-16 hidden border-t border-stone-200 py-8 md:block">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between text-sm text-stone-400">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              <span>DeerFlow AI Agent Platform</span>
            </div>
            <div className="flex items-center gap-4">
              <a href="#" className="transition-colors hover:text-stone-600">
                文档
              </a>
              <a href="#" className="transition-colors hover:text-stone-600">
                隐私政策
              </a>
              <a href="#" className="transition-colors hover:text-stone-600">
                使用条款
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
