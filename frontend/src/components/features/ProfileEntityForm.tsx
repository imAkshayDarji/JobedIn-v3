"use client";

import { useState } from "react";
import type {
  Certification,
  CertificationCreate,
  CertificationUpdate,
  Education,
  EducationCreate,
  EducationUpdate,
  Experience,
  ExperienceCreate,
  ExperienceUpdate,
  Language,
  LanguageCreate,
  LanguageUpdate,
  Project,
  ProjectCreate,
  ProjectUpdate,
  Skill,
  SkillCreate,
  SkillUpdate,
  TargetRole,
  TargetRoleCreate,
  TargetRoleUpdate,
} from "@/types/profile";
import {
  createCertification,
  createEducation,
  createExperience,
  createLanguage,
  createProject,
  createSkill,
  createTargetRole,
  updateCertification,
  updateEducation,
  updateExperience,
  updateLanguage,
  updateProject,
  updateSkill,
  updateTargetRole,
} from "@/lib/api/profile";

type EntityType =
  | "target-role"
  | "skill"
  | "education"
  | "experience"
  | "project"
  | "certification"
  | "language";

type EntityItem =
  | TargetRole
  | Skill
  | Education
  | Experience
  | Project
  | Certification
  | Language;

interface FieldConfig {
  key: string;
  label: string;
  type: "text" | "textarea" | "date" | "url" | "select" | "checkbox";
  required?: boolean;
  placeholder?: string;
  options?: { value: string; label: string }[];
  colSpan?: boolean;
}

const FIELD_CONFIGS: Record<EntityType, FieldConfig[]> = {
  "target-role": [
    { key: "title", label: "Title", type: "text", required: true, placeholder: "e.g. Senior Frontend Developer" },
    { key: "keywords", label: "Keywords", type: "text", placeholder: "e.g. React, TypeScript, Leadership" },
  ],
  skill: [
    { key: "name", label: "Skill Name", type: "text", required: true, placeholder: "e.g. Python" },
    { key: "category", label: "Category", type: "text", placeholder: "e.g. Programming Language" },
    { key: "proficiency", label: "Proficiency", type: "select", options: [
      { value: "", label: "Select proficiency" },
      { value: "beginner", label: "Beginner" },
      { value: "intermediate", label: "Intermediate" },
      { value: "advanced", label: "Advanced" },
      { value: "expert", label: "Expert" },
    ] },
  ],
  education: [
    { key: "institution", label: "Institution", type: "text", required: true, placeholder: "e.g. MIT" },
    { key: "degree", label: "Degree", type: "text", required: true, placeholder: "e.g. B.S. Computer Science" },
    { key: "field_of_study", label: "Field of Study", type: "text", placeholder: "e.g. Computer Science" },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "grade", label: "Grade / GPA", type: "text" },
    { key: "description", label: "Description", type: "textarea", colSpan: true },
  ],
  experience: [
    { key: "company", label: "Company", type: "text", required: true, placeholder: "e.g. Google" },
    { key: "title", label: "Job Title", type: "text", required: true, placeholder: "e.g. Software Engineer" },
    { key: "location", label: "Location", type: "text", placeholder: "e.g. San Francisco, CA" },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "is_current", label: "Currently working here", type: "checkbox" },
    { key: "description", label: "Description", type: "textarea", colSpan: true },
  ],
  project: [
    { key: "name", label: "Project Name", type: "text", required: true, placeholder: "e.g. JobedIn" },
    { key: "description", label: "Description", type: "textarea", colSpan: true },
    { key: "url", label: "URL", type: "url", placeholder: "https://..." },
    { key: "start_date", label: "Start Date", type: "date" },
    { key: "end_date", label: "End Date", type: "date" },
    { key: "technologies", label: "Technologies", type: "text", placeholder: "e.g. React, Node.js, PostgreSQL" },
  ],
  certification: [
    { key: "name", label: "Certification Name", type: "text", required: true, placeholder: "e.g. AWS Solutions Architect" },
    { key: "issuer", label: "Issuer", type: "text", placeholder: "e.g. Amazon Web Services" },
    { key: "issue_date", label: "Issue Date", type: "date" },
    { key: "expiry_date", label: "Expiry Date", type: "date" },
    { key: "credential_url", label: "Credential URL", type: "url", placeholder: "https://..." },
  ],
  language: [
    { key: "name", label: "Language", type: "text", required: true, placeholder: "e.g. Spanish" },
    { key: "proficiency", label: "Proficiency", type: "select", options: [
      { value: "", label: "Select proficiency" },
      { value: "elementary", label: "Elementary" },
      { value: "limited_working", label: "Limited Working" },
      { value: "professional_working", label: "Professional Working" },
      { value: "full_professional", label: "Full Professional" },
      { value: "native_or_bilingual", label: "Native or Bilingual" },
    ] },
  ],
};

