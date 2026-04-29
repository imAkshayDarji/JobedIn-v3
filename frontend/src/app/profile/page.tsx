"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  Certification,
  Education,
  Experience,
  Language,
  ProfileDetail,
  Project,
  Skill,
  TargetRole,
} from "@/types/profile";
import {
  createCertification,
  createEducation,
  createExperience,
  createLanguage,
  createProject,
  createSkill,
  createTargetRole,
  deleteCertification,
  deleteEducation,
  deleteExperience,
  deleteLanguage,
  deleteProject,
  deleteSkill,
  deleteTargetRole,
  getProfileFull,
  updateCertification,
  updateEducation,
  updateExperience,
  updateLanguage,
  updateProject,
  updateSkill,
  updateTargetRole,
} from "@/lib/api/profile";
import {
  deleteLinkedInCredentials,
  getLinkedInStatus,
  saveLinkedInCredentials,
} from "@/lib/api/settings";
import { uploadResume } from "@/lib/api/onboarding";
import { ProfileChildList } from "@/components/features/ProfileChildList";
import { ProfilePersonalInfo } from "@/components/features/ProfilePersonalInfo";
import { ProfileSection } from "@/components/features/ProfileSection";

type EditingItem =
  | { entity: "education"; item: Education }
  | { entity: "experience"; item: Experience }
  | { entity: "skill"; item: Skill }
  | { entity: "project"; item: Project }
  | { entity: "target-role"; item: TargetRole }
  | { entity: "certification"; item: Certification }
  | { entity: "language"; item: Language };

type AddingEntity =
  | "education"
  | "experience"
  | "skill"
  | "project"
  | "target-role"
  | "certification"
  | "language"
  | null;

