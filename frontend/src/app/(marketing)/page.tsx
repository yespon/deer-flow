"use client";

import {
  ChevronDown,
  Play,
  ArrowRight,
  Bot,
  FileText,
  Video,
  Globe,
  BarChart3,
  Mail,
  Terminal,
  Cpu,
  Clock,
  Zap,
  Check,
  X,
  MessageSquare,
  Quote,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { cn } from "@/lib/utils";

// ============================================================================
// Navigation
// ============================================================================
function Navbar() {
  return (
    <header className="fixed top-0 right-0 left-0 z-50 border-b border-gray-200/50 bg-[#F4F5F2]/80 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
              <div className="h-4 w-4 rotate-45 transform rounded-sm bg-white" />
            </div>
            <span className="text-xl font-semibold text-gray-900">Prism</span>
          </Link>

          {/* Nav Links */}
          <nav className="hidden items-center gap-8 md:flex">
            <Link
              href="#features"
              className="text-sm text-gray-600 transition-colors hover:text-gray-900"
            >
              功能
            </Link>
            <Link
              href="#use-cases"
              className="text-sm text-gray-600 transition-colors hover:text-gray-900"
            >
              用例
            </Link>
            <Link
              href="#pricing"
              className="text-sm text-gray-600 transition-colors hover:text-gray-900"
            >
              定价
            </Link>
            <Link
              href="#blog"
              className="text-sm text-gray-600 transition-colors hover:text-gray-900"
            >
              博客
            </Link>
          </nav>

          {/* CTA */}
          <div className="flex items-center gap-4">
            <Link
              href="/login"
              className="hidden items-center gap-2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-gray-800 sm:inline-flex"
            >
              登录
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}

// ============================================================================
// Hero Section
// ============================================================================
const USE_CASES = [
  {
    id: "1",
    title: "生成品牌PPT",
    icon: <FileText className="h-5 w-5" />,
    color: "bg-violet-100 text-violet-600",
  },
  {
    id: "2",
    title: "分析美股行情",
    icon: <BarChart3 className="h-5 w-5" />,
    color: "bg-fuchsia-100 text-fuchsia-600",
  },
  {
    id: "3",
    title: "视频创作",
    icon: <Video className="h-5 w-5" />,
    color: "bg-amber-100 text-amber-600",
  },
  {
    id: "4",
    title: "浏览器研究",
    icon: <Globe className="h-5 w-5" />,
    color: "bg-blue-100 text-blue-600",
  },
  {
    id: "5",
    title: "新闻报告生成",
    icon: <Mail className="h-5 w-5" />,
    color: "bg-emerald-100 text-emerald-600",
  },
  {
    id: "6",
    title: "Word文档编写",
    icon: <FileText className="h-5 w-5" />,
    color: "bg-rose-100 text-rose-600",
  },
];

function HeroSection() {
  return (
    <section className="overflow-hidden pt-32 pb-16 lg:pt-40 lg:pb-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Headline */}
        <div className="mx-auto mb-12 max-w-4xl text-center">
          <h1 className="mb-6 text-4xl leading-tight font-semibold text-gray-900 sm:text-5xl lg:text-6xl">
            你的全能 AI
            <span className="block bg-gradient-to-r from-violet-600 via-fuchsia-600 to-amber-500 bg-clip-text text-transparent">
              办公平台
            </span>
          </h1>
          <p className="mx-auto mb-8 max-w-2xl text-lg text-gray-600">
            7×24小时在线的 AI Agent，主动执行复杂任务，不只是聊天
          </p>
          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/login"
              className="group inline-flex items-center gap-2 rounded-xl bg-gray-900 px-6 py-3 font-medium text-white transition-all hover:scale-105 hover:bg-gray-800"
            >
              <Play className="h-4 w-4" />
              启动 Agent
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Link>
            <Link
              href="#features"
              className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-6 py-3 font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              了解更多
            </Link>
          </div>
        </div>

        {/* 3D Computer Illustration Placeholder */}
        <div className="relative mx-auto mb-16 max-w-4xl">
          <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl">
            {/* Window Header */}
            <div className="flex items-center gap-2 border-b border-gray-200 bg-gray-50 px-4 py-3">
              <div className="h-3 w-3 rounded-full bg-rose-400" />
              <div className="h-3 w-3 rounded-full bg-amber-400" />
              <div className="h-3 w-3 rounded-full bg-emerald-400" />
              <div className="flex-1 text-center text-xs text-gray-400">
                Prism Agent Workspace
              </div>
            </div>
            {/* Content */}
            <div className="p-8 lg:p-12">
              <div className="grid grid-cols-1 items-center gap-8 lg:grid-cols-2">
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Clock className="h-4 w-4" />
                    <span>正在执行任务...</span>
                  </div>
                  <div className="space-y-2">
                    <div className="h-2 w-3/4 rounded-full bg-gray-100" />
                    <div className="h-2 w-1/2 rounded-full bg-gray-100" />
                    <div className="h-2 w-5/6 rounded-full bg-gray-100" />
                  </div>
                  <div className="flex gap-2">
                    <span className="rounded bg-violet-100 px-2 py-1 text-xs text-violet-700">
                      SysMon
                    </span>
                    <span className="rounded bg-fuchsia-100 px-2 py-1 text-xs text-fuchsia-700">
                      Worker
                    </span>
                    <span className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-700">
                      DBSync
                    </span>
                  </div>
                </div>
                <div className="relative">
                  <div className="flex aspect-square items-center justify-center rounded-xl bg-gradient-to-br from-gray-50 to-gray-100">
                    <div className="flex h-32 w-32 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/20 via-fuchsia-500/20 to-amber-500/20">
                      <Bot className="h-16 w-16 text-gray-400" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          {/* Floating Elements */}
          <div className="absolute -top-4 -right-4 h-20 w-20 rounded-full bg-violet-500/10 blur-2xl" />
          <div className="absolute -bottom-4 -left-4 h-32 w-32 rounded-full bg-fuchsia-500/10 blur-2xl" />
        </div>

        {/* Use Case Cards */}
        <div className="relative">
          <div className="scrollbar-hide flex snap-x gap-4 overflow-x-auto pb-4">
            {USE_CASES.map((useCase) => (
              <div
                key={useCase.id}
                className="w-48 flex-shrink-0 cursor-pointer snap-start rounded-xl border border-gray-200 bg-white p-4 transition-shadow hover:shadow-lg"
              >
                <div
                  className={cn(
                    "mb-3 flex h-10 w-10 items-center justify-center rounded-lg",
                    useCase.color,
                  )}
                >
                  {useCase.icon}
                </div>
                <h3 className="text-sm font-medium text-gray-900">
                  {useCase.title}
                </h3>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// Core Features Section
// ============================================================================
const FEATURES = [
  {
    id: "always-on",
    title: "7×24小时在线",
    subtitle: "专属的 AI 工作站",
    description:
      "不同于传统聊天工具——关闭标签页就中断工作。Prism 在云端持续运行，即使您离线也能完成任务。",
    icon: <Clock className="h-5 w-5" />,
    visual: (
      <div className="rounded-lg bg-gray-900 p-4 font-mono text-xs">
        <div className="mb-3 flex items-center gap-2 text-gray-400">
          <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          <span>08:00 Active</span>
        </div>
        <div className="space-y-1 text-gray-300">
          <div className="flex items-center gap-2">
            <span className="text-violet-400">SysMon</span>
            <span className="text-gray-500">|</span>
            <span>运行正常</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-fuchsia-400">Worker</span>
            <span className="text-gray-500">|</span>
            <span>处理中...</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-amber-400">DBSync</span>
            <span className="text-gray-500">|</span>
            <span>已同步</span>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "self-evolving",
    title: "自我进化",
    subtitle: "集体智慧越用越聪明",
    description:
      "每一次工作流执行都让 Prism 变得更智能。从企业知识库中学习，不断优化执行策略。",
    icon: <Cpu className="h-5 w-5" />,
    visual: (
      <div className="rounded-lg bg-gray-900 p-4 font-mono text-xs">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-gray-400">学习进度</span>
          <span className="rounded bg-violet-500/20 px-2 py-0.5 text-[10px] text-violet-400">
            v2.1 Pro
          </span>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-gray-300">
            <span>知识库</span>
            <span className="text-emerald-400">98%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-gray-800">
            <div className="h-full w-[98%] rounded-full bg-emerald-500" />
          </div>
          <div className="flex items-center justify-between text-gray-300">
            <span>执行效率</span>
            <span className="text-violet-400">+45%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-gray-800">
            <div className="h-full w-[85%] rounded-full bg-violet-500" />
          </div>
        </div>
      </div>
    ),
  },
  {
    id: "proactive",
    title: "主动执行",
    subtitle: "监控、预警、执行一体化",
    description:
      "设置监控规则后，Prism 会主动检测异常、发送预警并执行预设动作，无需人工干预。",
    icon: <Zap className="h-5 w-5" />,
    visual: (
      <div className="rounded-lg bg-gray-900 p-4 font-mono text-xs">
        <div className="mb-3 flex items-center gap-2 text-gray-400">
          <Terminal className="h-3 w-3" />
          <span>Scheduler</span>
        </div>
        <div className="space-y-2 text-gray-300">
          <div className="flex items-center gap-2">
            <span className="w-8 text-gray-500">09:00</span>
            <span className="text-gray-500 line-through">数据备份</span>
            <Check className="ml-auto h-3 w-3 text-emerald-500" />
          </div>
          <div className="flex items-center gap-2">
            <span className="w-8 text-gray-500">10:30</span>
            <span>竞品价格监控</span>
            <div className="ml-auto h-2 w-2 animate-pulse rounded-full bg-amber-500" />
          </div>
          <div className="flex items-center gap-2">
            <span className="w-8 text-gray-500">14:00</span>
            <span>周报生成</span>
            <span className="ml-auto text-gray-500">待执行</span>
          </div>
        </div>
      </div>
    ),
  },
];

function FeaturesSection() {
  return (
    <section id="features" className="bg-white py-20 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="mb-16 text-center">
          <span className="mb-4 inline-flex items-center gap-2 rounded-full bg-violet-100 px-3 py-1 text-xs font-medium text-violet-700">
            <Zap className="h-3 w-3" />
            端到端自动化
          </span>
          <h2 className="mb-4 text-3xl font-semibold text-gray-900 lg:text-4xl">
            7×24小时在线的 AI Agent
            <br />
            自动化你的工作流
          </h2>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <div
              key={feature.id}
              className="group rounded-2xl bg-gray-50 p-6 transition-colors hover:bg-gray-100 lg:p-8"
            >
              <div className="mb-6">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-white text-violet-600 shadow-sm">
                  {feature.icon}
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">
                  {feature.title}
                </h3>
                <p className="mb-3 font-medium text-violet-600">
                  {feature.subtitle}
                </p>
                <p className="text-sm text-gray-600">{feature.description}</p>
              </div>
              <div className="mb-6">{feature.visual}</div>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 text-sm font-medium text-gray-900 transition-colors hover:text-violet-600"
              >
                免费试用
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// Comparison Section
// ============================================================================
const COMPARISON_ROWS = [
  { label: "功能定位", chatbot: "回答你的问题", prism: "完成整个任务流程" },
  {
    label: "工作方式",
    chatbot: "在聊天窗口生成文字",
    prism: "使用专属电脑——打开工具、执行步骤、交付结果",
  },
  {
    label: "可用性",
    chatbot: "仅在对话时活跃",
    prism: "7×24小时在线，持续运行",
  },
  {
    label: "学习能力",
    chatbot: "通用训练数据",
    prism: "从真实业务工作流中持续学习",
  },
  { label: "下班后", chatbot: "什么都不发生", prism: "主动监控、预警并执行" },
  {
    label: "设置方式",
    chatbot: "每次复制粘贴提示词",
    prism: "一次描述，自动运行",
  },
  {
    label: "你的工作量",
    chatbot: "其他一切仍需手动完成",
    prism: "仅需审核、批准、决策",
  },
];

function ComparisonSection() {
  return (
    <section className="bg-[#F4F5F2] py-20 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="mb-16 text-center">
          <h2 className="mb-4 text-3xl font-semibold text-gray-900 lg:text-4xl">
            不是聊天机器人，不只是提示词工具
          </h2>
          <p className="text-lg text-gray-600">而是真正的 AI 劳动力</p>
        </div>

        {/* Comparison Table */}
        <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xl">
          {/* Window Header */}
          <div className="flex items-center gap-2 border-b border-gray-200 bg-gray-50 px-4 py-3">
            <div className="h-3 w-3 rounded-full bg-rose-400" />
            <div className="h-3 w-3 rounded-full bg-amber-400" />
            <div className="h-3 w-3 rounded-full bg-emerald-400" />
          </div>

          {/* Table Header */}
          <div className="grid grid-cols-3 gap-4 border-b border-gray-200 bg-gray-50/50 p-6">
            <div className="text-sm font-medium text-gray-500">对比维度</div>
            <div className="flex items-center gap-2 text-sm font-medium text-gray-500">
              <Bot className="h-4 w-4" />
              聊天机器人 (ChatGPT, Copilot)
            </div>
            <div className="flex items-center gap-2 text-sm font-medium text-violet-600">
              <div className="flex h-4 w-4 items-center justify-center rounded bg-gradient-to-br from-violet-500 to-fuchsia-500">
                <div className="h-2 w-2 rotate-45 transform rounded-sm bg-white" />
              </div>
              Prism
            </div>
          </div>

          {/* Table Body */}
          <div className="divide-y divide-gray-100">
            {COMPARISON_ROWS.map((row, index) => (
              <div
                key={index}
                className="grid grid-cols-3 gap-4 p-6 transition-colors hover:bg-gray-50/50"
              >
                <div className="text-sm font-medium text-gray-700">
                  {row.label}
                </div>
                <div className="flex items-start gap-2 text-sm text-gray-500">
                  <X className="mt-0.5 h-4 w-4 flex-shrink-0 text-rose-400" />
                  {row.chatbot}
                </div>
                <div className="flex items-start gap-2 text-sm text-gray-900">
                  <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-500" />
                  {row.prism}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// Testimonials Section
// ============================================================================
const TESTIMONIALS = [
  {
    id: "1",
    name: "陈伟",
    role: "独立开发者",
    avatar: "C",
    color: "bg-violet-500",
    content:
      "太震撼了！Prism 让我可以专注于创造性工作，把繁琐的重复任务都交给它处理。",
  },
  {
    id: "2",
    name: "Tyler Brooks",
    role: "创业公司创始人",
    avatar: "T",
    color: "bg-fuchsia-500",
    content:
      "试用了 Prism 后真的被惊艳到了。它不只是回答问题，而是真正完成了整个市场调研报告。",
  },
  {
    id: "3",
    name: "李晓明",
    role: "产品经理",
    avatar: "L",
    color: "bg-amber-500",
    content:
      "昨晚忙到凌晨2点，因为 Prism 帮我整理了三个月的用户数据，效率提升太明显了。",
  },
  {
    id: "4",
    name: "王芳",
    role: "市场总监",
    avatar: "W",
    color: "bg-emerald-500",
    content:
      "这工具简直太实用了！从竞品分析到营销文案，Prism 都是我们团队的得力助手。",
  },
  {
    id: "5",
    name: "Kenji Mori",
    role: "软件工程师",
    avatar: "K",
    color: "bg-blue-500",
    content: "它太聪明了！不仅能力强，而且学习速度惊人，每次使用都比上次更好。",
  },
  {
    id: "6",
    name: "张晓燕",
    role: "数据分析师",
    avatar: "Z",
    color: "bg-rose-500",
    content:
      "难以置信——每个输出都是立即可用的。以前需要一天的数据报告，现在半小时搞定。",
  },
];

function TestimonialsSection() {
  return (
    <section className="bg-white py-20 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="mb-16 text-center">
          <h2 className="mb-4 text-3xl font-semibold text-gray-900 lg:text-4xl">
            听听用户怎么说
          </h2>
        </div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {TESTIMONIALS.map((testimonial) => (
            <div
              key={testimonial.id}
              className="rounded-2xl bg-gray-50 p-6 transition-shadow hover:shadow-lg"
            >
              <Quote className="mb-4 h-8 w-8 text-gray-200" />
              <p className="mb-6 leading-relaxed text-gray-700">
                {testimonial.content}
              </p>
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full font-medium text-white",
                    testimonial.color,
                  )}
                >
                  {testimonial.avatar}
                </div>
                <div>
                  <p className="font-medium text-gray-900">
                    {testimonial.name}
                  </p>
                  <p className="text-sm text-gray-500">{testimonial.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// FAQ Section
// ============================================================================
const FAQS = [
  {
    question: "什么是 AI Agent，与 ChatGPT 有什么不同？",
    answer:
      "AI Agent 不仅能回答问题，还能自主执行完整任务。与 ChatGPT 等聊天机器人不同，Prism 可以在云端持续运行，主动监控、执行工作流，并交付实际成果。",
  },
  {
    question: "Prism 可以自动化哪些类型的任务？",
    answer:
      "Prism 适用于需要多步骤执行的复杂任务，如数据分析、报告生成、市场调研、内容创作、竞品监控、代码开发等。它可以操作浏览器、使用办公软件、处理数据。",
  },
  {
    question: "7×24小时在线是如何工作的？",
    answer:
      "Prism 运行在云端专属环境中，不需要您的电脑保持开机。设置任务后，即使您离线，它也会持续运行并在完成时通知您。",
  },
  {
    question: "自我进化功能如何工作？我的数据安全吗？",
    answer:
      "Prism 从您授权的数据和工作流模式中学习，不断优化执行效率。所有数据都经过加密存储，企业版支持私有化部署，确保数据完全掌控在您手中。",
  },
  {
    question: "AI 会犯错吗？如果出现问题怎么办？",
    answer:
      "任何 AI 都可能犯错，因此 Prism 设置了多层审核机制：关键操作需要确认、执行过程可审计、支持随时暂停和回滚。您可以设置置信度阈值，低于阈值时自动暂停等待人工确认。",
  },
  {
    question: "使用 Prism 需要技术背景吗？",
    answer:
      "完全不需要。Prism 采用自然语言交互，您只需描述想要完成的任务，它会自动规划执行步骤。当然，技术人员可以通过 API 和脚本进行更深度的定制。",
  },
  {
    question: "Prism 与 Zapier 或 Make 有什么区别？",
    answer:
      "Zapier 和 Make 是规则型自动化工具，需要预先定义触发器和动作。Prism 是智能型 Agent，能理解上下文、处理复杂决策、适应变化，无需为每种情况硬编码规则。",
  },
];

function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="bg-[#F4F5F2] py-20 lg:py-32">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="mb-16 text-center">
          <h2 className="mb-4 text-3xl font-semibold text-gray-900 lg:text-4xl">
            常见问题
          </h2>
        </div>

        {/* FAQ List */}
        <div className="space-y-4">
          {FAQS.map((faq, index) => (
            <div
              key={index}
              className="overflow-hidden rounded-xl border border-gray-200 bg-white"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="flex w-full items-center justify-between p-6 text-left transition-colors hover:bg-gray-50"
              >
                <span className="font-medium text-gray-900">
                  {faq.question}
                </span>
                <ChevronDown
                  className={cn(
                    "h-5 w-5 text-gray-400 transition-transform",
                    openIndex === index && "rotate-180",
                  )}
                />
              </button>
              {openIndex === index && (
                <div className="px-6 pb-6">
                  <p className="leading-relaxed text-gray-600">{faq.answer}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// CTA Section
// ============================================================================
function CTASection() {
  return (
    <section className="bg-gray-900 py-20 lg:py-32">
      <div className="mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <h2 className="mb-6 text-3xl font-semibold text-white lg:text-4xl">
          准备好让 AI 为你工作了吗？
        </h2>
        <p className="mx-auto mb-8 max-w-2xl text-lg text-gray-400">
          7×24小时在线的 AI Agent，主动执行复杂任务，不只是聊天
        </p>
        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-xl bg-white px-8 py-4 font-medium text-gray-900 transition-colors hover:bg-gray-100"
          >
            免费开始使用
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="#features"
            className="inline-flex items-center gap-2 rounded-xl bg-gray-800 px-8 py-4 font-medium text-white transition-colors hover:bg-gray-700"
          >
            了解更多
          </Link>
        </div>
      </div>
    </section>
  );
}

// ============================================================================
// Footer
// ============================================================================
function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-[#F4F5F2] py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-12 grid grid-cols-2 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link href="/" className="mb-4 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
                <div className="h-4 w-4 rotate-45 transform rounded-sm bg-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">Prism</span>
            </Link>
            <p className="text-sm text-gray-500">
              你的个人 AI，7×24小时在线，主动为你工作
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="mb-4 font-medium text-gray-900">产品</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>
                <Link href="#features" className="hover:text-gray-900">
                  功能
                </Link>
              </li>
              <li>
                <Link href="#pricing" className="hover:text-gray-900">
                  定价
                </Link>
              </li>
              <li>
                <Link href="#use-cases" className="hover:text-gray-900">
                  用例
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-medium text-gray-900">公司</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>
                <Link href="#blog" className="hover:text-gray-900">
                  博客
                </Link>
              </li>
              <li>
                <Link href="#" className="hover:text-gray-900">
                  关于我们
                </Link>
              </li>
              <li>
                <Link href="#" className="hover:text-gray-900">
                  联系我们
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-medium text-gray-900">法律</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>
                <Link href="#" className="hover:text-gray-900">
                  服务条款
                </Link>
              </li>
              <li>
                <Link href="#" className="hover:text-gray-900">
                  隐私政策
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="flex flex-col items-center justify-between border-t border-gray-200 pt-8 md:flex-row">
          <p className="text-sm text-gray-500">
            © 2026 Prism. All rights reserved.
          </p>
          <div className="mt-4 flex items-center gap-4 md:mt-0">
            <Link
              href="#"
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Discord
            </Link>
            <Link
              href="#"
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Twitter
            </Link>
            <Link
              href="#"
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              LinkedIn
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}

// ============================================================================
// Main Page
// ============================================================================
export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#F4F5F2]">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <ComparisonSection />
      <TestimonialsSection />
      <FAQSection />
      <CTASection />
      <Footer />
    </main>
  );
}
