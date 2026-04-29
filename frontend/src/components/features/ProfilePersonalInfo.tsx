"use client";

import { useState } from "react";
import type { ProfileDetail, ProfileUpdateRequest } from "@/types/profile";
import { updateProfile } from "@/lib/api/profile";

interface ProfilePersonalInfoProps {
  profile: ProfileDetail;
  onUpdate: () => void;
}

export function ProfilePersonalInfo({
  profile,
  onUpdate,
}: ProfilePersonalInfoProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<ProfileUpdateRequest>({
    first_name: profile.first_name,
    last_name: profile.last_name,
    headline: profile.headline ?? "",
    summary: profile.summary ?? "",
    location: profile.location ?? "",
    phone: profile.phone ?? "",
    experience_level: profile.experience_level ?? "",
    linkedin_url: profile.linkedin_url ?? "",
    github_url: profile.github_url ?? "",
    portfolio_url: profile.portfolio_url ?? "",
    website_url: profile.website_url ?? "",
  });

  function handleCancel() {
    setForm({
      first_name: profile.first_name,
      last_name: profile.last_name,
      headline: profile.headline ?? "",
      summary: profile.summary ?? "",
      location: profile.location ?? "",
      phone: profile.phone ?? "",
      experience_level: profile.experience_level ?? "",
      linkedin_url: profile.linkedin_url ?? "",
      github_url: profile.github_url ?? "",
      portfolio_url: profile.portfolio_url ?? "",
      website_url: profile.website_url ?? "",
    });
    setError(null);
    setIsEditing(false);
  }

  async function handleSave() {
    setIsSaving(true);
    setError(null);
    try {
      const updateData: ProfileUpdateRequest = {};
      let hasChanges = false;

      if (form.first_name && form.first_name !== profile.first_name) {
        updateData.first_name = form.first_name;
        hasChanges = true;
      }
      if (form.last_name && form.last_name !== profile.last_name) {
        updateData.last_name = form.last_name;
        hasChanges = true;
      }
      if (form.headline !== (profile.headline ?? "")) {
        updateData.headline = form.headline || null;
        hasChanges = true;
      }
      if (form.summary !== (profile.summary ?? "")) {
        updateData.summary = form.summary || null;
        hasChanges = true;
      }
      if (form.location !== (profile.location ?? "")) {
        updateData.location = form.location || null;
        hasChanges = true;
      }
      if (form.phone !== (profile.phone ?? "")) {
        updateData.phone = form.phone || null;
        hasChanges = true;
      }
      if (form.experience_level !== (profile.experience_level ?? "")) {
        updateData.experience_level = form.experience_level || null;
        hasChanges = true;
      }
      if (form.linkedin_url !== (profile.linkedin_url ?? "")) {
        updateData.linkedin_url = form.linkedin_url || null;
        hasChanges = true;
      }
      if (form.github_url !== (profile.github_url ?? "")) {
        updateData.github_url = form.github_url || null;
        hasChanges = true;
      }
      if (form.portfolio_url !== (profile.portfolio_url ?? "")) {
        updateData.portfolio_url = form.portfolio_url || null;
        hasChanges = true;
      }
      if (form.website_url !== (profile.website_url ?? "")) {
        updateData.website_url = form.website_url || null;
        hasChanges = true;
      }

      if (hasChanges) {
        await updateProfile(updateData);
      }

      setIsEditing(false);
      onUpdate();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail ?? "Failed to update profile");
    } finally {
      setIsSaving(false);
    }
  }

  if (isEditing) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          Personal Information
        </h2>
        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              First Name
            </label>
            <input
              type="text"
              value={form.first_name ?? ""}
              onChange={(e) =>
                setForm({ ...form, first_name: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Last Name
            </label>
            <input
              type="text"
              value={form.last_name ?? ""}
              onChange={(e) =>
                setForm({ ...form, last_name: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Headline
            </label>
            <input
              type="text"
              value={form.headline ?? ""}
              onChange={(e) =>
                setForm({ ...form, headline: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Summary
            </label>
            <textarea
              value={form.summary ?? ""}
              onChange={(e) =>
                setForm({ ...form, summary: e.target.value })
              }
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Location
            </label>
            <input
              type="text"
              value={form.location ?? ""}
              onChange={(e) =>
                setForm({ ...form, location: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Phone
            </label>
            <input
              type="text"
              value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Experience Level
            </label>
            <select
              value={form.experience_level ?? ""}
              onChange={(e) =>
                setForm({ ...form, experience_level: e.target.value || null })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Select level</option>
              <option value="student">Student</option>
              <option value="fresher">Fresher</option>
              <option value="junior">Junior</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead</option>
              <option value="executive">Executive</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              LinkedIn URL
            </label>
            <input
              type="url"
              value={form.linkedin_url ?? ""}
              onChange={(e) =>
                setForm({ ...form, linkedin_url: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              GitHub URL
            </label>
            <input
              type="url"
              value={form.github_url ?? ""}
              onChange={(e) =>
                setForm({ ...form, github_url: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Portfolio URL
            </label>
            <input
              type="url"
              value={form.portfolio_url ?? ""}
              onChange={(e) =>
                setForm({ ...form, portfolio_url: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Website URL
            </label>
            <input
              type="url"
              value={form.website_url ?? ""}
              onChange={(e) =>
                setForm({ ...form, website_url: e.target.value })
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSaving}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Personal Information
        </h2>
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Edit
        </button>
      </div>

      <div className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium text-gray-500">Name</p>
          <p className="text-sm text-gray-900">
            {profile.first_name} {profile.last_name}
          </p>
        </div>
        {profile.headline && (
          <div>
            <p className="text-xs font-medium text-gray-500">Headline</p>
            <p className="text-sm text-gray-900">{profile.headline}</p>
          </div>
        )}
        {profile.location && (
          <div>
            <p className="text-xs font-medium text-gray-500">Location</p>
            <p className="text-sm text-gray-900">{profile.location}</p>
          </div>
        )}
        {profile.phone && (
          <div>
            <p className="text-xs font-medium text-gray-500">Phone</p>
            <p className="text-sm text-gray-900">{profile.phone}</p>
          </div>
        )}
        {profile.experience_level && (
          <div>
            <p className="text-xs font-medium text-gray-500">
              Experience Level
            </p>
            <p className="text-sm capitalize text-gray-900">
              {profile.experience_level}
            </p>
          </div>
        )}
        {profile.summary && (
          <div className="sm:col-span-2">
            <p className="text-xs font-medium text-gray-500">Summary</p>
            <p className="text-sm text-gray-900">{profile.summary}</p>
          </div>
        )}
        <div className="flex flex-wrap gap-4 sm:col-span-2">
          {profile.linkedin_url && (
            <a
              href={profile.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline"
            >
              LinkedIn
            </a>
          )}
          {profile.github_url && (
            <a
              href={profile.github_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline"
            >
              GitHub
            </a>
          )}
          {profile.portfolio_url && (
            <a
              href={profile.portfolio_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline"
            >
              Portfolio
            </a>
          )}
          {profile.website_url && (
            <a
              href={profile.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline"
            >
              Website
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
