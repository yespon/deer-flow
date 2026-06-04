"use client";

import {
  BarChart3,
  Cpu,
  Database,
  MessageSquare,
  Puzzle,
  Server,
  Users,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAdminDashboard } from "@/core/admin/hooks";

function StatCard({
  title,
  value,
  icon: Icon,
  subtitle,
}: {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  subtitle?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-gray-400" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
      </CardContent>
    </Card>
  );
}

export default function AdminDashboardPage() {
  const { data, isLoading, error } = useAdminDashboard();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <div className="h-16 animate-pulse rounded bg-gray-100" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <Card>
          <CardContent className="p-6 text-center text-red-600">
            Failed to load dashboard data. Please try again.
          </CardContent>
        </Card>
      </div>
    );
  }

  const {
    stats,
    feedback_stats,
    channels,
    memory_config,
    skills_count,
    mcp_servers,
  } = data ?? {};

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>

      {/* Core stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Users" value={stats?.total_users ?? 0} icon={Users} />
        <StatCard
          title="Runs"
          value={stats?.total_runs ?? 0}
          icon={BarChart3}
        />
        <StatCard
          title="Threads"
          value={stats?.total_threads ?? 0}
          icon={Database}
        />
        <StatCard
          title="Feedback"
          value={feedback_stats?.total ?? 0}
          icon={MessageSquare}
          subtitle={
            feedback_stats && feedback_stats.total > 0
              ? `${Math.round((feedback_stats.positive_rate ?? 0) * 100)}% positive`
              : undefined
          }
        />
      </div>

      {/* Models */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Cpu className="h-4 w-4" />
            Models
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(stats?.models?.length ?? 0) === 0 ? (
            <p className="text-sm text-gray-500">No models configured</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {stats?.models?.map((name) => (
                <Badge key={name} variant="secondary">
                  {name}
                </Badge>
              ))}
            </div>
          )}
          <p className="mt-2 text-xs text-gray-500">
            Database: {stats?.database_backend ?? "unknown"}
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Skills & MCP */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Puzzle className="h-4 w-4" />
              Extensions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Skills</span>
              <span className="font-medium">{skills_count}</span>
            </div>
            <div className="space-y-1">
              <span className="text-sm text-gray-600">MCP Servers</span>
              {Object.entries(mcp_servers ?? {}).map(([name, info]) => (
                <div
                  key={name}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="ml-3 text-gray-700">{name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">{info.type}</span>
                    <Badge
                      variant={info.enabled ? "default" : "outline"}
                      className="text-xs"
                    >
                      {info.enabled ? "On" : "Off"}
                    </Badge>
                  </div>
                </div>
              ))}
              {Object.keys(mcp_servers ?? {}).length === 0 && (
                <p className="ml-3 text-xs text-gray-400">
                  No MCP servers configured
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Channels & Memory */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Server className="h-4 w-4" />
              Services
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Channel Service</span>
              <Badge
                variant={channels?.service_running ? "default" : "outline"}
                className="text-xs"
              >
                {channels?.service_running ? "Running" : "Stopped"}
              </Badge>
            </div>
            {channels?.service_running &&
              Object.entries(channels.channels ?? {}).map(
                ([name, _info]: [string, unknown]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="ml-3 text-gray-700">{name}</span>
                    <Badge variant="outline" className="text-xs">
                      Active
                    </Badge>
                  </div>
                ),
              )}
            <div className="border-t border-gray-100 pt-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Memory</span>
                <Badge
                  variant={memory_config?.enabled ? "default" : "outline"}
                  className="text-xs"
                >
                  {memory_config?.enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              {memory_config?.enabled && (
                <div className="mt-1 flex items-center justify-between text-xs text-gray-500">
                  <span className="ml-3">
                    Max facts: {memory_config.max_facts}
                  </span>
                  <span>
                    Injection: {memory_config.injection_enabled ? "On" : "Off"}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
