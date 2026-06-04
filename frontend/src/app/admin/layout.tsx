import Link from "next/link";
import { redirect } from "next/navigation";

import { AuthProvider } from "@/core/auth/AuthProvider";
import { getServerSideUser } from "@/core/auth/server";
import { assertNever } from "@/core/auth/types";

import { AdminSidebar } from "./admin-sidebar";
import { RestartBanner } from "./restart-banner";

export const dynamic = "force-dynamic";

export default async function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const result = await getServerSideUser();

  switch (result.tag) {
    case "authenticated": {
      if (result.user.system_role !== "admin") {
        redirect("/workspace");
      }
      return (
        <AuthProvider initialUser={result.user}>
          <div className="flex h-screen flex-col bg-[#F4F5F2]">
            <RestartBanner />
            <div className="flex flex-1 overflow-hidden">
              <AdminSidebar />
              <main className="flex-1 overflow-y-auto p-6">{children}</main>
            </div>
          </div>
        </AuthProvider>
      );
    }
    case "needs_setup":
      redirect("/setup");
    case "system_setup_required":
      redirect("/setup");
    case "unauthenticated":
      redirect("/login");
    case "gateway_unavailable":
      return (
        <div className="flex h-screen flex-col items-center justify-center gap-4 bg-[#F4F5F2]">
          <p className="text-gray-600">Service temporarily unavailable.</p>
          <Link
            href="/admin"
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-800"
          >
            Retry
          </Link>
        </div>
      );
    case "config_error":
      throw new Error(result.message);
    default:
      assertNever(result);
  }
}
