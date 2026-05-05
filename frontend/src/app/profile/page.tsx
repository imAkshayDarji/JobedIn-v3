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
  deleteCertification,
  deleteEducation,
  deleteExperience,
  deleteLanguage,
  deleteProject,
  deleteSkill,
  deleteTargetRole,
  getProfileFull,
} from "@/lib/api/profile";
import {
  deleteLinkedInCredentials,
  getLinkedInStatus,
  saveLinkedInCredentials,
} from "@/lib/api/settings";
import { uploadResume } from "@/lib/api/onboarding";
import { AppLayout } from "@/components/layout/AppLayout";
import { ProfileChildList } from "@/components/features/ProfileChildList";
import { ProfileEntityForm } from "@/components/features/ProfileEntityForm";
import { ProfilePersonalInfo } from "@/components/features/ProfilePersonalInfo";
import { ProfileSection } from "@/components/features/ProfileSection";

type EntityType =
  | "target-role"
  | "skill"
  | "education"
  | "experience"
  | "project"
  | "certification"
  | "language";

type EditingItem =
  | { entity: "education"; item: Education }
  | { entity: "experience"; item: Experience }
  | { entity: "skill"; item: Skill }
  | { entity: "project"; item: Project }
  | { entity: "target-role"; item: TargetRole }
  | { entity: "certification"; item: Certification }
  | { entity: "language"; item: Language };

const ENTITY_SECTIONS: {
  title: string;
  entity: EntityType;
  entityName: string;
  getItems: (p: ProfileDetail) => { id: string }[];
}[] = [
  {
    title: "Target Roles",
    entity: "target-role",
    entityName: "target role",
    getItems: (p) => p.target_roles,
  },
  {
    title: "Skills",
    entity: "skill",
    entityName: "skill",
    getItems: (p) => p.skills,
  },
  {
    title: "Education",
    entity: "education",
    entityName: "education",
    getItems: (p) => p.education,
  },
  {
    title: "Experience",
    entity: "experience",
    entityName: "experience",
    getItems: (p) => p.experience,
  },
  {
    title: "Projects",
    entity: "project",
    entityName: "project",
    getItems: (p) => p.projects,
  },
  {
    title: "Certifications",
    entity: "certification",
    entityName: "certification",
    getItems: (p) => p.certifications,
  },
  {
    title: "Languages",
    entity: "language",
    entityName: "language",
    getItems: (p) => p.languages,
  },
];

export default function ProfilePage() {
  const [profileData, setProfileData] = useState<ProfileDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<EditingItem | null>(null);
  const [addingEntity, setAddingEntity] = useState<EntityType | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

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

  function handleFormSave() {
    setEditingItem(null);
    setAddingEntity(null);
    fetchProfile();
  }

  function handleFormCancel() {
    setEditingItem(null);
    setAddingEntity(null);
  }

  function getActiveFormEntity(): EntityType | null {
    if (editingItem) return editingItem.entity;
    if (addingEntity) return addingEntity;
    return null;
  }

  function renderItemImage(entity: EntityType, item: { id: string }): React.ReactNode {
    const p = profileData!;
    switch (entity) {
      case "target-role": {
        const tr = item as TargetRole;
        return (
          <div>
            <p className="text-sm font-medium text-gray-900">{tr.title}</p>
            {tr.keywords && (
              <p className="text-xs text-gray-500">{tr.keywords}</p>
            )}
          </div>
        );
      }
      case "skill": {
        const sk = item as Skill;
        return (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              {sk.name}
            </span>
            {sk.category && (
              <span className="text-xs text-gray-400">{sk.category}</span>
            )}
          </div>
        );
      }
      case "education": {
        const ed = item as Education;
        return (
          <div>
            <p className="text-sm font-medium text-gray-900">{ed.degree}</p>
            <p className="text-xs text-gray-500">{ed.institution}</p>
            {ed.field_of_study && (
              <p className="text-xs text-gray-400">{ed.field_of_study}</p>
            )}
          </div>
        );
      }
      case "experience": {
        const ex = item as Experience;
        return (
          <div>
            <p className="text-sm font-medium text-gray-900">{ex.title}</p>
            <p className="text-xs text-gray-500">{ex.company}</p>
            {ex.location && (
              <p className="text-xs text-gray-400">{ex.location}</p>
            )}
          </div>
        );
      }
      case "project": {
        const pr = item as Project;
        return (
          <div>
            <p className="text-sm font-medium text-gray-900">{pr.name}</p>
            {pr.description && (
              <p className="text-xs text-gray-500 line-clamp-2">
                {pr.description}
              </p>
            )}
            {pr.technologies && (
              <p className="text-xs text-gray-400">{pr.technologies}</p>
            )}
          </div>
        );
      }
      case "certification": {
        const cert = item as Certification;
        return (
          <div>
            <p className="text-sm font-medium text-gray-900">{cert.name}</p>
            {cert.issuer && (
              <p className="text-xs text-gray-500">{cert.issuer}</p>
            )}
          </div>
        );
      }
      case "language": {
        const lang = item as Language;
        return (
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900">
              {lang.name}
            </span>
            {lang.proficiency && (
              <span className="text-xs text-gray-400">
                ({lang.proficiency})
              </span>
            )}
          </div>
        );
      }
    }
  }

  const activeFormEntity = getActiveFormEntity();

  const pageContent = isLoading ? (
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
  ) : error && !profileData ? (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-red-700">{error}</p>
      </div>
    </div>
  ) : !profileData ? null : (
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

        {ENTITY_SECTIONS.map((section) => {
          const isFormActive = activeFormEntity === section.entity;
          const editingItemForSection =
            editingItem?.entity === section.entity ? editingItem.item : null;

          return (
            <ProfileSection
              key={section.entity}
              title={section.title}
              onAdd={() => {
                setEditingItem(null);
                setAddingEntity(section.entity);
              }}
            >
              {isFormActive && (
                <div className="mb-4">
                  <ProfileEntityForm
                    entityType={section.entity}
                    initialData={editingItemForSection ?? undefined}
                    onSave={handleFormSave}
                    onCancel={handleFormCancel}
                  />
                </div>
              )}
              <ProfileChildList
                items={section.getItems(profileData)}
                entityName={section.entityName}
                renderItem={(item) => renderItemImage(section.entity, item)}
                onEdit={(item) => {
                  setAddingEntity(null);
                  switch (section.entity) {
                    case "target-role":
                      setEditingItem({ entity: "target-role", item: item as TargetRole });
                      break;
                    case "skill":
                      setEditingItem({ entity: "skill", item: item as Skill });
                      break;
                    case "education":
                      setEditingItem({ entity: "education", item: item as Education });
                      break;
                    case "experience":
                      setEditingItem({ entity: "experience", item: item as Experience });
                      break;
                    case "project":
                      setEditingItem({ entity: "project", item: item as Project });
                      break;
                    case "certification":
                      setEditingItem({ entity: "certification", item: item as Certification });
                      break;
                    case "language":
                      setEditingItem({ entity: "language", item: item as Language });
                      break;
                  }
                }}
                onDelete={(item) => handleInlineDelete(section.entity, item)}
              />
            </ProfileSection>
          );
        })}

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

  return <AppLayout>{pageContent}</AppLayout>;
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
