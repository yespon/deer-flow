"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

interface SkillItem {
  name: string;
  description: string;
  license: string | null;
  category: "public" | "custom";
  enabled: boolean;
}

function useSkills() {
  return useQuery({
    queryKey: ["admin", "skills"],
    queryFn: async () => {
      const res = await fetch(`${getBackendBaseURL()}/api/skills`);
      const json = await res.json();
      return json.skills as SkillItem[];
    },
  });
}

function useToggleSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      name,
      enabled,
    }: {
      name: string;
      enabled: boolean;
    }) => {
      const res = await fetch(`${getBackendBaseURL()}/api/skills/${name}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "skills"] });
    },
  });
}

export default function AdminSkillsPage() {
  const { data: skills, isLoading } = useSkills();
  const toggleMut = useToggleSkill();

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Skills</h1>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Name
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Description
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Category
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">
                  Enabled
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    Loading...
                  </td>
                </tr>
              )}
              {skills?.map((skill) => (
                <tr
                  key={skill.name}
                  className="border-b border-gray-50 hover:bg-gray-50/50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {skill.name}
                  </td>
                  <td className="max-w-xs truncate px-4 py-3 text-gray-500">
                    {skill.description}
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant={
                        skill.category === "custom" ? "default" : "outline"
                      }
                    >
                      {skill.category}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Switch
                      checked={skill.enabled}
                      onCheckedChange={(checked) =>
                        void toggleMut.mutate({
                          name: skill.name,
                          enabled: checked,
                        })
                      }
                    />
                  </td>
                </tr>
              ))}
              {skills?.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    No skills found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
