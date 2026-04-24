"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import type { PersonalInfo, TargetRole } from "@/types/onboarding";

interface PersonalDetailsProps {
  personalInfo: PersonalInfo;
  targetRoles: TargetRole[];
  onUpdate: (info: PersonalInfo, roles: TargetRole[]) => void;
}

const EXPERIENCE_LEVELS = [
  "student",
  "fresher",
  "junior",
  "mid",
  "senior",
  "lead",
  "executive",
] as const;

export function PersonalDetails({
  personalInfo,
  targetRoles,
  onUpdate,
}: PersonalDetailsProps) {
  const [info, setInfo] = useState<PersonalInfo>(personalInfo);
  const [roles, setRoles] = useState<TargetRole[]>(targetRoles);

  const updateField = (field: keyof PersonalInfo, value: string) => {
    const updated = { ...info, [field]: value || null };
    setInfo(updated);
    onUpdate(updated, roles);
  };

  const addRole = () => {
    const updated = [...roles, { title: "", priority: roles.length, keywords: null }];
    setRoles(updated);
    onUpdate(info, updated);
  };

  const removeRole = (index: number) => {
    const updated = roles.filter((_, i) => i !== index);
    setRoles(updated);
    onUpdate(info, updated);
  };

  const updateRole = (index: number, field: keyof TargetRole, value: string) => {
    const updated = roles.map((r, i) =>
      i === index ? { ...r, [field]: value || null } : r,
    );
    setRoles(updated);
    onUpdate(info, updated);
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="first_name" className="block text-sm font-medium text-gray-700">
            First Name *
          </label>
          <input
            id="first_name"
            type="text"
            required
            value={info.first_name}
            onChange={(e) => updateField("first_name", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="last_name" className="block text-sm font-medium text-gray-700">
            Last Name *
          </label>
          <input
            id="last_name"
            type="text"
            required
            value={info.last_name}
            onChange={(e) => updateField("last_name", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          />
        </div>
      </div>

      <div>
        <label htmlFor="headline" className="block text-sm font-medium text-gray-700">
          Professional Headline
        </label>
        <input
          id="headline"
          type="text"
          placeholder="e.g., Senior Full-Stack Engineer"
          value={info.headline ?? ""}
          onChange={(e) => updateField("headline", e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="location" className="block text-sm font-medium text-gray-700">
            Location
          </label>
          <input
            id="location"
            type="text"
            placeholder="e.g., San Francisco, CA"
            value={info.location ?? ""}
            onChange={(e) => updateField("location", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label htmlFor="experience_level" className="block text-sm font-medium text-gray-700">
            Experience Level
          </label>
          <select
            id="experience_level"
            value={info.experience_level ?? ""}
            onChange={(e) => updateField("experience_level", e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          >
            <option value="">Select level</option>
            {EXPERIENCE_LEVELS.map((level) => (
              <option key={level} value={level}>
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="summary" className="block text-sm font-medium text-gray-700">
          Professional Summary
        </label>
        <textarea
          id="summary"
          rows={3}
          placeholder="Brief summary of your professional background..."
          value={info.summary ?? ""}
          onChange={(e) => updateField("summary", e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
        />
      </div>

      <div>
        <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
          Phone
        </label>
        <input
          id="phone"
          type="tel"
          placeholder="+1 (555) 123-4567"
          value={info.phone ?? ""}
          onChange={(e) => updateField("phone", e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
        />
      </div>

      <div className="border-t border-gray-200 pt-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">
            Target Job Roles
          </h3>
          <button
            type="button"
            onClick={addRole}
            className="flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100"
          >
            <Plus className="h-4 w-4" />
            Add Role
          </button>
        </div>

        <div className="mt-3 space-y-3">
          {roles.map((role, index) => (
            <div
              key={index}
              className="flex items-start gap-3 rounded-md border border-gray-200 p-3"
            >
              <div className="flex-1 space-y-2">
                <input
                  type="text"
                  placeholder="Job title *"
                  value={role.title}
                  onChange={(e) => updateRole(index, "title", e.target.value)}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
                <input
                  type="text"
                  placeholder="Keywords (comma separated)"
                  value={role.keywords ?? ""}
                  onChange={(e) => updateRole(index, "keywords", e.target.value)}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <button
                type="button"
                onClick={() => removeRole(index)}
                className="mt-1 rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
          {roles.length === 0 && (
            <p className="py-4 text-center text-sm text-gray-500">
              No target roles added yet. Click &quot;Add Role&quot; to get
              started.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