function getDefaults(entityType: EntityType): Record<string, string | boolean> {
  const fields = FIELD_CONFIGS[entityType];
  const defaults: Record<string, string | boolean> = {};
  for (const field of fields) {
    if (field.type === "checkbox") {
      defaults[field.key] = false;
    } else {
      defaults[field.key] = "";
    }
  }
  return defaults;
}

function itemToFormValues(item: EntityItem, entityType: EntityType): Record<string, string | boolean> {
  const defaults = getDefaults(entityType);
  const record = item as unknown as Record<string, unknown>;
  for (const key of Object.keys(defaults)) {
    if (record[key] !== null && record[key] !== undefined) {
      defaults[key] = record[key] as string | boolean;
    }
  }
  return defaults;
}

interface ProfileEntityFormProps {
  entityType: EntityType;
  initialData?: EntityItem;
  onSave: () => void;
  onCancel: () => void;
}

export function ProfileEntityForm({
  entityType,
  initialData,
  onSave,
  onCancel,
}: ProfileEntityFormProps) {
  const isEditing = !!initialData;
  const fields = FIELD_CONFIGS[entityType];
  const [formValues, setFormValues] = useState<Record<string, string | boolean>>(
    isEditing ? itemToFormValues(initialData, entityType) : getDefaults(entityType),
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateField(key: string, value: string | boolean) {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    setError(null);

    const stringValues: Record<string, string | boolean> = {};
    for (const [key, value] of Object.entries(formValues)) {
      if (typeof value === "string" && value.trim() === "") continue;
      stringValues[key] = value;
    }

    try {
      switch (entityType) {
        case "target-role":
          if (isEditing) {
            await updateTargetRole((initialData as TargetRole).id, stringValues as unknown as TargetRoleUpdate);
          } else {
            await createTargetRole(stringValues as unknown as TargetRoleCreate);
          }
          break;
        case "skill":
          if (isEditing) {
            await updateSkill((initialData as Skill).id, stringValues as unknown as SkillUpdate);
          } else {
            await createSkill(stringValues as unknown as SkillCreate);
          }
          break;
        case "education":
          if (isEditing) {
            await updateEducation((initialData as Education).id, stringValues as unknown as EducationUpdate);
          } else {
            await createEducation(stringValues as unknown as EducationCreate);
          }
          break;
        case "experience":
          if (isEditing) {
            await updateExperience((initialData as Experience).id, stringValues as unknown as ExperienceUpdate);
          } else {
            await createExperience(stringValues as unknown as ExperienceCreate);
          }
          break;
        case "project":
          if (isEditing) {
            await updateProject((initialData as Project).id, stringValues as unknown as ProjectUpdate);
          } else {
            await createProject(stringValues as unknown as ProjectCreate);
          }
          break;
        case "certification":
          if (isEditing) {
            await updateCertification((initialData as Certification).id, stringValues as unknown as CertificationUpdate);
          } else {
            await createCertification(stringValues as unknown as CertificationCreate);
          }
          break;
        case "language":
          if (isEditing) {
            await updateLanguage((initialData as Language).id, stringValues as unknown as LanguageUpdate);
          } else {
            await createLanguage(stringValues as unknown as LanguageCreate);
          }
          break;
      }

      onSave();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail ?? "Failed to save");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-blue-200 bg-blue-50/30 p-4">
      {error && (
        <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {fields.map((field) => {
          if (field.type === "checkbox") {
            return (
              <div key={field.key} className="flex items-center gap-2 sm:col-span-2">
                <input
                  id={`field-${field.key}`}
                  type="checkbox"
                  checked={formValues[field.key] as boolean}
                  onChange={(e) => updateField(field.key, e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor={`field-${field.key}`} className="text-sm font-medium text-gray-700">
                  {field.label}
                </label>
              </div>
            );
          }

          if (field.type === "textarea") {
            return (
              <div key={field.key} className={field.colSpan ? "sm:col-span-2" : ""}>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  {field.label}
                </label>
                <textarea
                  value={(formValues[field.key] as string) ?? ""}
                  onChange={(e) => updateField(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            );
          }

          if (field.type === "select") {
            return (
              <div key={field.key}>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  {field.label}
                </label>
                <select
                  value={(formValues[field.key] as string) ?? ""}
                  onChange={(e) => updateField(field.key, e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {field.options?.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            );
          }

          return (
            <div key={field.key} className={field.colSpan ? "sm:col-span-2" : ""}>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {field.label}
              </label>
              <input
                type={field.type}
                value={(formValues[field.key] as string) ?? ""}
                onChange={(e) => updateField(field.key, e.target.value)}
                required={field.required}
                placeholder={field.placeholder}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          );
        })}
      </div>
      <div className="mt-4 flex gap-2">
        <button
          type="submit"
          disabled={isSaving}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isSaving ? "Saving..." : isEditing ? "Update" : "Add"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isSaving}
          className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
