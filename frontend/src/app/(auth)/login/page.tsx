"use client";

import { ArrowRight, Mail, Lock, Building2, User, Shield } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { cn } from "@/lib/utils";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [activeTab, setActiveTab] = useState<"code" | "password">("code");
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const sendCode = () => {
    if (!email) return;
    setCountdown(60);
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/login/local", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        credentials: "include",
        body: new URLSearchParams({
          username: email,
          password: password,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.needs_setup) {
          router.push("/setup");
        } else {
          router.push("/workspace");
        }
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail?.message ?? "登录失败，请检查邮箱和密码");
      }
    } catch {
      setError("网络错误，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#F4F5F2]">
      {/* Left Side - Brand */}
      <div className="relative hidden overflow-hidden bg-[#26251E] lg:flex lg:w-1/2">
        {/* Gradient background */}
        <div className="absolute inset-0">
          <div className="absolute top-0 left-0 h-full w-full bg-gradient-to-br from-[#26251E] via-[#1a1914] to-[#0d0c0a]" />
          <div className="absolute top-20 left-20 h-96 w-96 rounded-full bg-violet-500/10 blur-3xl" />
          <div className="absolute right-20 bottom-20 h-96 w-96 rounded-full bg-fuchsia-500/10 blur-3xl" />
          <div className="absolute top-1/2 left-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500/5 blur-3xl" />
        </div>

        <div className="relative z-10 flex flex-col justify-center px-16 py-12">
          <div className="mb-8">
            <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
              <div className="h-6 w-6 rotate-45 transform rounded-sm bg-white" />
            </div>
            <h1 className="mb-2 text-4xl font-semibold text-white">Prism,</h1>
            <h2 className="mb-4 text-3xl font-semibold text-white/90">
              Your Enterprise AI,
            </h2>
            <h2 className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-amber-400 bg-clip-text text-3xl font-semibold text-transparent">
              Always on, acts before you ask.
            </h2>
          </div>

          <p className="max-w-md text-lg leading-relaxed text-gray-400">
            欢迎使用 Prism 企业版
          </p>

          {/* Feature highlights */}
          <div className="mt-12 space-y-4">
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
                <Building2 className="h-5 w-5" />
              </div>
              <span>企业级安全与合规</span>
            </div>
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
                <User className="h-5 w-5" />
              </div>
              <span>团队协作与权限管理</span>
            </div>
            <div className="flex items-center gap-3 text-gray-300">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10">
                <Shield className="h-5 w-5" />
              </div>
              <span>7×24 小时 AI 助手</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="absolute bottom-8 left-16">
          <p className="text-sm text-gray-500">
            © 2024 Prism. All rights reserved.
          </p>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="flex flex-1 flex-col justify-center px-8 py-12 sm:px-12 lg:px-16">
        <div className="mx-auto w-full max-w-md">
          {/* Mobile Logo */}
          <div className="mb-8 flex items-center justify-center lg:hidden">
            <div className="mr-3 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-amber-500">
              <div className="h-5 w-5 rotate-45 transform rounded-sm bg-white" />
            </div>
            <span className="text-xl font-semibold text-gray-900">Prism</span>
          </div>

          <div className="mb-8 text-center">
            <h2 className="mb-2 text-2xl font-semibold text-gray-900">
              欢迎使用 Prism 企业版
            </h2>
            <p className="text-gray-500">使用工作账号登录</p>
          </div>

          {/* Login Tabs */}
          <div className="mb-6 flex rounded-xl bg-gray-100 p-1">
            <button
              className={cn(
                "flex-1 rounded-lg py-2.5 text-sm font-medium transition-all",
                activeTab === "code"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700",
              )}
              onClick={() => setActiveTab("code")}
            >
              验证码登录
            </button>
            <button
              className={cn(
                "flex-1 rounded-lg py-2.5 text-sm font-medium transition-all",
                activeTab === "password"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700",
              )}
              onClick={() => setActiveTab("password")}
            >
              密码登录
            </button>
          </div>

          {/* Form */}
          <form className="space-y-4" onSubmit={handleLogin}>
            {/* Email Input */}
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                工作邮箱地址
              </label>
              <div className="relative">
                <Mail className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  required
                  className="w-full rounded-xl border border-gray-200 bg-white py-3 pr-4 pl-10 text-gray-900 transition-all placeholder:text-gray-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 focus:outline-none"
                />
              </div>
            </div>

            {/* Code or Password Input */}
            {activeTab === "code" ? (
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  验证码
                </label>
                <div className="flex gap-3">
                  <div className="relative flex-1">
                    <Lock className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-gray-400" />
                    <input
                      type="text"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder="6位验证码"
                      className="w-full rounded-xl border border-gray-200 bg-white py-3 pr-4 pl-10 text-gray-900 transition-all placeholder:text-gray-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 focus:outline-none"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={sendCode}
                    disabled={countdown > 0 || !email}
                    className={cn(
                      "rounded-xl px-4 py-3 text-sm font-medium whitespace-nowrap transition-all",
                      countdown > 0 || !email
                        ? "cursor-not-allowed bg-gray-100 text-gray-400"
                        : "bg-gray-900 text-white hover:bg-gray-800",
                    )}
                  >
                    {countdown > 0 ? `${countdown}s` : "发送验证码"}
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700">
                  密码
                </label>
                <div className="relative">
                  <Lock className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-gray-400" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="输入密码"
                    required={activeTab === "password"}
                    className="w-full rounded-xl border border-gray-200 bg-white py-3 pr-4 pl-10 text-gray-900 transition-all placeholder:text-gray-400 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/20 focus:outline-none"
                  />
                </div>
                <div className="mt-2 flex justify-end">
                  <a
                    href="#"
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    忘记密码？
                  </a>
                </div>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={
                loading || !email || (activeTab === "password" && !password)
              }
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-xl bg-gray-900 py-3.5 font-medium text-white transition-all",
                loading || !email || (activeTab === "password" && !password)
                  ? "cursor-not-allowed opacity-70"
                  : "hover:bg-gray-800",
              )}
            >
              {loading ? "登录中..." : "登录"}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-[#F4F5F2] px-4 text-gray-500">或</span>
            </div>
          </div>

          {/* SSO Button */}
          <button className="w-full rounded-xl border border-gray-200 bg-white py-3.5 font-medium text-gray-700 transition-all hover:bg-gray-50">
            使用 SSO 登录
          </button>

          {/* Terms */}
          <p className="mt-6 text-center text-sm text-gray-500">
            继续即表示你同意我们的{" "}
            <a href="#" className="text-gray-700 hover:underline">
              服务条款
            </a>{" "}
            和{" "}
            <a href="#" className="text-gray-700 hover:underline">
              隐私政策
            </a>
          </p>

          {/* Back to home */}
          <div className="mt-6 text-center">
            <Link
              href="/"
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              ← 返回首页
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
