"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import type { Skill } from "@/types/onboarding";

interface SkillsFormProps {
  skills: Skill[];
  onUpdate: (skills: Skill[]) => void;
}

const SKILL_CATEGORIES = [
  "Programming",
  "Framework",
  "Database",
  "DevOps",
  "Design",
  "Soft Skills",
  "Other",
] as const;

const PROFICIENCY_LEVELS = [
  "beginner",
  "intermediate",
  "advanced",
  "expert",
] as const;

export function SkillsForm({ skills, onUpdate }: SkillsFormProps) {
  const [items, setItems] = useState<Skill[]>(skills);

  const addSkill = () => {
    const updated = [...items, { name: "", category: null, proficiency: null }];
    setItems(updated);
    onUpdate(updated);
  };

  const removeSkill = (index: number) => {
    const updated = items.filter((_, i) => i !== index);
    setItems(updated);
    onUpdate(updated);
  };

  const updateSkill = (
    index: number,
    field: keyof Skill,
    value: string,
  ) => {
    const updated = items.map((s, i) =>
      i === index ? { ...s, [field]: value || null } : s,
    );
    setItems(updated);
    onUpdate(updated);
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Add your key skills. These help match you with relevant job
        opportunities.
      </p>

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Skills</h3>
        <button
          type="button"
          onClick={addSkill}
          className="flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
        >
          <Plus className="h-4 w-4" />
          Add Skill
        </button>
      </div>

      <div className="space-y-3">
        {items.map((skill, index) => (
          <div
            key={index}
            className="flex items-start gap-3 rounded-md border border-gray-200 p-3"
          >
            <div className="flex flex-1 flex-wrap gap-2">
              <input
                type="text"
                placeholder="Skill name *"
                value={skill.name}
                onChange={(e) => updateSkill(index, "name", e.target.value)}
                className="min-w-[150px] flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
              <select
                value={skill.category ?? ""}
                onChange={(e) => updateSkill(index, "category", e.target.value)}
                className="min-w-[120px] rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              >
                <option value="">Category</option>
                {SKILL_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
              <select
                value={skill.proficiency ?? ""}
                onChange={(e) =>
                  updateSkill(index, "proficiency", e.target.value)
                }
                className="min-w-[120px] rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              >
                <option value="">Proficiency</option>
                {PROFICIENCY_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level.charAt(0).toUpperCase() + level.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => removeSkill(index)}
              className="mt-1 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        {items.length === 0 && (
          <p className="py-4 text-center text-sm text-gray-500">
            No skills added yet. Click &quot;Add Skill&quot; to get started.
          </p>
        )}
      </div>
    </div>
  );
}