export default function ProfilePage() {
  const [profileData, setProfileData] = useState<ProfileDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<EditingItem | null>(null);
  const [addingEntity, setAddingEntity] = useState<AddingEntity>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const [linkedinStatus, setLinkedinStatus] = useState<{
    has_credentials: boolean;
    email: string | null;
  } | null>(null);

  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isUploadingResume, setIsUploadingResume] = useState(false);

  const fetchProfile = useCallback(async () => {
    try {
      const data = await getProfileFull();
      setProfileData(data);
    } catch (err: unknown) {
      const apiErr = err as { detail?: string; status?: number };
      if (apiErr.status === 404) {
        setError("Complete your profile first.");
      } else {
        setError(apiErr.detail ?? "Failed to load profile");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchLinkedInStatus = useCallback(async () => {
    try {
      const status = await getLinkedInStatus();
      setLinkedinStatus(status);
    } catch {
      // Silently ignore
    }
  }, []);

  useEffect(() => {
    fetchProfile();
    fetchLinkedInStatus();
  }, [fetchProfile, fetchLinkedInStatus]);

  async function handleDeleteConfirm(itemId: string) {
    setDeleteConfirm(itemId);
  }

  async function handleDeleteExecute() {
    if (!deleteConfirm || !editingItem) return;
    setActionError(null);
    try {
      const { entity, item } = editingItem;
      const id = item.id;

      switch (entity) {
        case "education":
          await deleteEducation(id);
          break;
        case "experience":
          await deleteExperience(id);
          break;
        case "skill":
          await deleteSkill(id);
          break;
        case "project":
          await deleteProject(id);
          break;
        case "target-role":
          await deleteTargetRole(id);
          break;
        case "certification":
          await deleteCertification(id);
          break;
        case "language":
          await deleteLanguage(id);
          break;
      }

      setEditingItem(null);
      setDeleteConfirm(null);
      await fetchProfile();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setActionError(apiErr.detail ?? "Failed to delete");
    }
  }

  async function handleInlineDelete(
    entity: string,
    item: { id: string },
  ) {
    setActionError(null);
    try {
      switch (entity) {
        case "education":
          await deleteEducation(item.id);
          break;
        case "experience":
          await deleteExperience(item.id);
          break;
        case "skill":
          await deleteSkill(item.id);
          break;
        case "project":
          await deleteProject(item.id);
          break;
        case "target-role":
          await deleteTargetRole(item.id);
          break;
        case "certification":
          await deleteCertification(item.id);
          break;
        case "language":
          await deleteLanguage(item.id);
          break;
      }
      await fetchProfile();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setActionError(apiErr.detail ?? "Failed to delete");
    }
  }

  async function handleUploadResume() {
    if (!resumeFile) return;
    setIsUploadingResume(true);
    try {
      await uploadResume(resumeFile);
      setResumeFile(null);
      await fetchProfile();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setActionError(apiErr.detail ?? "Failed to upload resume");
    } finally {
      setIsUploadingResume(false);
    }
  }

  async function handleSaveLinkedIn(email: string, password: string) {
    try {
      await saveLinkedInCredentials(email, password);
      await fetchLinkedInStatus();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setActionError(apiErr.detail ?? "Failed to save LinkedIn credentials");
    }
  }

  async function handleDeleteLinkedIn() {
    try {
      await deleteLinkedInCredentials();
      await fetchLinkedInStatus();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setActionError(
        apiErr.detail ?? "Failed to delete LinkedIn credentials",
      );
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-8 h-8 w-48 animate-pulse rounded bg-gray-200" />
        <div className="space-y-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-40 animate-pulse rounded-lg bg-gray-100"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error && !profileData) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!profileData) return null;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-8 text-2xl font-bold text-gray-900">Profile</h1>

      {actionError && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {actionError}
          <button
            type="button"
            onClick={() => setActionError(null)}
            className="ml-2 font-medium underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="space-y-6">
        <ProfilePersonalInfo
          profile={profileData}
          onUpdate={fetchProfile}
        />

        <ProfileSection title="Target Roles">
          <ProfileChildList
            items={profileData.target_roles}
            entityName="target role"
            renderItem={(item) => (
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {item.title}
                </p>
                {item.keywords && (
                  <p className="text-xs text-gray-500">{item.keywords}</p>
                )}
              </div>
            )}
            onEdit={(item) =>
              setEditingItem({ entity: "target-role", item })
            }
            onDelete={(item) => handleInlineDelete("target-role", item)}
          />
        </ProfileSection>

        <ProfileSection title="Skills">
          <ProfileChildList
            items={profileData.skills}
            entityName="skill"
            renderItem={(item) => (
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
                  {item.name}
                </span>
                {item.category && (
                  <span className="text-xs text-gray-400">
                    {item.category}
                  </span>
                )}
              </div>
            )}
            onEdit={(item) => setEditingItem({ entity: "skill", item })}
            onDelete={(item) => handleInlineDelete("skill", item)}
          />
        </ProfileSection>

        <ProfileSection title="Education">
          <ProfileChildList
            items={profileData.education}
            entityName="education"
            renderItem={(item) => (
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {item.degree}
                </p>
                <p className="text-xs text-gray-500">{item.institution}</p>
                {item.field_of_study && (
                  <p className="text-xs text-gray-400">
                    {item.field_of_study}
                  </p>
                )}
              </div>
            )}
            onEdit={(item) =>
              setEditingItem({ entity: "education", item })
            }
            onDelete={(item) => handleInlineDelete("education", item)}
          />
        </ProfileSection>

        <ProfileSection title="Experience">
          <ProfileChildList
            items={profileData.experience}
            entityName="experience"
            renderItem={(item) => (
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {item.title}
                </p>
                <p className="text-xs text-gray-500">{item.company}</p>
                {item.location && (
                  <p className="text-xs text-gray-400">{item.location}</p>
                )}
              </div>
            )}
            onEdit={(item) =>
              setEditingItem({ entity: "experience", item })
            }
            onDelete={(item) => handleInlineDelete("experience", item)}
          />
        </ProfileSection>

        <ProfileSection title="Projects">
          <ProfileChildList
            items={profileData.projects}
            entityName="project"
            renderItem={(item) => (
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {item.name}
                </p>
                {item.description && (
                  <p className="text-xs text-gray-500 line-clamp-2">
                    {item.description}
                  </p>
                )}
                {item.technologies && (
                  <p className="text-xs text-gray-400">
                    {item.technologies}
                  </p>
                )}
              </div>
            )}
            onEdit={(item) =>
              setEditingItem({ entity: "project", item })
            }
            onDelete={(item) => handleInlineDelete("project", item)}
          />
        </ProfileSection>

        <ProfileSection title="Certifications">
          <ProfileChildList
            items={profileData.certifications}
            entityName="certification"
            renderItem={(item) => (
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {item.name}
                </p>
                {item.issuer && (
                  <p className="text-xs text-gray-500">{item.issuer}</p>
                )}
              </div>
            )}
            onEdit={(item) =>
              setEditingItem({ entity: "certification", item })
            }
            onDelete={(item) => handleInlineDelete("certification", item)}
          />
        </ProfileSection>

        <ProfileSection title="Languages">
          <ProfileChildList
            items={profileData.languages}
            entityName="language"
            renderItem={(item) => (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900">
                  {item.name}
                </span>
                {item.proficiency && (
                  <span className="text-xs text-gray-400">
                    ({item.proficiency})
                  </span>
                )}
              </div>
            )}
            onEdit={(item) =>
              setEditingItem({ entity: "language", item })
            }
            onDelete={(item) => handleInlineDelete("language", item)}
          />
        </ProfileSection>

        <ProfileSection title="LinkedIn Credentials">
          {linkedinStatus?.has_credentials ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-900">
                  Connected: {linkedinStatus.email}
                </p>
              </div>
              <button
                type="button"
                onClick={handleDeleteLinkedIn}
                className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
              >
                Remove
              </button>
            </div>
          ) : (
            <LinkedInForm onSave={handleSaveLinkedIn} />
          )}
        </ProfileSection>

        <ProfileSection title="Resume">
          <div className="flex items-center gap-4">
            <input
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={(e) =>
                setResumeFile(e.target.files?.[0] ?? null)
              }
              className="text-sm text-gray-500 file:mr-4 file:rounded-md file:border-0 file:bg-gray-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-gray-700 hover:file:bg-gray-200"
            />
            <button
              type="button"
              onClick={handleUploadResume}
              disabled={!resumeFile || isUploadingResume}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isUploadingResume ? "Uploading..." : "Upload Resume"}
            </button>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Upload a new resume to update your profile. AI-suggested updates
            will appear in your profile.
          </p>
        </ProfileSection>
      </div>
    </div>
  );
}

function LinkedInForm({ onSave }: { onSave: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    await onSave(email, password);
    setIsSaving(false);
    setEmail("");
    setPassword("");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          LinkedIn Email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          LinkedIn Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <button
        type="submit"
        disabled={isSaving}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {isSaving ? "Saving..." : "Save Credentials"}
      </button>
    </form>
  );
}
