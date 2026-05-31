"use client";

import {
  Image,
  Video,
  BarChart3,
  Globe,
  FileText,
  Sparkles,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo } from "react";

import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

let waved = false;

// ============================================================================
// Quick Actions Data
// ============================================================================
const QUICK_ACTIONS = [
  {
    id: "image",
    title: "生成图片",
    icon: Image,
    prompt: "帮我生成一张",
    color: "bg-violet-50 text-violet-600",
  },
  {
    id: "video",
    title: "创建视频",
    icon: Video,
    prompt: "帮我创建一个视频",
    color: "bg-fuchsia-50 text-fuchsia-600",
  },
  {
    id: "analysis",
    title: "数据分析",
    icon: BarChart3,
    prompt: "帮我分析这份数据",
    color: "bg-amber-50 text-amber-600",
  },
  {
    id: "website",
    title: "创建网站",
    icon: Globe,
    prompt: "帮我创建一个网站",
    color: "bg-blue-50 text-blue-600",
  },
  {
    id: "document",
    title: "生成文档",
    icon: FileText,
    prompt: "帮我生成一份文档",
    color: "bg-emerald-50 text-emerald-600",
  },
  {
    id: "creative",
    title: "创意灵感",
    icon: Sparkles,
    prompt: "给我一些创意灵感",
    color: "bg-rose-50 text-rose-600",
  },
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

// ============================================================================
// Welcome Component
// ============================================================================
export function Welcome({
  className,
  mode,
  onActionClick,
}: {
  className?: string;
  mode?: "ultra" | "pro" | "thinking" | "flash";
  onActionClick?: (prompt: string) => void;
}) {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const isUltra = useMemo(() => mode === "ultra", [mode]);
  const greeting = getGreeting();

  useEffect(() => {
    waved = true;
  }, []);

  if (searchParams.get("mode") === "skill") {
    return (
      <div
        className={cn(
          "mx-auto flex w-full flex-col items-center justify-center gap-2 px-8 py-4 text-center",
          className,
        )}
      >
        <div className="text-2xl font-bold">
          {`✨ ${t.welcome.createYourOwnSkill} ✨`}
        </div>
        <div className="text-muted-foreground text-sm">
          {t.welcome.createYourOwnSkillDescription.includes("\n") ? (
            <pre className="font-sans whitespace-pre">
              {t.welcome.createYourOwnSkillDescription}
            </pre>
          ) : (
            <p>{t.welcome.createYourOwnSkillDescription}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-8 text-center lg:py-12",
        className,
      )}
    >
      {/* Status Badge */}
      <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1.5">
        <span className="flex h-2 w-2 animate-pulse rounded-full bg-amber-500" />
        <span className="text-xs font-medium text-gray-600">Beta</span>
        <span className="text-xs text-gray-500">启动 Prism Agent</span>
      </div>

      {/* Greeting */}
      <h1 className="mb-2 text-2xl font-semibold text-gray-900 lg:text-3xl">
        {greeting}，
        <span className={cn("inline-block", !waved ? "animate-wave" : "")}>
          {isUltra ? "🚀" : "👋"}
        </span>
      </h1>
      <p className="mb-8 text-gray-500">准备好创建点什么了吗？</p>

      {/* Quick Actions */}
      <div className="grid w-full max-w-3xl grid-cols-3 gap-3 px-4 sm:grid-cols-6">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.id}
            onClick={() => onActionClick?.(action.prompt)}
            className="group flex flex-col items-center gap-2 rounded-2xl border border-gray-100 bg-white p-4 transition-all hover:border-gray-200 hover:shadow-md"
          >
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl transition-colors",
                action.color,
              )}
            >
              <action.icon className="h-5 w-5" />
            </div>
            <span className="text-sm font-medium text-gray-700">
              {action.title}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
