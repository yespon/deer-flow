import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AuthProvider } from "@/core/auth/AuthProvider";
import { getServerSideUser } from "@/core/auth/server";
import { assertNever } from "@/core/auth/types";

import { WorkspaceContent } from "./workspace-content";

export const dynamic = "force-dynamic";

function parseSidebarOpenCookie(
  value: string | undefined,
): boolean | undefined {
  if (value === "true") return true;
  if (value === "false") return false;
  return undefined;
}

export default async function WorkspaceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const result = await getServerSideUser();
  const cookieStore = await cookies();
  const initialSidebarOpen = parseSidebarOpenCookie(
    cookieStore.get("sidebar_state")?.value,
  );

  switch (result.tag) {
    case "authenticated":
      return (
        <AuthProvider initialUser={result.user}>
          <WorkspaceContent defaultOpen={initialSidebarOpen}>
            {children}
          </WorkspaceContent>
        </AuthProvider>
      );
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
          <p className="text-xs text-gray-500">
            The backend may be restarting. Please wait a moment and try again.
          </p>
          <div className="flex gap-3">
            <Link
              href="/workspace"
              className="rounded-lg bg-gray-900 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-800"
            >
              Retry
            </Link>
            <form action="/api/v1/auth/logout" method="post">
              <button
                type="submit"
                className="text-muted-foreground hover:bg-muted rounded-md border px-4 py-2 text-sm"
              >
                Logout &amp; Reset
              </button>
            </form>
          </div>
        </div>
      );
    case "config_error":
      throw new Error(result.message);
    default:
      assertNever(result);
  }
}
